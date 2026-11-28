"""Source-audited private listening lab. Generated HTML must never enter Git."""
from __future__ import annotations
import argparse,base64,hashlib,io,json,math,random
from pathlib import Path
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from .html_listening_lab import _read_clip,_peak_db
from .pairing_audit import audit_group,file_sha


def make_lab(manifest,output):
    manifest=Path(manifest);output=Path(output)
    if output.exists():raise FileExistsError('Refusing to overwrite a listening session')
    doc=json.loads(manifest.read_text(encoding='utf-8'))
    if doc.get('schema')!='skelly.verified-listening-manifest.v1':raise ValueError('Expected provenance manifest')
    if not isinstance(doc.get('groups'),list) or not 1<=len(doc['groups'])<=100:
        raise ValueError('Expected 1-100 comparisons')
    groups=[];audits=[];total=0;seen=set()
    for group in doc['groups']:
        if group['id'] in seen:raise ValueError('Duplicate comparison identity')
        seen.add(group['id']);audit=audit_group(group,manifest.parent)
        candidates=list(group.get('candidates',[]));random.SystemRandom().shuffle(candidates)
        if len(candidates)>12 or len({c['version_id'] for c in candidates})!=len(candidates):
            raise ValueError('Invalid candidate versions')
        entries=[group['reference'],*candidates]
        data=[];levels=[];hashes=[]
        for entry in entries:
            offset=int(entry.get('offset_samples',0))/audit['sample_rate']
            audio,sr=_read_clip((manifest.parent/entry['path']).resolve(),float(group['start'])+offset,float(group['seconds']))
            loudness=float(pyln.Meter(sr).integrated_loudness(audio))
            if not math.isfinite(loudness) or loudness<-70:raise ValueError('Silent/unmeterable comparison')
            data.append(audio*10**((-18-loudness)/20));levels.append(loudness)
        trim=min(0.,-1.2-max(_peak_db(a) for a in data));encoded=[]
        for a in data:
            a=a*10**(trim/20);buffer=io.BytesIO();sf.write(buffer,a,sr,format='FLAC',subtype='PCM_24')
            blob=buffer.getvalue();back,rate=sf.read(io.BytesIO(blob),always_2d=True)
            lufs=float(pyln.Meter(rate).integrated_loudness(back));peak=_peak_db(back)
            if peak>-1.17 or not np.isfinite(back).all():raise ValueError('FLAC safety check failed')
            total+=len(blob)
            if total>85_000_000:raise ValueError('Embedded audio cap exceeded')
            encoded.append('data:audio/flac;base64,'+base64.b64encode(blob).decode())
            hashes.append(hashlib.sha256(blob).hexdigest())
            audit.setdefault('encoded_checks',[]).append({'lufs':lufs,'estimated_peak_dbtp_4x':peak,'flac_sha256':hashes[-1]})
        measured=[x['lufs'] for x in audit['encoded_checks']]
        if max(measured)-min(measured)>.05:raise ValueError('Encoded comparison loudness mismatch')
        choices=[{'letter':chr(65+i),'version_id':c['version_id'],'identity':c['identity'],
                  'sha256':c['sha256'],'audio':encoded[i+1]} for i,c in enumerate(candidates)]
        groups.append({'id':group['id'],'preset':group['preset'],'stage':group['stage'],
                       'listen_for':group['listen_for'],'status':audit['status'],'issues':audit['issues'],
                       'seconds':group['seconds'],'recording_id':group['recording_id'],
                       'reference':{'label':group['reference']['label'],'sha256':audit['reference_sha256'],'audio':encoded[0]},
                       'candidates':choices})
        audit['id']=group['id'];audits.append(audit)
    payload={'schema':'skelly.verified-listening-lab.v1','groups':groups,
             'prior_sessions':doc.get('prior_sessions',[])}
    # References have no letter. Role, take, stage, hashes and mappings bind votes.
    identity=[{k:g[k] for k in ('id','recording_id','stage','status')}|{
        'reference_sha256':g['reference']['sha256'],
        'candidates':[(c['letter'],c['version_id'],c['sha256']) for c in g['candidates']]} for g in groups]
    payload['session_id']=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
    safe=json.dumps(payload,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(TEMPLATE.replace('/*__LAB__*/',safe),encoding='utf-8')
    return {'session_id':payload['session_id'],'comparisons':len(groups),
            'pairing_pass':sum(g['status']=='PAIRING_CHECKS_PASS' for g in groups),
            'unverified':sum(g['status']!='PAIRING_CHECKS_PASS' for g in groups),
            'clips':sum(1+len(g['candidates']) for g in groups),'audits':audits,
            'html_sha256':file_sha(output),'embedded_bytes':total}


TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Skelly Sound Match</title><style>
:root{color-scheme:dark;--bg:#090e0d;--panel:#141d19;--edge:#34463b;--green:#b8ef83;--text:#f1f5ee;--muted:#afbdaf}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,Segoe UI,sans-serif}main{max-width:940px;margin:auto;padding:25px 18px 80px}h1{font-size:32px;margin:4px 0}h2{font-size:23px;margin:4px 0}h3{font-size:16px;margin:0 0 10px}p{color:var(--muted)}button,select,textarea,input{font:inherit}button,select,textarea{color:var(--text);background:#1d2c22;border:1px solid #526a58;border-radius:8px;padding:10px 14px}button{cursor:pointer}button:hover{border-color:var(--green)}button[aria-pressed=true]{background:#304d30;border:2px solid var(--green);padding:9px 13px}button:focus-visible,select:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--green);outline-offset:3px}button:disabled{opacity:.5;cursor:default}.eyebrow,.stage{color:var(--green);font-size:12px;letter-spacing:.14em;text-transform:uppercase}.nav{display:flex;gap:7px;flex-wrap:wrap;margin:20px 0}.nav button{font-size:13px;padding:8px 11px}.panel{border:1px solid var(--edge);background:var(--panel);border-radius:13px;padding:20px;margin:15px 0}.ref{border-color:#6d925b;background:#16251a}.ref h3{color:var(--green);letter-spacing:.1em;font-size:13px}.versions{display:flex;gap:10px;flex-wrap:wrap}.versions button{min-width:80px}.meta{font-size:13px;color:var(--muted)}.warning{color:#f2d197;background:#30291a;border:1px solid #786038;border-radius:8px;padding:12px}.transport{position:sticky;top:0;z-index:2;background:#0d1711;border:1px solid #455d49;border-radius:12px;padding:14px;margin:18px 0;box-shadow:0 8px 20px #0008}.transport-row{display:flex;gap:12px;align-items:center}.transport strong{flex:1}.transport input{width:100%;accent-color:var(--green);margin-top:13px}.row{display:flex;gap:15px;flex-wrap:wrap;align-items:end}.row label{flex:1;min-width:150px}label{display:block;color:var(--muted);font-size:14px;margin:12px 0 6px}select{display:block;width:100%;margin-top:5px}textarea{width:100%;min-height:90px;resize:vertical;display:block;margin-top:6px}.feedback{margin-top:20px}#status{color:var(--green)}#reveal{white-space:pre-wrap;color:#d6e7c7}a{color:var(--green)}.hidden{display:none!important}@media(max-width:600px){main{padding:15px 12px 60px}h1{font-size:26px}.panel{padding:15px}.transport-row{flex-wrap:wrap}.transport strong{flex-basis:65%}.row{display:block}.nav button{padding:7px 9px}.transport{top:6px}}
</style></head><body><main><header><div class="eyebrow">SKELLY / SOUND MATCH</div><h1>Listen. Compare. Rate.</h1><p id="reviewCount"></p></header><nav class="nav" id="nav" aria-label="Vocal comparisons"></nav>
<div class="transport"><div class="transport-row"><button id="playPause" aria-label="Play or pause active audio">Play</button><strong id="activeLabel">Choose original or a candidate</strong><span id="time" class="meta">0:00 / 0:00</span></div><input id="progress" aria-label="Playback progress" type="range" min="0" max="1" step="0.01" value="0"><audio id="player" preload="none"></audio></div>
<section id="comparison"><div class="stage" id="stage"></div><h2 id="preset"></h2><p id="listenFor"></p><p id="verification" class="meta"></p><div id="warning" class="warning hidden"></div>
<div class="panel ref"><h3>ORIGINAL REFERENCE</h3><p id="refLabel" class="meta"></p><button id="original">Play original reference</button></div>
<div class="panel"><h3>Recreated versions</h3><div id="candidates" class="versions"></div><p id="candidateNote" class="meta"></p></div>
<div class="panel feedback"><h3>Your review</h3><div id="voteFields" class="row"><label>Closest candidate<select id="winner" aria-label="Closest candidate"></select></label><label>Weakest candidate<select id="loser" aria-label="Weakest candidate"></select></label></div><label>Similarity to original<select id="rating" aria-label="Similarity to original"><option value="">Not rated</option><option value="1">1 / 5 · Very different</option><option value="2">2 / 5 · Far</option><option value="3">3 / 5 · Getting close</option><option value="4">4 / 5 · Close</option><option value="5">5 / 5 · Nearly exact</option></select></label><label><input type="checkbox" id="uncertain"> Too close to call / unsure</label><label>What sounds different?<textarea id="notes" placeholder="Tone, compression, stereo, tails, movement or artifacts…"></textarea></label><button id="submit">Submit this review</button><p id="reveal"></p></div></section>
<button id="export">Download all feedback</button><p id="status" role="status"></p><p class="meta">Private offline research. No recording or vote is sent anywhere. Unverified pairings cannot receive candidate votes. Same-take measurements do not establish independent-performance or native-plugin accuracy.</p></main><script>
const LAB=/*__LAB__*/;
const $=id=>document.getElementById(id),audio=$('player'),key='skelly-verified-feedback-v1-'+LAB.session_id;
let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(_){}
const reviews={};for(const g of LAB.groups){const old=saved[g.id]||{};const allowed=g.candidates.map(c=>c.letter);reviews[g.id]={winner:allowed.includes(old.winner)?old.winner:'',loser:allowed.includes(old.loser)?old.loser:'',rating:['1','2','3','4','5'].includes(old.rating)?old.rating:'',notes:typeof old.notes==='string'?old.notes:'',uncertain:!!old.uncertain,submitted:!!old.submitted};if(g.status!=='PAIRING_CHECKS_PASS'){reviews[g.id].winner='';reviews[g.id].loser='';reviews[g.id].rating=''} }
let index=0,active=null,token=0;const buttons=[];
const persist=()=>{try{localStorage.setItem(key,JSON.stringify(reviews))}catch(_){}updateCount()};
const current=()=>LAB.groups[index];const review=()=>reviews[current().id];
function updateCount(){$('reviewCount').textContent=Object.values(reviews).filter(r=>r.submitted).length+' / '+LAB.groups.length+' comparisons reviewed';buttons.forEach((b,i)=>b.textContent=LAB.groups[i].preset+(reviews[LAB.groups[i].id].submitted?' ✓':' · needs review'))}
function clock(t){return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0')}
function updateProgress(){const d=Number.isFinite(audio.duration)?audio.duration:current().seconds;$('progress').max=d||1;$('progress').value=audio.currentTime||0;$('time').textContent=clock(audio.currentTime||0)+' / '+clock(d);$('playPause').textContent=audio.paused?'Play':'Pause'}
function stopReset(){++token;audio.pause();try{audio.currentTime=0}catch(_){}$('progress').value=0;active=null;audio.removeAttribute('src');audio.load();$('activeLabel').textContent='Choose original or a candidate';updateProgress()}
function markActive(){document.querySelectorAll('[data-version]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.version===active)))}
async function choose(version){if(active===version){if(audio.paused){try{await audio.play()}catch(_){$('status').textContent='Press Play to start audio.'}}else audio.pause();updateProgress();return}
 stopReset();const mine=++token,g=current(),clip=version==='original'?g.reference:g.candidates.find(c=>c.letter===version);if(!clip)return;active=version;audio.src=clip.audio;audio.load();try{audio.currentTime=0}catch(_){}$('activeLabel').textContent=g.preset+' · '+(version==='original'?'ORIGINAL':('Candidate '+version));markActive();
 const reset=()=>{if(mine===token){audio.currentTime=0;updateProgress()}};audio.addEventListener('loadedmetadata',reset,{once:true});try{await audio.play()}catch(_){if(mine===token)$('status').textContent='Audio selected. Press Play.'}if(mine===token)updateProgress()}
function fillSelect(id,choices){const s=$(id);s.replaceChildren();for(const value of ['',...choices]){const o=document.createElement('option');o.value=value;o.textContent=value||'Not chosen';s.append(o)}}
function showRound(n){stopReset();index=n;const g=current(),r=review();$('preset').textContent=g.preset;$('stage').textContent=g.stage.replaceAll('_',' ');$('listenFor').textContent=g.listen_for;$('refLabel').textContent=g.reference.label;$('verification').textContent=g.status==='PAIRING_CHECKS_PASS'?'Source, stage, format and timing checks passed':'UNVERIFIED comparison';$('warning').classList.toggle('hidden',g.status==='PAIRING_CHECKS_PASS');$('warning').textContent='UNVERIFIED: '+g.issues.join('. ');$('candidates').replaceChildren();for(const c of g.candidates){const b=document.createElement('button');b.textContent='Candidate '+c.letter;b.dataset.version=c.letter;b.setAttribute('aria-pressed','false');b.onclick=()=>choose(c.letter);$('candidates').append(b)}
 $('original').dataset.version='original';$('original').setAttribute('aria-pressed','false');$('candidateNote').textContent=g.candidates.length===1?'One recreation: rate its similarity.':g.candidates.length?'Compare each recreation against the original.':'No accepted recreation yet. Original available for context.';
 const eligible=g.status==='PAIRING_CHECKS_PASS',letters=g.candidates.map(c=>c.letter);fillSelect('winner',letters);fillSelect('loser',letters);$('voteFields').classList.toggle('hidden',letters.length<2);for(const id of ['winner','loser','rating','uncertain'])$(id).disabled=!eligible;$('winner').value=r.winner;$('loser').value=r.loser;$('rating').value=r.rating;$('notes').value=r.notes;$('uncertain').checked=r.uncertain;$('reveal').textContent=r.submitted?g.candidates.map(c=>c.letter+' — '+c.identity).join('\n'):'';$('submit').textContent=r.submitted?'Update review':'Submit this review';buttons.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===n)));updateProgress();updateCount()}
LAB.groups.forEach((g,i)=>{const b=document.createElement('button');b.onclick=()=>showRound(i);buttons.push(b);$('nav').append(b)});
$('original').onclick=()=>choose('original');$('playPause').onclick=()=>active?choose(active):choose('original');
audio.addEventListener('timeupdate',updateProgress);audio.addEventListener('pause',updateProgress);audio.addEventListener('play',updateProgress);audio.addEventListener('ended',updateProgress);
$('progress').oninput=()=>{if(active)audio.currentTime=Number($('progress').value);updateProgress()};
for(const field of ['winner','loser'])$(field).onchange=()=>{const r=review();r[field]=$(field).value;const opposite=field==='winner'?'loser':'winner';if(r[field]&&r[field]===r[opposite]){r[opposite]='';$(opposite).value=''}if(r[field]){r.uncertain=false;$('uncertain').checked=false}persist()};
$('rating').onchange=()=>{review().rating=$('rating').value;persist()};$('notes').oninput=()=>{review().notes=$('notes').value;persist()};$('uncertain').onchange=()=>{const r=review();r.uncertain=$('uncertain').checked;if(r.uncertain){r.winner='';r.loser='';$('winner').value='';$('loser').value=''}persist()};
$('submit').onclick=()=>{review().submitted=true;persist();$('reveal').textContent=current().candidates.map(c=>c.letter+' — '+c.identity).join('\n');$('submit').textContent='Update review';$('status').textContent='Review saved on this device. Download feedback when ready.'};
function feedback(){return {schema:'skelly.verified-feedback.v1',session_id:LAB.session_id,results:LAB.groups.map(g=>({group_id:g.id,preset:g.preset,stage:g.stage,pairing_status:g.status,reference_sha256:g.reference.sha256,candidate_versions:g.candidates.map(c=>({letter:c.letter,version_id:c.version_id,sha256:c.sha256})),...reviews[g.id]}))}}
$('export').onclick=()=>{const blob=new Blob([JSON.stringify(feedback(),null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='SKELLY_LISTENING_FEEDBACK.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000);$('status').textContent='Feedback downloaded.'};showRound(0);
</script></body></html>'''


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=make_lab(a.manifest,a.output);print(json.dumps({k:v for k,v in r.items() if k!='audits'},indent=2))
