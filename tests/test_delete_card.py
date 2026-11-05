import sys,json,tempfile,threading,http.client
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import originals as store,manage
with tempfile.TemporaryDirectory(dir=store.ROOT/'.local') as tmp:
 root=Path(tmp);folder=root/'content/dogs';folder.mkdir(parents=True)
 raw=json.dumps({'id':'S1','name':'Тест','photos':['/media/shared.webp'],'description':'Сохранить всё','age':'4 года'},ensure_ascii=False).encode('utf-8')
 (folder/'S1.json').write_bytes(raw);(folder/'S2.json').write_bytes(raw.replace(b'S1',b'S2'))
 media=root/'static/media';media.mkdir(parents=True);(media/'shared.webp').write_bytes(b'kept')
 vault=root/'vault';vault.mkdir();(vault/'index.json').write_bytes(b'{"keep":true}')
 manage.ROOT=root;commits=[];manage.commit=lambda paths,message:commits.append((paths,message)) or {'committed':True}
 card=manage.find_card('S1')
 for payload in [{'id':'S1','_revision':card['_revision']},{'id':'S1','_revision':'stale','confirmed':True},{'id':'../S1','confirmed':True}]:
  try:manage.delete_card(payload)
  except ValueError:pass
  else:raise AssertionError('unsafe delete accepted')
 assert (folder/'S1.json').read_bytes()==raw and not (root/'.local/deleted_cards').exists()
 server=manage.ThreadingHTTPServer(('127.0.0.1',0),manage.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
 def post(headers,payload):
  conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5);conn.request('POST','/api/delete',json.dumps(payload),headers={'Content-Type':'application/json',**headers});response=conn.getresponse();status=response.status;body=json.loads(response.read());conn.close();return status,body
 payload={'id':'S1','_revision':card['_revision'],'confirmed':True}
 try:
  assert post({},payload)[0]==403
  assert post({'X-Editor-Token':manage.TOKEN,'Origin':'https://foreign.example'},payload)[0]==403
  manage.JOBS['test']={'state':'running'}
  assert post({'X-Editor-Token':manage.TOKEN},payload)[0]==400;manage.JOBS.clear()
  status,result=post({'X-Editor-Token':manage.TOKEN},payload);assert status==200 and result['deleted_id']=='S1'
 finally:server.shutdown();server.server_close()
 assert not (folder/'S1.json').exists() and (folder/'S2.json').exists()
 backups=list((root/'.local/deleted_cards').glob('*.json'));assert len(backups)==1 and backups[0].read_bytes()==raw
 assert (media/'shared.webp').read_bytes()==b'kept' and (vault/'index.json').read_bytes()==b'{"keep":true}'
 assert len(commits)==1 and commits[0][0]==[folder.resolve()/'S1.json']
 # Restore the exact card from its backup, then delete the last two fixtures.
 (folder/'S1.json').write_bytes(backups[0].read_bytes());assert manage.find_card('S1')['name']=='Тест'
 for identifier in ['S1','S2']:
  c=manage.find_card(identifier);manage.delete_card({'id':identifier,'_revision':c['_revision'],'confirmed':True})
 assert manage.cards()==[] and (media/'shared.webp').is_file()
print('PASS: confirmed/revision-safe deletion, authenticated HTTP, active-job rejection, exact backup/restore, shared photos and originals retained, last-card deletion')
