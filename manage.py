"""Local owner editor. Only optimized copies are published; originals stay private."""
import base64,hashlib,json,mimetypes,os,secrets,threading,time,uuid,webbrowser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote,urlsplit,unquote
import originals as store

ROOT=store.ROOT
TOKEN=secrets.token_urlsafe(32)
JOBS={}

def revision(card):
 return hashlib.sha256(json.dumps({k:v for k,v in card.items() if not k.startswith('_')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def cards():
 result=store.load_cards(ROOT)
 for card in result:card['_revision']=revision(card)
 return result

def find_card(identifier):
 if not isinstance(identifier,str):raise ValueError('Не указана карточка.')
 return next((card for card in cards() if card['id']==identifier),None)

def commit(paths,message):
 paths=list(dict.fromkeys(str(Path(p).relative_to(ROOT)).replace('\\','/') for p in paths))
 try:
  store.git('add','-A','--',*paths)
  if not store.git('diff','--cached','--name-only','--',*paths).strip():return {'committed':True}
  store.git('commit','--only','-m',message,'--',*paths)
  return {'committed':True}
 except (ValueError,TimeoutError) as error:return {'committed':False,'notice':'Файлы сохранены. В GitHub Desktop нужно сначала сделать Commit, затем Push origin. '+str(error)}

def save_card(payload):
 with store.LOCK:
  identifier=payload.get('id');old=find_card(identifier) if identifier else None
  if identifier and not old:raise ValueError('Карточка не найдена. Обновите список.')
  if old and payload.get('_revision')!=old['_revision']:raise ValueError('Карточка уже изменилась. Обновите список перед сохранением.')
  name=str(payload.get('name','')).strip()
  if not name or len(name)>160:raise ValueError('Введите кличку длиной до 160 символов.')
  photos=list(dict.fromkeys('/'+store.asset_key(p) for p in payload.get('photos',[])))
  if not photos:raise ValueError('Добавьте хотя бы одно фото перед сохранением карточки.')
  for asset in photos:
   if not (ROOT/'static'/asset.lstrip('/')).is_file():raise ValueError('Не найдено фото: '+asset)
  status=payload.get('status','unknown')
  if status not in ('unknown','shelter','home'):raise ValueError('Неверный статус.')
  colors=payload.get('tag_colors',[])
  if not isinstance(colors,list) or any(c not in ['синяя','голубая','красная','оранжевая','светло-оранжевая','жёлтая','зелёная','бежевая','белая'] for c in colors):raise ValueError('Неверный цвет бирки.')
  sex=payload.get('sex',(old or {}).get('sex','unknown'))
  if sex not in ('unknown','male','female'):raise ValueError('Неверный пол.')
  age=str(payload.get('age',(old or {}).get('age',''))).strip()
  if len(age)>80:raise ValueError('Укажите возраст длиной до 80 символов.')
  identifier=identifier or 'N'+uuid.uuid4().hex[:12]
  card={k:v for k,v in (old or {}).items() if not k.startswith('_')}
  card.update(id=identifier,name=name,photos=photos,status=status,sex=sex,age=age,tag_colors=colors,tag_number=str(payload.get('tag_number','')).strip(),description=str(payload.get('description',card.get('description',''))).strip(),character_description=str(payload.get('character_description',card.get('character_description',''))).strip())
  path=ROOT/'content/dogs'/(old['_file'] if old else identifier+'.json');store.atomic_json(path,card)
  paths=[path]
  for asset in photos:
   if asset.startswith('/media/library/'):
    paths.extend([ROOT/'static'/asset.lstrip('/'),ROOT/'static'/asset.lstrip('/').replace('media/','thumbs/',1)])
  result=commit(paths,'Update dog card '+identifier);result['id']=identifier
  return result

def move_photos(payload):
 with store.LOCK:
  source=find_card(payload.get('source'));target=find_card(payload.get('target'))
  if not source or not target or source['id']==target['id']:raise ValueError('Выберите две разные карточки.')
  if payload.get('_revision')!=source['_revision']:raise ValueError('Карточка изменилась. Обновите список.')
  selected=set('/'+store.asset_key(a) for a in payload.get('photos',[]))
  if not selected or not selected.issubset(set(source['photos'])):raise ValueError('Выберите фотографии из исходной карточки.')
  moving=[p for p in source['photos'] if p in selected]
  source['photos']=[p for p in source['photos'] if p not in selected]
  if not source['photos'] and not payload.get('remove_empty'):raise ValueError('Карточка станет пустой. Для объединения отметьте «Удалить пустую карточку».')
  target['photos']=list(dict.fromkeys(target['photos']+moving))
  paths=[]
  for card in [source,target]:
   path=ROOT/'content/dogs'/card['_file'];paths.append(path)
   if not card['photos']:path.unlink()
   else:store.atomic_json(path,{k:v for k,v in card.items() if not k.startswith('_')})
  result=commit(paths,'Move photos from '+source['id']+' to '+target['id']);result['id']=target['id'];return result

def task(operation):
 identifier=uuid.uuid4().hex;job={'id':identifier,'state':'running','done':0,'total':0,'message':'Подготовка…'};JOBS[identifier]=job
 def work():
  try:
   if operation=='sync':
    if store.git('status','--porcelain').strip():raise ValueError('В папке есть несохранённые изменения. Сначала сохраните карточки и сделайте Commit в GitHub Desktop.')
    if store.git('branch','--show-current').decode().strip()!='main':raise ValueError('Переключитесь на main в GitHub Desktop.')
    store.git('fetch','origin','main',timeout=180);store.git('merge','--ff-only','origin/main',timeout=180)
    job.update(state='done',message='Изменения с GitHub получены.')
   else:
    if operation=='github':
     job['message']='Получаем актуальные карточки с GitHub…';snapshot,source=store.github_snapshot()
    else:snapshot,source=store.load_cards(),'local'
    job['message']='Собираем оригиналы без изменения качества…'
    def progress(done,total):job.update(done=done,total=total)
    result=store.export_originals(snapshot,source,progress)
    job.update(state='done',message='Архив готов.',result=result)
  except Exception as error:job.update(state='error',message=str(error))
 threading.Thread(target=work,daemon=True).start();return {'job':identifier}

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def allowed(self):
  host=self.headers.get('Host','');expected=f'127.0.0.1:{self.server.server_port}'
  origin=self.headers.get('Origin')
  return host==expected and (not origin or origin=='http://'+expected)
 def respond(self,value,status=200):
  data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def authorized(self):return self.allowed() and secrets.compare_digest(self.headers.get('X-Editor-Token',''),TOKEN)
 def file(self,path,download=False):
  if not path.is_file():return self.respond({'error':'Файл не найден.'},404)
  self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(path.stat().st_size))
  if download:self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(path.name))
  self.end_headers()
  with path.open('rb') as stream:
   while chunk:=stream.read(1024*1024):self.wfile.write(chunk)
 def do_GET(self):
  try:
   if not self.allowed():return self.respond({'error':'Доступ разрешён только с этого компьютера.'},403)
   path=unquote(urlsplit(self.path).path)
   if path=='/health':return self.respond({'app':'dog-catalog-editor','root':hashlib.sha256(str(ROOT).encode()).hexdigest()})
   if path.startswith('/api/'):
    if not self.authorized():return self.respond({'error':'Обновите страницу редактора.'},403)
    if path=='/api/state':
     index=store.load_index();return self.respond({'description_fields_version':3,'cards':cards(),'originals':len(index['assets']),'site_url':json.loads((ROOT/'settings.json').read_text(encoding='utf-8'))['site_url']})
    if path.startswith('/api/job/'):return self.respond(JOBS.get(path.rsplit('/',1)[-1],{'state':'error','message':'Задание не найдено.'}))
    return self.respond({'error':'Неизвестная команда.'},404)
   if path.startswith('/download/'):
    job=JOBS.get(path.rsplit('/',1)[-1]);result=job.get('result') if job else None
    if not result:return self.respond({'error':'Архив ещё не готов.'},404)
    file=Path(result['file']).resolve()
    if not file.is_relative_to(store.EXPORTS.resolve()):return self.respond({'error':'Неверный архив.'},403)
    return self.file(file,True)
   if path.startswith(('/media/','/thumbs/')):
    file=(ROOT/'static'/path.lstrip('/')).resolve()
    if not file.is_relative_to((ROOT/'static').resolve()):return self.respond({'error':'Неверный путь.'},403)
    return self.file(file)
   if path in ('/editor.js','/editor.css'):return self.file(ROOT/'editor'/path.lstrip('/'))
   if path=='/':
    data=(ROOT/'editor/index.html').read_text(encoding='utf-8').replace('__EDITOR_TOKEN__',TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
   return self.respond({'error':'Страница не найдена.'},404)
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception as error:self.respond({'error':str(error)},400)
 def do_POST(self):
  try:
   if not self.authorized():return self.respond({'error':'Обновите страницу редактора.'},403)
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<85*1024*1024:raise ValueError('Слишком большой запрос.')
   payload=json.loads(self.rfile.read(length));path=urlsplit(self.path).path
   if any(job['state']=='running' for job in JOBS.values()) and path not in ('/api/stop',):raise ValueError('Дождитесь завершения обновления или экспорта.')
   if path=='/api/save':return self.respond(save_card(payload))
   if path=='/api/move':return self.respond(move_photos(payload))
   if path=='/api/upload':
    data=base64.b64decode(payload['data'],validate=True)
    with store.LOCK:asset=store.import_new_photo(data,payload['filename'])
    return self.respond({'asset':asset})
   if path=='/api/bind':
    data=base64.b64decode(payload['data'],validate=True)
    from PIL import Image
    import io
    with Image.open(io.BytesIO(data)) as image:image.verify()
    with store.LOCK:
     index=store.load_index();store.store_original(data,payload['filename'],payload['asset'],index);store.atomic_json(store.VAULT/'index.json',index)
    return self.respond({'message':'Оригинал привязан.'})
   if path=='/api/export':return self.respond(task('github' if payload.get('source')=='github' else 'local'))
   if path=='/api/sync':return self.respond(task('sync'))
   if path=='/api/stop':
    if any(j['state']=='running' for j in JOBS.values()):raise ValueError('Дождитесь завершения экспорта или обновления.')
    self.respond({'message':'Редактор закрыт.'});threading.Thread(target=self.server.shutdown,daemon=True).start();return
   self.respond({'error':'Неизвестная команда.'},404)
  except Exception as error:self.respond({'error':str(error)},400)

def main():
 server=None
 for port in range(8768,8778):
  try:server=ThreadingHTTPServer(('127.0.0.1',port),Handler);break
  except OSError:
   try:
    import http.client
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=2);connection.request('GET','/health');response=connection.getresponse();state=json.loads(response.read());connection.close()
    if state.get('app')=='dog-catalog-editor' and state.get('root')==hashlib.sha256(str(ROOT).encode()).hexdigest():webbrowser.open(f'http://127.0.0.1:{port}/');return
   except Exception:pass
   continue
 if server is None:raise RuntimeError('Не удалось открыть локальный редактор.')
 thread=threading.Thread(target=server.serve_forever);thread.start()
 try:webbrowser.open(f'http://127.0.0.1:{server.server_port}/');thread.join()
 finally:server.shutdown();server.server_close()

if __name__=='__main__':
 try:main()
 except Exception as error:
  path=ROOT/'.local/editor-error.log';path.parent.mkdir(exist_ok=True);path.write_text(str(error),encoding='utf-8')
  if os.name=='nt':
   import ctypes
   ctypes.windll.user32.MessageBoxW(0,'Не удалось открыть редактор. Сообщите об этом в чате. Подробности сохранены в .local/editor-error.log.','Редактор собак',16)
  else:raise
