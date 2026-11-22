"""Battle UI for private full-sound attempts. No original receives a letter."""
import json
from pathlib import Path
from .html_listening_lab import make_lab


def build(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    temporary=output.with_suffix('.encoding.html')
    qa=make_lab(Path(manifest),temporary)
    text=temporary.read_text(encoding='utf-8')
    prior=json.JSONDecoder().raw_decode(text.split('const LAB = ',1)[1])[0]
    groups=[]
    for g in prior['groups']:
        refs=[c for c in g['clips'] if c['kind']=='reference']
        choices=[c for c in g['clips'] if c['kind']=='candidate']
        if len(refs)!=1 or len(choices)!=3:raise ValueError('Battle needs one original and three recreated contenders')
        groups.append({'id':g['id'],'title':g['title'],'note':g['note'],'reference':refs[0]['audio'],
                       'candidates':[{'letter':chr(65+i),'identity':c['identity'],'audio':c['audio']} for i,c in enumerate(choices)]})
    doc={'session_id':prior['session_id'],'groups':groups}
    payload=json.dumps(doc,ensure_ascii=True).replace('<','\\u003c')
    output.write_text(TEMPLATE.replace('/*DATA*/',payload),encoding='utf-8')
    temporary.unlink()
    return qa


TEMPLATE=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Skelly Sound Battles</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#0b110d;color:#f1f5ef;font:17px/1.5 system-ui;margin:0}main{max-width:740px;margin:30px auto;padding:18px}h1{font-size:34px;margin:4px 0}h2{margin:0}p{color:#b6c5b6}.panel{background:#17231a;border:1px solid #40593e;padding:22px;border-radius:16px;margin:18px 0}button,select,textarea{font:inherit;color:inherit;background:#243b27;border:1px solid #64845a;border-radius:9px;padding:13px;cursor:pointer}button:hover{border-color:#bded8d}button[aria-pressed=true]{outline:3px solid #bded8d;background:#365c34}.row{display:flex;gap:14px}.row>*{flex:1}.pick{font-size:22px;font-weight:700}.muted{font-size:13px;color:#bfceb9}audio,textarea,select{width:100%}textarea{min-height:60px;cursor:text}#status{color:#c5f79a}#next{background:#bddf93;color:#10220b;font-weight:700;width:100%;margin-top:14px}.badge{color:#c6ef9e;letter-spacing:.12em;font-size:12px}#export{margin-top:14px;width:100%}@media(max-width:500px){main{margin:8px auto;padding:12px}.panel{padding:16px}h1{font-size:28px}.row{gap:9px}button{padding:12px 8px}}
</style><main><div class="badge">SKELLY / SOUND BATTLES</div><h1>Which recreation wins?</h1><p id="progress"></p><select id="round" aria-label="Choose vocal preset"></select><section class="panel"><h2 id="title"></h2><p class="muted" id="note"></p><button id="original" style="width:100%">▶ ORIGINAL REFERENCE</button><p class="muted">Listen to the original, then compare A, B and C.</p><div class="row"><button id="a" class="pick">▶ A</button><button id="b" class="pick">▶ B</button><button id="c" class="pick">▶ C</button></div><audio id="audio" controls preload="none"></audio></section><section class="panel"><h2>Pick your winner</h2><div class="row"><button id="voteA">A wins</button><button id="voteB">B wins</button><button id="voteC">C wins</button></div><p class="muted">Eliminate the weakest; keep the other two for the next round.</p><div class="row"><button id="dropA">Drop A</button><button id="dropB">Drop B</button><button id="dropC">Drop C</button></div><button id="tie" style="width:100%;margin-top:12px">Too close / neither is close yet</button><p><textarea id="notes" placeholder="Optional: what should improve?" aria-label="Listening notes"></textarea></p><button id="next">Save pick & next battle →</button><p id="status" role="status"></p></section><button id="export">Download my picks</button><p class="muted">Experimental full-sound attempts, not approved exact recreations. Missing effects remain noted. Every version change starts at 0:00. Original is never a contender.</p></main><script>
const LAB=/*DATA*/;const $=id=>document.getElementById(id),audio=$('audio'),key='skelly-battles-'+LAB.session_id;let votes={};try{votes=JSON.parse(localStorage.getItem(key)||'{}')}catch(_){}let n=0,active=null;
const group=()=>LAB.groups[n],state=()=>votes[group().id]||(votes[group().id]={winner:'',eliminate:'',notes:''});
function save(){try{localStorage.setItem(key,JSON.stringify(votes))}catch(_){}$('progress').textContent=Object.values(votes).filter(v=>v.winner).length+' / '+LAB.groups.length+' battles picked'}
function stop(){audio.pause();try{audio.currentTime=0}catch(_){}audio.removeAttribute('src');audio.load();active=null;for(const id of ['original','a','b','c'])$(id).setAttribute('aria-pressed','false')}
async function play(which){if(active===which){if(audio.paused)await audio.play().catch(()=>{});else audio.pause();return}stop();active=which;audio.src=which==='original'?group().reference:group().candidates[which.charCodeAt(0)-65].audio;audio.load();audio.currentTime=0;$(which==='original'?'original':which.toLowerCase()).setAttribute('aria-pressed','true');await audio.play().catch(()=>{})}
function mark(){for(const [id,v] of [['voteA','A'],['voteB','B'],['voteC','C'],['dropA','drop_A'],['dropB','drop_B'],['dropC','drop_C'],['tie','tie']])$(id).setAttribute('aria-pressed',String(v.startsWith('drop_')?state().eliminate===v.slice(5):state().winner===v))}
function show(i){stop();n=i;$('round').value=String(i);$('title').textContent=group().title;$('note').textContent=group().note;$('notes').value=state().notes;$('status').textContent='';mark();save()}
LAB.groups.forEach((g,i)=>{const o=document.createElement('option');o.value=i;o.textContent=g.title;$('round').append(o)});$('round').onchange=()=>show(Number($('round').value));$('original').onclick=()=>play('original');$('a').onclick=()=>play('A');$('b').onclick=()=>play('B');$('c').onclick=()=>play('C');for(const [id,v] of [['voteA','A'],['voteB','B'],['voteC','C'],['dropA','drop_A'],['dropB','drop_B'],['dropC','drop_C'],['tie','tie']])$(id).onclick=()=>{if(v.startsWith('drop_')){state().eliminate=v.slice(5);if(state().winner===state().eliminate)state().winner=''}else{state().winner=v;if(state().eliminate===v)state().eliminate=''}mark();save()};$('notes').oninput=()=>{state().notes=$('notes').value;save()};$('next').onclick=()=>{if(!state().winner||(state().winner!=='tie'&&!state().eliminate)){$('status').textContent='Choose a winner and weakest, or none are close.';return}save();if(n<LAB.groups.length-1)show(n+1);else{stop();$('status').textContent='All battles reviewed. Download your picks below.'}};
$('export').onclick=()=>{const result={schema:'skelly.sound-battle-feedback.v1',session_id:LAB.session_id,results:LAB.groups.map(g=>({group_id:g.id,preset:g.title,winner:votes[g.id]?.winner||'',eliminate:votes[g.id]?.eliminate||'',survivors:g.candidates.filter(c=>c.letter!==votes[g.id]?.eliminate).map(c=>c.identity),notes:votes[g.id]?.notes||'',candidate_versions:g.candidates.map(c=>({letter:c.letter,identity:c.identity}))}))};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));a.download='SKELLY_BATTLE_PICKS.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000)};show(0);
</script></html>'''
