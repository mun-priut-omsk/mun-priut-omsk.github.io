(()=>{'use strict';
 const $=s=>document.querySelector(s),base=new URL('./',location.href),practiceKey='dog-catalog-practice-v1';
 const node=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
 const unnamed=d=>!String(d.name||'').trim()||/^(?:Собака|Серия)(?:\s|$)|^Без\s+клички(?:\s|$)/iu.test(String(d.name).trim()),norm=s=>String(s).toLowerCase().replaceAll('ё','е');
 const nameOrder=new Intl.Collator('ru',{sensitivity:'base',numeric:true});
 const compareByName=(a,b)=>Number(unnamed(a))-Number(unnamed(b))||nameOrder.compare(String(a.name).trim(),String(b.name).trim())||nameOrder.compare(a.id,b.id);
 const M=CatalogModel;
 let state=M.read(location.href),draft=null,searchTimer=null,lockedY=0,restoring=false;
 let dogs=[],shown=state.page*24,current=null,index=0,trigger=null,practiceEnabled=false;
 function imageURL(path){return new URL(path,base).href;}
 function card(d){
  const article=node('article','dog-card'),button=node('button','card-open');button.type='button';button.setAttribute('aria-label','Открыть карточку: '+d.name);
  const photo=node('div','card-photo'),img=node('img');img.src=imageURL(d.photos[0].thumb);img.alt=d.name;img.loading='lazy';img.decoding='async';photo.append(img);
  if(d.status==='home')photo.append(node('span','home-badge','♡  Дома'));
  photo.append(node('span','photo-amount',d.photos.length+' фото'));
  const body=node('div','card-body'),heading=node('div','card-heading');heading.append(node('h3','',d.name),node('span','','↗'));body.append(heading,node('p','card-id',d.id));
  const tags=node('div','card-tags');tags.append(node('span','',d.tag_number?'Бирка '+d.tag_number:'Бирка не указана'));
  body.append(tags);button.append(photo,body);button.addEventListener('click',()=>openDog(d,button));article.append(button);return article;
 }
 function filtered(selection=state){
  const list=dogs.filter(d=>M.matches(d,selection));
  return list.sort((a,b)=>selection.sort==='name'?compareByName(a,b):selection.sort==='newest'?b.id.localeCompare(a.id,'ru',{numeric:true}):a.id.localeCompare(b.id,'ru',{numeric:true}));
 }
 function render(){const list=filtered(),grid=$('#dog-grid');grid.replaceChildren(...list.slice(0,shown).map(card));$('#result-count').textContent='Найдено: '+list.length;$('#empty-state').hidden=!!list.length;$('#load-more').hidden=list.length<=shown;renderChips();syncControls();}
 function syncControls(){
  $('#search').value=state.q;$('#sort').value=state.sort;
  document.querySelectorAll('[data-filter]').forEach(b=>{const active=b.dataset.filter===state.tab;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  document.querySelectorAll('#desktop-fields input').forEach(i=>i.checked=i.name==='desktop-sex'?state.sex===i.value:state[i.dataset.group].includes(i.value));
  $('#open-filters').textContent='Фильтры'+(M.count(state)?' · '+M.count(state):'');
 }
 function renderChips(){
  const area=$('#active-filters');area.replaceChildren();
  for(const [group,values] of [['sex',state.sex?[state.sex]:[]],['ages',state.ages],['sizes',state.sizes]])for(const value of values){
   const b=node('button','active-chip',M.labels[value]);b.type='button';b.setAttribute('aria-label','Убрать: '+M.labels[value]);b.append(node('span','','×'));b.addEventListener('click',()=>{if(group==='sex')state.sex='';else state[group]=state[group].filter(v=>v!==value);apply();});area.append(b);
  }
  $('#clear-profile').hidden=!M.count(state);
 }
 function persist(){clearTimeout(searchTimer);const url=M.write(location.href,state);if(url.href!==location.href)history.pushState(null,'',url);}
 function showResults(){const target=$('#results-start'),rect=target.getBoundingClientRect(),top=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--catalog-top'))||16;const offset=top+(matchMedia('(max-width:900px)').matches?$('#open-filters').parentElement.offsetHeight:0)+12;if(rect.top<offset||rect.top>innerHeight-80)window.scrollBy({top:rect.top-offset,behavior:'auto'});}
 function apply(){state.page=1;shown=24;persist();render();showResults();}
 function resetProfile(){Object.assign(state,M.empty());apply();}
 function makeFields(container,prefix){
  for(const [key,title,options,type] of [['sex','Пол',[['','Любой'],['male','Мальчик'],['female','Девочка']],'radio'],['ages','Возраст',[['puppy','Молодая · до 2 лет'],['adult','Взрослая · от 2 до 8 лет'],['senior','Пожилая · от 8 лет']],'checkbox'],['sizes','Размер',[['small','Небольшой'],['medium','Средний'],['large','Крупный']],'checkbox']]){
   const field=node('fieldset','profile-group');field.append(node('legend','',title));for(const [value,label] of options){const item=node('label','profile-option'),input=node('input');input.type=type;input.name=prefix+'-'+key;input.value=value;input.dataset.group=key;item.append(input,node('span','',label));field.append(item);}container.append(field);
  }
  container.addEventListener('change',e=>{const i=e.target;if(!i.matches('input'))return;const selection=prefix==='desktop'?state:draft;if(i.dataset.group==='sex')selection.sex=i.value;else selection[i.dataset.group]=[...container.querySelectorAll('input[data-group="'+i.dataset.group+'"]:checked')].map(n=>n.value);if(prefix==='desktop')apply();else updateDraftCount();});
 }
 function updateDraftCount(){$('#apply-filters').textContent='Показать '+filtered({...state,...draft}).length+' '+M.dogWord(filtered({...state,...draft}).length);}
 function syncDraft(){document.querySelectorAll('#mobile-fields input').forEach(i=>i.checked=i.dataset.group==='sex'?draft.sex===i.value:draft[i.dataset.group].includes(i.value));updateDraftCount();}
 function openFilters(){clearTimeout(searchTimer);persist();draft=M.clean(state);syncDraft();lockedY=scrollY;document.body.style.setProperty('--locked-scroll',-lockedY+'px');document.body.classList.add('filters-open');$('#filters-dialog').showModal();$('#close-filters').focus();}
 function finishFilters(){if(!document.body.classList.contains('filters-open'))return;draft=null;document.body.classList.remove('filters-open');document.body.style.removeProperty('--locked-scroll');window.scrollTo({top:lockedY,behavior:'instant'});$('#open-filters').focus({preventScroll:true});}
 function closeFilters(){$('#filters-dialog').close();finishFilters();}
 makeFields($('#desktop-fields'),'desktop');makeFields($('#mobile-fields'),'mobile');
 $('#open-filters').addEventListener('click',openFilters);$('#close-filters').addEventListener('click',closeFilters);
 $('#mobile-reset').addEventListener('click',()=>{draft=M.empty();syncDraft();});
 $('#apply-filters').addEventListener('click',()=>{Object.assign(state,M.clean(draft));closeFilters();apply();});
 $('#filters-dialog').addEventListener('close',finishFilters);
 $('#filters-dialog').addEventListener('keydown',e=>{if(e.key!=='Tab')return;const focusable=[...$('#filters-dialog').querySelectorAll('button,input')].filter(n=>!n.disabled);const first=focusable[0],last=focusable.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}});
 $('#filters-dialog').addEventListener('click',e=>{if(e.target===$('#filters-dialog'))closeFilters();});
 $('#desktop-reset').addEventListener('click',resetProfile);$('#clear-profile').addEventListener('click',resetProfile);
 function restore(){clearTimeout(searchTimer);if($('#filters-dialog').open)closeFilters();state=M.read(location.href);shown=state.page*24;render();const id=new URL(location.href).searchParams.get('dog');if(current&&!id){restoring=true;$('#dog-dialog').close();}if(id){const d=dogs.find(d=>d.id===id);if(d)openDog(d,null);}}
 window.addEventListener('popstate',restore);
 const headerObserver=new ResizeObserver(()=>{const header=$('.site-header'),fixed=['sticky','fixed'].includes(getComputedStyle(header).position);document.documentElement.style.setProperty('--catalog-top',(fixed?header.offsetHeight+12:12)+'px');});headerObserver.observe($('.site-header'));
 matchMedia('(max-width:900px)').addEventListener('change',e=>{if(!e.matches&&$('#filters-dialog').open)closeFilters();});
 function setPhoto(){
  const p=current.photos[index],img=$('#detail-photo');img.src=imageURL(p.full);img.alt=current.name+' — фото '+(index+1);$('#photo-counter').textContent=(index+1)+' / '+current.photos.length;
  const download=$('#download-photo');download.href=img.src;download.download=current.name.replace(/[\\/:*?"<>|]/g,'_')+'_'+(index+1)+'.webp';
  $('#previous-photo').hidden=$('#next-photo').hidden=current.photos.length<2;
  document.querySelectorAll('.thumbnail').forEach((n,i)=>{n.classList.toggle('active',i===index);n.setAttribute('aria-pressed',String(i===index));});
 }
 function appendProfileTags(tags,d){
  const sex={male:'Мальчик',female:'Девочка'}[d.sex];
  if(sex)tags.append(node('span','detail-tag',sex));
  if(String(d.age||'').trim())tags.append(node('span','detail-tag',String(d.age).trim()));
  const size={small:'Небольшой размер',medium:'Средний размер',large:'Крупный размер'}[d.size];
  if(size)tags.append(node('span','detail-tag',size));
 }
 function renderCharacterDescription(value){
  const text=String(value||''),fragment=document.createDocumentFragment();let position=0;
  for(const match of text.matchAll(/\*\*([\s\S]+?)\*\*/g)){fragment.append(document.createTextNode(text.slice(position,match.index)),node('strong','',match[1]));position=match.index+match[0].length;}
  fragment.append(document.createTextNode(text.slice(position)));return fragment;
 }
 function openDog(d,source){
  current=d;index=0;trigger=source;$('#dog-title').textContent=d.name;$('#dog-id').textContent='Карточка '+d.id;$('#detail-description').replaceChildren(renderCharacterDescription(d.character_description));$('#detail-description').hidden=!String(d.character_description||'').trim();$('#copy-status').textContent='';
  const tags=$('#detail-tags');tags.replaceChildren();if(d.status==='home')tags.append(node('span','detail-tag','♡ Дома'));else if(d.status==='shelter')tags.append(node('span','detail-tag','В приюте'));
  if(d.tag_number)tags.append(node('span','detail-tag','Бирка №'+d.tag_number));
  appendProfileTags(tags,d);
  const thumbnails=$('#thumbnails');thumbnails.replaceChildren(...d.photos.map((p,i)=>{const b=node('button','thumbnail'),im=node('img');b.type='button';b.setAttribute('aria-label','Показать фото '+(i+1));im.src=imageURL(p.thumb);im.alt='';im.loading='lazy';b.append(im);b.addEventListener('click',()=>{index=i;setPhoto();});return b;}));setPhoto();
  const url=new URL(location.href);url.searchParams.set('dog',d.id);history.replaceState(null,'',url);if(!$('#dog-dialog').open)$('#dog-dialog').showModal();document.body.classList.add('dialog-open');$('#close-dialog').focus();
 }
 $('#close-dialog').addEventListener('click',()=>$('#dog-dialog').close());$('#dog-dialog').addEventListener('click',e=>{if(e.target===$('#dog-dialog'))$('#dog-dialog').close();});
 $('#dog-dialog').addEventListener('close',()=>{document.body.classList.remove('dialog-open');const url=new URL(location.href);url.searchParams.delete('dog');if(!restoring)history.replaceState(null,'',url);restoring=false;$('#detail-photo').removeAttribute('src');trigger?.focus({preventScroll:true});current=null;});
 const step=delta=>{if(current){index=(index+delta+current.photos.length)%current.photos.length;setPhoto();}};$('#previous-photo').addEventListener('click',()=>step(-1));$('#next-photo').addEventListener('click',()=>step(1));
 $('#dog-dialog').addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();step(e.key==='ArrowLeft'?-1:1);}});
 $('#copy-link').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);$('#copy-status').textContent='Ссылка скопирована — можно отправить её друзьям.';}catch{$('#copy-status').textContent='Скопируйте ссылку из адресной строки браузера.';}});
 $('#search').addEventListener('input',()=>{state.q=$('#search').value;state.page=1;shown=24;render();clearTimeout(searchTimer);searchTimer=setTimeout(persist,300);});
 $('#sort').addEventListener('change',()=>{state.sort=$('#sort').value;apply();});
 $('#load-more').addEventListener('click',()=>{const previous=shown;state.page++;shown=state.page*24;persist();render();const firstNew=$('#dog-grid').children[previous]?.querySelector('button');firstNew?.focus({preventScroll:true});});
 document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{state.tab=b.dataset.filter;apply();}));
 $('#reset-search').addEventListener('click',resetProfile);
 document.addEventListener('keydown',e=>{if(e.key==='/'&&!$('#dog-dialog').open&&!$('#filters-dialog').open&&!['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)){e.preventDefault();$('#search').focus();}});
 function mergePractice(){if(!practiceEnabled)return;try{const overrides=JSON.parse(localStorage.getItem(practiceKey)||'{}');dogs=dogs.map(d=>({...d,...overrides[d.id]}));$('#practice-banner').hidden=!Object.keys(overrides).length;}catch{}}
 window.addEventListener('storage',e=>{if(e.key===practiceKey)location.reload();});
 fetch(new URL('data/dogs.json',base),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(data=>{
  dogs=data.dogs;practiceEnabled=data.practice_enabled;mergePractice();$('#practice-link').hidden=!practiceEnabled;$('#total-cards').textContent=data.card_count;$('#total-photos').textContent=new Intl.NumberFormat('ru').format(data.photo_count);
  const big=dogs.find(d=>d.id==='S111')||dogs[0],small=dogs.find(d=>d.id==='S30')||dogs[1],smallPhoto=small.photos.find(p=>p.full==='media/S30/p05715.webp')||small.photos[0];$('#hero-main').src=imageURL(big.photos[0].full);$('#hero-main').alt=big.name;$('#hero-main-name').textContent=big.name;$('#hero-small').src=imageURL(smallPhoto.full);$('#hero-small').alt=small.name;
  render();const id=new URL(location.href).searchParams.get('dog');if(id){const d=dogs.find(d=>d.id===id);if(d)openDog(d,null);}
 }).catch(error=>{$('#load-error').hidden=false;$('#result-count').textContent='Каталог недоступен';console.error('Catalog loading failed',error);});
})();
