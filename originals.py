"""Private original-photo storage and lossless export; no account credentials."""
import csv,hashlib,io,json,os,re,shutil,subprocess,threading,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parent
VAULT=ROOT.parent/'dog_originals'
EXPORTS=ROOT.parent/'dog_original_exports'
LOCK=threading.RLock()

def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
 temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 os.replace(temporary,path)

def asset_key(value):
 value=str(value).replace('\\','/').lstrip('/')
 parts=PurePosixPath(value).parts
 if not parts or parts[0]!='media' or any(p in ('.','..') for p in parts) or ':' in value:raise ValueError('Неверный путь фотографии.')
 return '/'.join(parts)

def safe_name(value,fallback='Без имени'):
 value=re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',str(value)).strip(' .')[:120] or fallback
 if value.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:value='_'+value
 return value

def load_index(vault=VAULT):
 path=Path(vault)/'index.json'
 return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'version':1,'assets':{}}

def store_original(data,filename,asset,index=None,vault=VAULT):
 vault=Path(vault);index=index if index is not None else load_index(vault)
 digest=hashlib.sha256(data).hexdigest();extension=Path(filename).suffix.lower()
 if not re.fullmatch(r'\.[a-z0-9]{1,10}',extension):extension='.bin'
 relative=f'objects/{digest[:2]}/{digest}{extension}'
 destination=vault/relative;destination.parent.mkdir(parents=True,exist_ok=True)
 if not destination.exists():
  temporary=destination.with_suffix(destination.suffix+'.tmp');temporary.write_bytes(data);os.replace(temporary,destination)
 elif destination.stat().st_size!=len(data):raise ValueError('Повреждён файл оригинала. Экспорт остановлен.')
 entry={'sha256':digest,'file':relative,'filename':safe_name(PurePosixPath(str(filename).replace('\\','/')).name),'bytes':len(data)}
 key=asset_key(asset);previous=index['assets'].get(key)
 if previous and previous['sha256']!=digest:raise ValueError('У этого фото уже есть другой оригинал. Существующий оригинал сохранён.')
 if previous:entry=previous
 index['assets'][key]=entry
 return entry

def seed(progress=print):
 catalog=ROOT.parent/'dog_catalog'
 manifest=json.loads((ROOT/'.local/original_photo_manifest.json').read_text(encoding='utf-8'))
 locations=json.loads((catalog/'photo_locations.json').read_text(encoding='utf-8'))
 source=json.loads((catalog/'sources.json').read_text(encoding='utf-8'))[0]['path']
 index=load_index();count=len(manifest)
 VAULT.mkdir(exist_ok=True)
 (VAULT/'ПРОЧИТАЙТЕ.txt').write_text('Это хранилище ОРИГИНАЛОВ фотографий. Сохраните резервную копию ВСЕЙ этой папки вместе с index.json.\nНе переименовывайте файлы внутри objects вручную. Карточки и их клички можно менять: связи сохраняются по фотографии.\nПапка не отправляется на GitHub.\n',encoding='utf-8')
 with zipfile.ZipFile(source) as archive:
  for n,item in enumerate(manifest,1):
   key=asset_key(item['asset']);existing=index['assets'].get(key)
   if existing and (VAULT/existing['file']).is_file() and (VAULT/existing['file']).stat().st_size==existing['bytes']:continue
   member=item['member'];path=Path(locations[member]) if member in locations else None
   data=path.read_bytes() if path and path.is_file() else archive.read(member)
   if item.get('sha256') and hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError(f'Исходник изменился: {member}')
   store_original(data,PurePosixPath(member).name,key,index)
   if n%100==0:
    atomic_json(VAULT/'index.json',index);progress(f'Originals protected: {n}/{count}')
 atomic_json(VAULT/'index.json',index);progress(f'Originals protected: {count}/{count}')
 return {'photos':count,'objects':len({x['file'] for x in index['assets'].values()}),'bytes':sum(p.stat().st_size for p in (VAULT/'objects').rglob('*') if p.is_file())}

