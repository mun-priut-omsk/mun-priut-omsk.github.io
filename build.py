import argparse,hashlib,json,re,shutil
from pathlib import Path
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parent
def make_config(settings):
 fields=[dict(label='Номер карточки',name='id',widget='hidden',default=''),dict(label='Кличка',name='name',widget='string',hint='Если кличка неизвестна, напишите «Собака без клички».'),dict(label='Описание характера — видно на сайте',name='character_description',widget='text',required=False),dict(label='Описание внешности — служебное',name='description',widget='text',required=False,hint='Не показывается в карточке на сайте; используется для поиска по приметам.'),dict(label='Пол',name='sex',widget='select',default='unknown',options=[dict(label='Не указан',value='unknown'),dict(label='Мальчик',value='male'),dict(label='Девочка',value='female')]),dict(label='Возраст',name='age',widget='string',required=False),dict(label='Размер',name='size',widget='select',default='unknown',options=[dict(label='Не указан',value='unknown'),dict(label='Маленький',value='small'),dict(label='Средний',value='medium'),dict(label='Крупный',value='large')]),dict(label='Номер бирки',name='tag_number',widget='string',required=False),dict(label='Цвет бирки',name='tag_colors',widget='select',multiple=True,required=False,options=['синяя','голубая','красная','оранжевая','светло-оранжевая','жёлтая','зелёная','бежевая','белая']),dict(label='Статус',name='status',widget='select',default='unknown',options=[dict(label='Не указан',value='unknown'),dict(label='В приюте',value='shelter'),dict(label='Дома',value='home')]),dict(label='Фотографии',name='photos',widget='list',min=1,field=dict(label='Фото',name='image',widget='image',choose_url=False),hint='Первое фото — обложка. Порядок можно менять перетаскиванием.')]
 backend=dict(name='github',repo=(settings['github_owner'] or 'YOUR_USERNAME')+'/'+settings['github_repo'],branch='main')
 if settings['auth_site']:backend['site_domain']=settings['auth_site']
 return dict(backend=backend,locale='ru',media_folder='static/media',public_folder='/media',publish_mode='simple',site_url=settings['site_url'],display_url=settings['site_url'],show_preview_links=False,collections=[dict(name='dogs',label='Собаки',label_singular='Собака',folder='content/dogs',create=True,delete=True,extension='json',format='json',identifier_field='name',slug='{{year}}-{{month}}-{{day}}-{{hour}}-{{minute}}-{{second}}-{{slug}}',summary='{{name}} · бирка {{tag_number}}',sortable_fields=['name','tag_number'],editor=dict(preview=False),fields=fields)])
def main(production=False,sample=False):
 assert not (production and sample)
 output=ROOT/'dist';output.mkdir(exist_ok=True)
 for file in (ROOT/'static').rglob('*'):
  if not file.is_file():continue
  relative=file.relative_to(ROOT/'static')
  if production and relative.as_posix() in ['practice.html','practice.js']:continue
  if relative.parts[0]=='media':continue
  dest=output/relative;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists() or dest.stat().st_mtime<file.stat().st_mtime:shutil.copy2(file,dest)
 if production:
  for name in ['practice.html','practice.js']:
   if (output/name).is_file():(output/name).unlink()
 dogs=[];seen=set()
 for file in sorted((ROOT/'content/dogs').glob('*.json')):
  if sample and file.stem not in ['S200','S111','S416','S417','S12','S327']:continue
  dog=json.loads(file.read_text(encoding='utf-8'));dog['id']=str(dog.get('id') or 'N'+hashlib.sha256(file.stem.encode()).hexdigest()[:12])
  assert re.fullmatch(r'[A-Za-z0-9_-]{1,80}',dog['id']) and dog['id'] not in seen;seen.add(dog['id'])
  dog['name']=str(dog.get('name') or 'Собака без клички').strip();dog['description']=str(dog.get('description') or '');dog['character_description']=str(dog.get('character_description') or '');dog['sex']=dog.get('sex') or 'unknown';assert dog['sex'] in ['unknown','male','female'];dog['age']=str(dog.get('age') or '').strip();dog['size']=dog.get('size') or 'unknown';assert dog['size'] in ['unknown','small','medium','large'];dog['tag_number']=str(dog.get('tag_number') or '');dog['tag_colors']=list(dog.get('tag_colors') or [])
  assert dog.get('status') in ['unknown','home','shelter'];assert dog.get('photos');pictures=[]
  for path in dog['photos']:
   relative=Path(path[1:] if path.startswith('/media/') else path);assert not relative.is_absolute() and '..' not in relative.parts
   source=ROOT/'static'/relative;assert source.is_file(),f'Missing photo {path}'
   if not (ROOT/'static'/relative.as_posix().replace('media/','thumbs/',1)).is_file():
    key='u'+hashlib.sha256(source.read_bytes()).hexdigest()[:20];full=f'media/uploads-ready/{key}.webp';thumb=f'thumbs/uploads-ready/{key}.webp';original=ImageOps.exif_transpose(Image.open(source)).convert('RGB')
    for target,side,quality in [(full,1800,84),(thumb,520,77)]:
     dest=output/target;dest.parent.mkdir(parents=True,exist_ok=True)
     if not dest.exists():
      image=original.copy();image.thumbnail((side,side),Image.Resampling.LANCZOS);image.save(dest,'WEBP',quality=quality)
   else:
    full=relative.as_posix();thumb=full.replace('media/','thumbs/',1)
    dest=output/full;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists() or dest.stat().st_mtime<source.stat().st_mtime:shutil.copy2(source,dest)
    assert (output/thumb).is_file()
   pictures.append(dict(full=full,thumb=thumb))
  dog['photos']=pictures;dogs.append(dog)
 dogs.sort(key=lambda d:(d['name'].startswith('Собака '),d['name'].casefold().replace('ё','е'),d['id']))
 data=output/'data';data.mkdir(exist_ok=True);payload=dict(dogs=dogs,card_count=len(dogs),photo_count=sum(len(d['photos']) for d in dogs),practice_enabled=not production)
 (data/'dogs.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 settings=json.loads((ROOT/'settings.json').read_text(encoding='utf-8'));configured=bool(settings['github_owner'] and settings['auth_site']);admin=output/'admin';admin.mkdir(exist_ok=True)
 (admin/'setup.json').write_text(json.dumps(dict(configured=configured,owner=settings['github_owner'],repo=settings['github_repo']),ensure_ascii=False),encoding='utf-8')
 (admin/'config.yml').write_text(json.dumps(make_config(settings),ensure_ascii=False,indent=2),encoding='utf-8');(output/'.nojekyll').write_text('')
 total=sum(p.stat().st_size for p in output.rglob('*') if p.is_file());assert total<900*1024*1024,'Site approaching GitHub Pages size limit.'
 print(json.dumps(dict(cards=len(dogs),photos=payload['photo_count'],site_MB=round(total/1048576,1),admin_connected=configured)))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--production',action='store_true');parser.add_argument('--sample',action='store_true');args=parser.parse_args();main(args.production,args.sample)
