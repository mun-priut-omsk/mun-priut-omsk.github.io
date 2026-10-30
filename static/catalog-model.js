/* Catalog state and matching. No characteristics are inferred from names or photos. */
(function(root){
 'use strict';
 const sexes=['male','female'],ages=['puppy','adult','senior'],sizes=['small','medium','large'];
 const labels={male:'Мальчик',female:'Девочка',puppy:'Молодая · до 2 лет',adult:'Взрослая · от 2 до 8 лет',senior:'Пожилая · от 8 лет',small:'Небольшой',medium:'Средний',large:'Крупный'};
 const norm=s=>String(s||'').toLowerCase().replaceAll('ё','е');
 const unnamed=d=>!String(d.name||'').trim()||/^(?:Собака|Серия)(?:\s|$)|^Без\s+клички(?:\s|$)/iu.test(String(d.name).trim());
 const empty=()=>({sex:'',ages:[],sizes:[]});
 const clean=f=>({sex:sexes.includes(f.sex)?f.sex:'',ages:ages.filter(v=>(f.ages||[]).includes(v)),sizes:sizes.filter(v=>(f.sizes||[]).includes(v))});
 function read(url){const p=new URL(url).searchParams;return {q:p.get('q')||'',tab:['all','named','unnamed','home'].includes(p.get('tab'))?p.get('tab'):'named',sort:['name','id','newest'].includes(p.get('sort'))?p.get('sort'):'name',page:Math.min(10000,Math.max(1,Math.floor(Number(p.get('page')))||1)),...clean({sex:p.get('sex'),ages:(p.get('age')||'').split(','),sizes:(p.get('size')||'').split(',')})};}
 function write(url,s){const u=new URL(url);for(const k of ['q','tab','sort','sex','age','size','page'])u.searchParams.delete(k);if(s.q)u.searchParams.set('q',s.q);if(s.tab!=='named')u.searchParams.set('tab',s.tab);if(s.sort!=='name')u.searchParams.set('sort',s.sort);if(s.sex)u.searchParams.set('sex',s.sex);if(s.ages.length)u.searchParams.set('age',s.ages.join(','));if(s.sizes.length)u.searchParams.set('size',s.sizes.join(','));if(s.page>1)u.searchParams.set('page',s.page);return u;}
 function search(d,q){const terms=norm(q).match(/[\p{L}\p{N}]+/gu)||[];if(!terms.length)return true;if(unnamed(d))return false;const words=norm([d.id,d.name,d.character_description,d.description,d.tag_number,...(d.tag_colors||[])].join(' ')).match(/[\p{L}\p{N}]+/gu)||[];return terms.every(t=>words.some(w=>w.startsWith(t)));}
 function ageGroup(years){return typeof years==='number'&&Number.isFinite(years)&&years>=0?(years<2?'puppy':years<8?'adult':'senior'):null;}
 function matches(d,s,available={age:false,size:true}){
  const named=!unnamed(d);
  if(!(s.tab==='all'||s.tab==='home'&&d.status==='home'||s.tab==='named'&&named&&d.status!=='home'||s.tab==='unnamed'&&!named))return false;
  if(!search(d,s.q)||s.sex&&d.sex!==s.sex)return false;
  // Age remains nonrestrictive; size is explicitly supplied by the owner in the editor.
  if((s.ages.length||s.sizes.length)&&!named)return false;
  if(available.age&&s.ages.length&&!s.ages.includes(ageGroup(d.age_years)))return false;
  if(available.size&&s.sizes.length&&!s.sizes.includes(d.size))return false;
  return true;
 }
 const count=f=>(f.sex?1:0)+f.ages.length+f.sizes.length;
 function dogWord(n){const a=Math.abs(n)%100,b=a%10;return a>=11&&a<=14?'собак':b===1?'собаку':b>=2&&b<=4?'собаки':'собак';}
 const api={labels,empty,clean,read,write,search,unnamed,ageGroup,matches,count,dogWord};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.CatalogModel=api;
})(typeof globalThis!=='undefined'?globalThis:this);
