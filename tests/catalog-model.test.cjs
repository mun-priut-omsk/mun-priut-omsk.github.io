'use strict';
const assert=require('node:assert/strict');
const M=require('../static/catalog-model.js');
const base=()=>({...M.read('https://example.org/'),tab:'all'});
const dog=(changes={})=>({id:'S1',name:'Граф',sex:'male',status:'shelter',description:'Чёрная шерсть',tag_number:'1234',tag_colors:[],...changes});
assert(M.matches(dog(),base()));
assert(M.matches(dog(),{...base(),sex:'male'}));
assert(!M.matches(dog(),{...base(),sex:'female'}));
assert(!M.matches(dog({sex:'unknown'}),{...base(),sex:'male'}));
assert(M.search(dog(),'граф'));assert(!M.search(dog({name:'Белка',description:'На фотографиях'}),'граф'));
assert(!M.search(dog({name:'Собака S1'}),'1234'));assert(M.search(dog(),'черная 123'));
assert(!M.matches(dog({status:'home'}),{...base(),tab:'named'}));
assert(M.matches(dog({status:'home'}),{...base(),tab:'home'}));
assert(M.matches(dog({name:'Собака S1'}),{...base(),tab:'unnamed'}));
for(const age of ['puppy','adult','senior'])for(const size of ['small','medium','large']){
 assert(M.matches(dog({size}),{...base(),ages:[age],sizes:[size]}));
 assert(!M.matches(dog(),{...base(),ages:[age],sizes:[size]}));
 assert(!M.matches(dog({name:'Собака S1'}),{...base(),ages:[age],sizes:[size]}));
 assert(!M.matches(dog(),{...base(),sex:'female',ages:[age],sizes:[size]}));
}
for(const [years,expected] of [[0,'puppy'],[.999,'puppy'],[1,'adult'],[7.999,'adult'],[8,'senior'],[19,'senior'],[-1,null],[null,null],[NaN,null]])assert.equal(M.ageGroup(years),expected);
// Age is still disabled in production. Explicit sizes use OR within the group, AND with sex.
const selection={...base(),sex:'male',ages:['puppy','senior'],sizes:['small','medium']};
assert(M.matches(dog({age_years:8,size:'medium'}),selection,{age:true,size:true}));
assert(!M.matches(dog({age_years:2,size:'medium'}),selection,{age:true,size:true}));
assert(!M.matches(dog({age_years:8,size:'large'}),selection,{age:true,size:true}));
const full={...base(),q:'Граф 123',tab:'home',sort:'newest',sex:'male',ages:['puppy','senior'],sizes:['small','large'],page:3};
const url=M.write('https://example.org/?dog=S1#catalog',full);assert.deepEqual(M.read(url),full);assert.equal(url.searchParams.get('dog'),'S1');assert.equal(url.hash,'#catalog');
assert.deepEqual(M.read('https://example.org/?sex=garbage&age=adult,adult,bad&size=medium,bad&sort=x&tab=x&page=-3'),{q:'',tab:'named',sort:'name',sex:'',ages:['adult'],sizes:['medium'],page:1});
const reset={...full,...M.empty()};assert.equal(reset.q,full.q);assert.equal(reset.tab,full.tab);assert.equal(reset.sort,full.sort);assert.equal(M.count(reset),0);
for(const [n,word] of [[0,'собак'],[1,'собаку'],[2,'собаки'],[4,'собаки'],[5,'собак'],[11,'собак'],[14,'собак'],[21,'собаку'],[22,'собаки'],[111,'собак']])assert.equal(M.dogWord(n),word);
assert(M.matches(dog({size:'medium'}),{...base(),sizes:['small','medium']}));
assert(!M.matches(dog({size:'large'}),{...base(),sizes:['small','medium']}));
assert(M.matches(dog({size:'unknown'}),base()));
console.log('PASS: sex, named-only search, tabs, size including unknown/multiple choices, placeholder age, OR/AND, age boundaries, URL, reset and plurals');
