// Logic regression harness; not a substitute for real-browser inspection.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.listeners={};this.currentTime=0;this.duration=6;this.paused=true;this.value='';this.textContent='';this.classList={toggle(){}};}
 append(...n){this.children.push(...n)}replaceChildren(...n){this.children=n}
 setAttribute(k,v){this.attributes[k]=v}removeAttribute(k){delete this.attributes[k];if(k==='src')this.src=''}
 addEventListener(k,f){(this.listeners[k]??=[]).push(f)}
 pause(){this.paused=true}load(){this.currentTime=0}async play(){this.paused=false}
 click(){if(this.onclick)return this.onclick()}
}
const ids={};for(const id of ['player','reviewCount','nav','playPause','activeLabel','time','progress','stage','preset','listenFor','verification','warning','refLabel','original','candidates','candidateNote','voteFields','winner','loser','rating','uncertain','notes','submit','reveal','export','status'])ids[id]=new Element(id==='player'?'audio':'div');
const document={getElementById:id=>ids[id],createElement:tag=>new Element(tag),querySelectorAll:()=>[ids.original,...ids.candidates.children]};
const state={};const context={document,localStorage:{getItem(){return null},setItem(k,v){state[k]=v}},console,URL,Blob,setTimeout};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
const run=code=>vm.runInContext(code,context);
(async()=>{
 assert.equal(ids.reveal.textContent,'');assert.equal(run('LAB.groups[0].reference.letter'),undefined);
 await ids.original.click();ids.player.currentTime=2;
 await ids.candidates.children[0].click();assert.equal(ids.player.currentTime,0);
 ids.player.currentTime=1.5;await ids.candidates.children[0].click();assert(ids.player.paused);assert.equal(ids.player.currentTime,1.5);
 await ids.candidates.children[0].click();assert(!ids.player.paused);assert.equal(ids.player.currentTime,1.5);
 ids.nav.children[1].click();assert(ids.player.paused);assert.equal(ids.player.currentTime,0);assert.equal(ids.player.src,'');
 await ids.playPause.click();assert.equal(run('active'),'original');assert.equal(ids.player.currentTime,0);
 ids.rating.value='4';ids.rating.onchange();ids.submit.click();assert(ids.reveal.textContent.includes('private-version'));
 const feedback=run('feedback()');assert.equal(feedback.results[1].rating,'4');assert(feedback.results[1].submitted);
 ids.nav.children[2].click();assert(ids.rating.disabled);assert(ids.winner.disabled);assert.equal(run('feedback().results[2].winner'),'');
 assert.equal(run('document.getElementById("player")===audio'),true);
 console.log('PASS reset/reference/candidate/round/pause-resume/blind-review/export/unverified-gates');
})().catch(e=>{console.error(e);process.exitCode=1});
