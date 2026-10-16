import csv,hashlib,io,json,re,zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parent
CATALOG=ROOT.parent/'dog_catalog'
def main():
 records=json.loads((CATALOG/'series.json').read_text(encoding='utf-8'))
 register={r['archive_member']:r for r in csv.DictReader((CATALOG/'photo_register.csv').open(encoding='utf-8-sig'))}
 locations=json.loads((CATALOG/'photo_locations.json').read_text(encoding='utf-8'))
 archive=zipfile.ZipFile(json.loads((CATALOG/'sources.json').read_text(encoding='utf-8'))[0]['path'])
 content=ROOT/'content/dogs';content.mkdir(parents=True,exist_ok=True)
 private=ROOT/'.local';private.mkdir(exist_ok=True);jobs=[];manifest=[]
 for record in records:
  sid=record['series'];files=list(dict.fromkeys(record.get('representative_files',[])+record['files']));photos=[]
  for member in files:
   position=int(register[member]['position']);photos.append(f'media/{sid}/p{position:05}.webp');jobs.append((member,sid,position))
  name=record.get('name') or f'Собака {sid}'
  home=record.get('adoption_status') in ['дома','забрали'] or bool(re.search(r'\((дома|забрали)\)',name,re.I))
  dog=dict(id=sid,name=name,description=record['description'],tag_number=str(record.get('tag_number') or ''),tag_colors=record.get('tag_colors',[]),status='home' if home else 'unknown',photos=photos)
  (content/f'{sid}.json').write_text(json.dumps(dog,ensure_ascii=False,indent=2),encoding='utf-8')
 def convert(job):
  member,sid,position=job;relative=f'media/{sid}/p{position:05}.webp';dest=ROOT/'static'/relative;thumb=ROOT/'static/thumbs'/sid/f'p{position:05}.webp'
  if dest.exists() and thumb.exists():return dict(member=member,asset=relative,bytes=dest.stat().st_size,cached=True)
  path=Path(locations[member]) if member in locations else None
  data=path.read_bytes() if path and path.is_file() else archive.read(member)
  image=ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB');original_size=image.size
  dest.parent.mkdir(parents=True,exist_ok=True);thumb.parent.mkdir(parents=True,exist_ok=True)
  small=image.copy();small.thumbnail((520,520),Image.Resampling.LANCZOS);small.save(thumb,'WEBP',quality=77,method=4)
  image.thumbnail((1800,1800),Image.Resampling.LANCZOS);image.save(dest,'WEBP',quality=84,method=4)
  return dict(member=member,asset=relative,original_size=original_size,published_size=image.size,bytes=dest.stat().st_size,sha256=hashlib.sha256(data).hexdigest())
 with ThreadPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(convert,job) for job in jobs]
  for index,future in enumerate(as_completed(futures),1):
   manifest.append(future.result())
   if index%250==0:print(f'Photos prepared: {index}/{len(jobs)}',flush=True)
 archive.close();assert len(jobs)==len({job[0] for job in jobs})==3064
 (private/'original_photo_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 total=sum(p.stat().st_size for p in (ROOT/'static').rglob('*') if p.is_file())
 summary=dict(cards=len(records),photos=len(jobs),asset_megabytes=round(total/1048576,1),max_photo_side=1800,source_revision='C052')
 (private/'import_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
