// Unit-test the actual generated script with synthetic DOM/audio objects.
// This is deliberately not a browser or physical audio-device test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
 constructor(tag){this.tagName=tag;this.children=[];this.listeners={};this.dataset={};this.value='';this.paused=true;this.currentTime=0;this.duration=8;this.className='';this.classList={add(){},remove(){},toggle(){}};}
 append(...nodes){for(const n of nodes){if(typeof n==='object')n.parentElement=this;this.children.push(n)}}
 setAttribute(){}
 addEventListener(name,fn){(this.listeners[name]??=[]).push(fn)}
 async fire(name){for(const f of this.listeners[name]||[])await f({target:this})}
 async play(){this.paused=false;await this.fire('play')}
 pause(){this.paused=true}
 load(){this.currentTime=0}
 querySelector(){return null}
 querySelectorAll(){return []}
}
const ids={};for(const id of ['groups','jump','progress','feedbackText','status','copy','export','generate','playbackMode'])ids[id]=new Element('div');
ids.playbackMode.value='aligned';
const document={getElementById:id=>ids[id],createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text}),body:new Element('body')};
const context={document,localStorage:{getItem(){return null},setItem(){}},console,setTimeout,URL,Blob,navigator:{}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
const descendants=node=>[node,...(node.children||[]).filter(x=>typeof x==='object').flatMap(descendants)];
const cards=ids.groups.children;
const buttons=card=>descendants(card).filter(x=>x.tagName==='button'&&x.textContent?.startsWith('▶'));
const player=card=>descendants(card).find(x=>x.tagName==='audio');
(async()=>{
 const first=buttons(cards[0]);const a=player(cards[0]);
 await first[0].fire('click');a.currentTime=2.4;
 await first[1].fire('click');assert.equal(a.currentTime,2.4,'aligned switching must preserve the phrase position');
 ids.playbackMode.value='restart';a.currentTime=3.1;
 await first[0].fire('click');assert.equal(a.currentTime,0,'restart mode must reset');
 const b=player(cards[1]);await buttons(cards[1])[0].fire('click');assert(a.paused);assert(!b.paused);
 await a.play();assert(b.paused,'native player controls must also enforce exclusive audio');
 const feedback=vm.runInContext('feedback()',context);
 assert.equal(feedback.reference_outside_voting,true);
 assert.deepEqual(Array.from(feedback.results[0].candidate_letters),['B','C']);
 assert(!feedback.results[0].candidate_letters.includes('A'));
 console.log('PASS: synchronized/restart switching, native-player exclusivity, reference voting boundary');
})().catch(e=>{console.error(e);process.exitCode=1});