def git(*args,root=ROOT,timeout=120):
 candidates=[shutil.which('git'),str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe')]
 candidates+=list(map(str,(Path.home()/'AppData/Local/GitHubDesktop').glob('app-*/resources/app/git/cmd/git.exe')))
 executable=next((p for p in candidates if p and Path(p).is_file()),None)
 if not executable:raise ValueError('Не найден Git. Установите GitHub Desktop.')
 env=os.environ.copy();env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never')
 result=subprocess.run([executable,'-C',str(root),'--work-tree='+str(root),*args],capture_output=True,env=env,timeout=timeout)
 if result.returncode:raise ValueError(result.stderr.decode('utf-8',errors='replace').strip() or 'Git не смог выполнить операцию.')
 return result.stdout

def load_cards(root=ROOT):
 cards=[];ids=set()
 for file in sorted((Path(root)/'content/dogs').glob('*.json')):
  card=json.loads(file.read_text(encoding='utf-8'));identifier=card.get('id') or 'N'+hashlib.sha256(file.stem.encode()).hexdigest()[:12]
  if identifier in ids:raise ValueError('Повтор номера карточки: '+identifier)
  ids.add(identifier);card['id']=identifier;card['_file']=file.name
  card.setdefault('name','Собака '+identifier);card.setdefault('description','');card.setdefault('tag_number','');card.setdefault('tag_colors',[]);card.setdefault('status','unknown');card.setdefault('photos',[])
  cards.append(card)
 return cards

def github_snapshot():
 git('fetch','origin','main',timeout=180)
 revision=git('rev-parse','origin/main').decode().strip()
 data=git('archive','--format=zip',revision,'content/dogs')
 cards=[];identifiers=set()
 with zipfile.ZipFile(io.BytesIO(data)) as archive:
  for name in archive.namelist():
   if name.endswith('.json'):
    card=json.loads(archive.read(name));card['id']=card.get('id') or 'N'+hashlib.sha256(Path(name).stem.encode()).hexdigest()[:12]
    if card['id'] in identifiers:raise ValueError('Повтор номера карточки на GitHub: '+card['id'])
    identifiers.add(card['id']);cards.append(card)
 return cards,revision

def export_originals(cards,source='local',progress=None,vault=VAULT,exports=EXPORTS):
 progress=progress or (lambda *args:None);vault=Path(vault);exports=Path(exports);index=load_index(vault)
 plan=[];folders=set();summary=[]
 for card in cards:
  if not card.get('photos'):raise ValueError('В карточке нет фотографий: '+card.get('name',''))
  folder=safe_name(card.get('name') or 'Без клички');candidate=folder
  if candidate.casefold() in folders:candidate=folder+' ['+safe_name(card['id'])+']'
  if candidate.casefold() in folders:raise ValueError('Повтор папки карточки. Проверьте номера карточек.')
  folder=candidate;folders.add(folder.casefold());names=set()
  for photo_number,asset in enumerate(card['photos'],1):
   key=asset_key(asset);entry=index['assets'].get(key)
   if not entry:raise ValueError('В карточке «'+card.get('name',card['id'])+'» ('+card['id']+'), фото '+str(photo_number)+', не привязан оригинал. Выберите это фото в редакторе и нажмите «Привязать оригинал».')
   path=(vault/entry['file']).resolve()
   if not path.is_relative_to(vault.resolve()) or not path.is_file() or path.stat().st_size!=entry['bytes']:raise ValueError('Не найден или повреждён оригинал: '+entry['filename'])
   name=entry['filename'];stem=Path(name).stem;suffix=Path(name).suffix;number=2
   while name.casefold() in names:name=f'{stem}_{number}{suffix}';number+=1
   names.add(name.casefold());plan.append((path,f'Собаки/{folder}/{name}',entry,key,card['id']))
  summary.append([card['id'],card.get('name',''),card.get('tag_number',''),', '.join(card.get('tag_colors',[])),card.get('status',''),card.get('description',''),len(card['photos']),folder])
 exports.mkdir(parents=True,exist_ok=True);size=sum(item[2]['bytes'] for item in plan)
 if shutil.disk_usage(exports).free<size+100*1024*1024:raise ValueError('Недостаточно места для архива оригиналов.')
 stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC');destination=exports/f'Оригиналы собак_{stamp}_{uuid.uuid4().hex[:4]}.zip';temporary=destination.with_suffix('.partial')
 records=[]
 try:
  with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
   for n,(path,name,entry,key,card_id) in enumerate(plan,1):
    digest=hashlib.sha256()
    with path.open('rb') as original,archive.open(name,'w',force_zip64=True) as target:
     while chunk:=original.read(1024*1024):target.write(chunk);digest.update(chunk)
    if digest.hexdigest()!=entry['sha256']:raise ValueError('Проверка оригинала не пройдена: '+entry['filename'])
    records.append({'card_id':card_id,'asset':key,'file':name,'sha256':entry['sha256']})
    if n%25==0 or n==len(plan):progress(n,len(plan))
   stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['Номер','Кличка','Бирка','Цвет бирки','Статус','Описание','Фото','Папка']);writer.writerows(summary)
   archive.writestr('Карточки.csv',('\ufeff'+stream.getvalue()).encode('utf-8'))
   archive.writestr('Карточки.json',json.dumps([{k:v for k,v in d.items() if not k.startswith('_')} for d in cards],ensure_ascii=False,indent=2).encode('utf-8'))
   archive.writestr('Экспорт.json',json.dumps({'source':source,'created_at':datetime.now(timezone.utc).isoformat(),'cards':len(cards),'photos':len(plan),'files':records},ensure_ascii=False,indent=2).encode('utf-8'))
  os.replace(temporary,destination)
 except BaseException:
  if temporary.is_file():temporary.unlink()
  raise
 return {'file':str(destination),'name':destination.name,'cards':len(cards),'photos':len(plan),'bytes':destination.stat().st_size,'source':source}

def import_new_photo(data,filename,root=ROOT,vault=VAULT):
 if len(data)>60*1024*1024:raise ValueError('Файл больше 60 МБ. Добавьте его отдельно через поддержку.')
 with Image.open(io.BytesIO(data)) as original:
  original.load();image=ImageOps.exif_transpose(original).convert('RGB')
 digest=hashlib.sha256(data).hexdigest();asset=f'media/library/{digest}.webp';index=load_index(vault)
 store_original(data,filename,asset,index,vault);atomic_json(Path(vault)/'index.json',index)
 for relative,side,quality in [(asset,1800,84),(asset.replace('media/','thumbs/',1),520,77)]:
  path=Path(root)/'static'/relative;path.parent.mkdir(parents=True,exist_ok=True)
  if not path.exists():
   photo=image.copy();photo.thumbnail((side,side),Image.Resampling.LANCZOS);temporary=path.with_suffix('.tmp');photo.save(temporary,'WEBP',quality=quality);os.replace(temporary,path)
 return '/'+asset

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['seed','export-local','export-github']);args=parser.parse_args()
 if args.operation=='seed':print(json.dumps(seed(),ensure_ascii=True))
 else:
  cards,source=github_snapshot() if args.operation=='export-github' else (load_cards(),'local')
  print(json.dumps(export_originals(cards,source,lambda n,total:print(f'Exported {n}/{total}',flush=True)),ensure_ascii=True))
