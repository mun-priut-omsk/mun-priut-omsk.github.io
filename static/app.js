(()=>{'use strict';
 const $=s=>document.querySelector(s),base=new URL('./',location.href),colors={'голубая':'#85b9d2','светло-оранжевая':'#e8af83','красная':'#bc5547','белая':'#e5e4db','синяя':'#68a4bc','оранжевая':'#d77b52','жёлтая':'#d4b458','зелёная':'#75a078','бежевая':'#b6a588'},practiceKey='dog-catalog-practice-v1';
 const node=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
 const unnamed=d=>!String(d.name||'').trim()||/^(?:Собака|Серия)(?:\s|$)|^Без\s+клички(?:\s|$)/iu.test(String(d.name).trim()),norm=s=>String(s).toLowerCase().replaceAll('ё','е');
 const nameOrder=new Intl.Collator('ru',{sensitivity:'base',numeric:true});
 const compareByName=(a,b)=>Number(unnamed(a))-Number(unnamed(b))||nameOrder.compare(String(a.name).trim(),String(b.name).trim())||nameOrder.compare(a.id,b.id);
 let dogs=[],filter='named',shown=24,current=null,index=0,trigger=null,practiceEnabled=false;
 function imageURL(path){return new URL(path,base).href;}
 function card(d){
  const article=node('article','dog-card'),button=node('button','card-open');button.type='button';button.setAttribute('aria-label','Открыть карточку: '+d.name);
  const photo=node('div','card-photo'),img=node('img');img.src=imageURL(d.photos[0].thumb);img.alt=d.name;img.loading='lazy';img.decoding='async';photo.append(img);
  if(d.status==='home')photo.append(node('span','home-badge','♡  Дома'));
  photo.append(node('span','photo-amount',d.photos.length+' фото'));
  const body=node('div','card-body'),heading=node('div','card-heading');heading.append(node('h3','',d.name),node('span','','↗'));body.append(heading,node('p','card-id',d.id));
  const tags=node('div','card-tags'),dot=node('span','tag-dot');dot.style.background=colors[d.tag_colors[0]]||'#c5cbbd';tags.append(dot,node('span','',d.tag_number?'Бирка '+d.tag_number:d.tag_colors.length?'Бирка: '+d.tag_colors.map(c=>c==='оранжевая'?'красная':c).join(', '):'Бирка не определена'));
  body.append(tags);button.append(photo,body);button.addEventListener('click',()=>openDog(d,button));article.append(button);return article;
 }
 function filtered(){
  const q=norm($('#search').value.trim()),sort=$('#sort').value;
  const list=dogs.filter(d=>(filter==='all'||filter==='home'&&d.status==='home'||filter==='named'&&!unnamed(d)&&d.status!=='home'||filter==='unnamed'&&unnamed(d))&&norm([d.id,d.name,d.description,d.tag_number,...d.tag_colors].join(' ')).includes(q));
  return list.sort((a,b)=>sort==='name'?compareByName(a,b):sort==='newest'?b.id.localeCompare(a.id,'ru',{numeric:true}):a.id.localeCompare(b.id,'ru',{numeric:true}));
 }
 function render(){const list=filtered(),grid=$('#dog-grid');grid.replaceChildren(...list.slice(0,shown).map(card));$('#result-count').textContent='Найдено: '+list.length;$('#empty-state').hidden=!!list.length;$('#load-more').hidden=list.length<=shown;}
 function setPhoto(){
  const p=current.photos[index],img=$('#detail-photo');img.src=imageURL(p.full);img.alt=current.name+' — фото '+(index+1);$('#photo-counter').textContent=(index+1)+' / '+current.photos.length;
  const download=$('#download-photo');download.href=img.src;download.download=current.name.replace(/[\\/:*?"<>|]/g,'_')+'_'+(index+1)+'.webp';
  $('#previous-photo').hidden=$('#next-photo').hidden=current.photos.length<2;
  document.querySelectorAll('.thumbnail').forEach((n,i)=>{n.classList.toggle('active',i===index);n.setAttribute('aria-pressed',String(i===index));});
 }
 function openDog(d,source){
  current=d;index=0;trigger=source;$('#dog-title').textContent=d.name;$('#dog-id').textContent='Карточка '+d.id;$('#detail-description').textContent=d.description;$('#copy-status').textContent='';
  const tags=$('#detail-tags');tags.replaceChildren();if(d.status==='home')tags.append(node('span','detail-tag','♡ Дома'));else if(d.status==='shelter')tags.append(node('span','detail-tag','В приюте'));
  if(d.tag_number)tags.append(node('span','detail-tag','Бирка №'+d.tag_number));
  d.tag_colors.forEach(c=>{const tag=node('span','detail-tag'),dot=node('span','tag-dot');dot.style.background=colors[c]||'#c5cbbd';tag.append(dot,document.createTextNode(c==='оранжевая'?'Оранжево-красная':c[0].toUpperCase()+c.slice(1)));tags.append(tag);});
  const thumbnails=$('#thumbnails');thumbnails.replaceChildren(...d.photos.map((p,i)=>{const b=node('button','thumbnail'),im=node('img');b.type='button';b.setAttribute('aria-label','Показать фото '+(i+1));im.src=imageURL(p.thumb);im.alt='';im.loading='lazy';b.append(im);b.addEventListener('click',()=>{index=i;setPhoto();});return b;}));setPhoto();
  const url=new URL(location.href);url.searchParams.set('dog',d.id);history.replaceState(null,'',url);if(!$('#dog-dialog').open)$('#dog-dialog').showModal();document.body.classList.add('dialog-open');$('#close-dialog').focus();
 }
 $('#close-dialog').addEventListener('click',()=>$('#dog-dialog').close());$('#dog-dialog').addEventListener('click',e=>{if(e.target===$('#dog-dialog'))$('#dog-dialog').close();});
 $('#dog-dialog').addEventListener('close',()=>{document.body.classList.remove('dialog-open');const url=new URL(location.href);url.searchParams.delete('dog');history.replaceState(null,'',url);$('#detail-photo').removeAttribute('src');trigger?.focus({preventScroll:true});current=null;});
 const step=delta=>{if(current){index=(index+delta+current.photos.length)%current.photos.length;setPhoto();}};$('#previous-photo').addEventListener('click',()=>step(-1));$('#next-photo').addEventListener('click',()=>step(1));
 $('#dog-dialog').addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();step(e.key==='ArrowLeft'?-1:1);}});
 $('#copy-link').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);$('#copy-status').textContent='Ссылка скопирована — можно отправить её друзьям.';}catch{$('#copy-status').textContent='Скопируйте ссылку из адресной строки браузера.';}});
 $('#search').addEventListener('input',()=>{shown=24;render();});$('#sort').addEventListener('change',render);$('#load-more').addEventListener('click',()=>{shown+=24;render();});
 document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;shown=24;document.querySelectorAll('[data-filter]').forEach(n=>{n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));});render();}));
 $('#reset-search').addEventListener('click',()=>{$('#search').value='';document.querySelector('[data-filter="all"]').click();});
 document.addEventListener('keydown',e=>{if(e.key==='/'&&!$('#dog-dialog').open&&!['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)){e.preventDefault();$('#search').focus();}});
 function mergePractice(){if(!practiceEnabled)return;try{const overrides=JSON.parse(localStorage.getItem(practiceKey)||'{}');dogs=dogs.map(d=>({...d,...overrides[d.id]}));$('#practice-banner').hidden=!Object.keys(overrides).length;}catch{}}
 window.addEventListener('storage',e=>{if(e.key===practiceKey)location.reload();});
 fetch(new URL('data/dogs.json',base),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(data=>{
  dogs=data.dogs;practiceEnabled=data.practice_enabled;mergePractice();$('#practice-link').hidden=!practiceEnabled;$('#total-cards').textContent=data.card_count;$('#total-photos').textContent=new Intl.NumberFormat('ru').format(data.photo_count);
  const big=dogs.find(d=>d.id==='S111')||dogs[0],small=dogs.find(d=>d.id==='S30')||dogs[1],smallPhoto=small.photos.find(p=>p.full==='media/S30/p05715.webp')||small.photos[0];$('#hero-main').src=imageURL(big.photos[0].full);$('#hero-main').alt=big.name;$('#hero-main-name').textContent=big.name;$('#hero-small').src=imageURL(smallPhoto.full);$('#hero-small').alt=small.name;
  render();const id=new URL(location.href).searchParams.get('dog');if(id){const d=dogs.find(d=>d.id===id);if(d)openDog(d,null);}
 }).catch(error=>{$('#load-error').hidden=false;$('#result-count').textContent='Каталог недоступен';console.error('Catalog loading failed',error);});
})();
