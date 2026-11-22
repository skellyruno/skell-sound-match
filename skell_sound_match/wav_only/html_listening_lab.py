"""Create a private, self-contained four-or-many-preset blind listening HTML.

Public code. NEVER add generated HTML (which embeds private vocal audio),
reference audio, fitted filters or private manifests to a public repository.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

SCHEMA = "skelly.blind-listening-lab.v1"


def _peak_db(audio: np.ndarray) -> float:
    return float(20 * math.log10(max(float(np.max(np.abs(signal.resample_poly(audio, 4, 1, axis=0)))), 1e-12)))


def _read_clip(path: Path, start: float, seconds: float) -> tuple[np.ndarray, int]:
    with sf.SoundFile(path) as f:
        sr = f.samplerate
        if not 32000 <= sr <= 192000 or f.channels not in (1, 2):
            raise ValueError(f"Unsupported sample format: {path.name}")
        start_frame = round(start * sr)
        end_frame = start_frame + round(seconds * sr)
        if start_frame < 0 or end_frame > f.frames:
            raise ValueError(f"Insufficient duration: {path.name}")
        f.seek(start_frame)
        audio = f.read(end_frame - start_frame, dtype="float64", always_2d=True)
    if audio.shape[0] != end_frame - start_frame or not np.isfinite(audio).all():
        raise ValueError(f"Unreadable/nonfinite audio: {path.name}")
    return audio, sr


def _safe_name(s: Any) -> str:
    text = str(s)
    if len(text) > 160 or any(ord(c) < 32 for c in text):
        raise ValueError("Invalid name/description")
    return text


def _read_prior_lab(path: Path) -> tuple[list[dict], int]:
    """Reuse verified encoded A/B clips without rerendering or changing letters.

    The source must be a trusted lab created by this generator. It contains
    private audio and must never be checked into public Git.
    """
    html = path.read_text(encoding="utf-8")
    marker = "const LAB = "
    pos = html.find(marker)
    if pos < 0:
        raise ValueError("Existing file does not contain a listening lab")
    try:
        prior, _ = json.JSONDecoder().raw_decode(html[pos+len(marker):])
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid existing lab JSON") from exc
    if not isinstance(prior, dict) or prior.get("schema") != SCHEMA or not isinstance(prior.get("groups"), list):
        raise ValueError("Existing lab schema mismatch")
    groups = prior["groups"]
    if len(groups) > 100 or len({g.get("id") for g in groups}) != len(groups):
        raise ValueError("Existing lab has invalid group identities")
    count_bytes = 0
    for group in groups:
        clips = group.get("clips", [])
        if not isinstance(clips, list) or not 2 <= len(clips) <= 12:
            raise ValueError("Existing lab has invalid clips")
        for number, clip in enumerate(clips):
            if clip.get("letter") != chr(ord("A") + number):
                raise ValueError("Existing lab has invalid letter mapping")
            uri = clip.get("audio", "")
            if not isinstance(uri, str) or not uri.startswith("data:audio/flac;base64,"):
                raise ValueError("Existing lab has an invalid private FLAC")
            try:
                count_bytes += len(base64.b64decode(uri.split(",",1)[1], validate=True))
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Existing lab contains invalid FLAC base64") from exc
    if count_bytes > 85_000_000:
        raise ValueError("Existing lab exceeds audio cap")
    return groups, count_bytes


def _session_fingerprint(groups: list[dict]) -> str:
    """Bind votes to exact randomized mappings, not only group names."""
    digest = hashlib.sha256()
    for group in groups:
        digest.update(group["id"].encode("utf-8"))
        for clip in group["clips"]:
            digest.update(clip["letter"].encode("ascii"))
            digest.update(clip["identity"].encode("utf-8"))
            # Hash the already encoded content, avoiding huge duplicate buffers.
            digest.update(hashlib.sha256(clip["audio"].encode("ascii")).digest())
    return digest.hexdigest()[:24]


def make_lab(manifest: Path, output: Path, *, target_lufs: float = -18.0,
             ceiling_dbtp: float = -1.2, seed: int | None = None,
             append_from: Path | None = None) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite: {output}")
    if not -30.0 <= target_lufs <= -12.0 or not -12.0 <= ceiling_dbtp <= -0.5:
        raise ValueError("Unsafe target loudness/peak ceiling")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    groups_in = doc.get("groups")
    if not isinstance(groups_in, list) or not 1 <= len(groups_in) <= 100:
        raise ValueError("Expected between 1 and 100 listening groups")
    randomizer = random.Random(seed) if seed is not None else random.SystemRandom()
    out_groups, total_bytes = _read_prior_lab(append_from) if append_from else ([], 0)
    if len(out_groups) + len(groups_in) > 100:
        raise ValueError("Combined lab exceeds 100 groups; split into another chapter")
    qa: list[dict] = []
    ids: set[str] = {group["id"] for group in out_groups}
    for g in groups_in:
        group_id = _safe_name(g["id"])
        if not group_id or group_id in ids:
            raise ValueError("Group IDs must be unique and nonempty")
        ids.add(group_id)
        title = _safe_name(g["title"])
        note = _safe_name(g.get("note", ""))
        clips = g.get("clips")
        if not isinstance(clips, list) or not 2 <= len(clips) <= 12:
            raise ValueError(f"Group {group_id} must have 2–12 clips")
        start = float(g.get("start", 0))
        seconds = float(g.get("seconds", 12))
        if not (math.isfinite(start) and math.isfinite(seconds) and 0 <= start <= 3600 and 2 <= seconds <= 45):
            raise ValueError("Invalid clip window")
        decoded = []
        rate = None
        shape = None
        for clip in clips:
            label = _safe_name(clip["label"])
            if clip.get("kind", "candidate") not in {"candidate", "reference", "reference-stage"}:
                raise ValueError("Unknown clip kind; explicitly mark candidate or reference")
            # Files are resolved relative to the local, private manifest.
            path = (manifest.parent / str(clip["path"])).resolve()
            x, sr = _read_clip(path, start, seconds)
            if rate is None:
                rate, shape = sr, x.shape
            if sr != rate or x.shape != shape:
                raise ValueError(f"Sample rate/channel/length mismatch in {group_id}")
            meter = pyln.Meter(sr)
            loudness = float(meter.integrated_loudness(x))
            if not math.isfinite(loudness) or loudness < -70:
                raise ValueError(f"Silent/unmeterable clip: {path.name}")
            adjusted = x * 10 ** ((target_lufs - loudness) / 20)
            decoded.append((label, adjusted, str(clip.get("kind", "candidate")), path, loudness))
        # A COMMON safety trim across every clip preserves LUFS equality.
        peaks = [_peak_db(x) for _, x, *_ in decoded]
        safety_trim_db = min(0.0, ceiling_dbtp - max(peaks))
        attenuation = 10 ** (safety_trim_db / 20)
        permutation = list(range(len(decoded)))
        randomizer.shuffle(permutation)
        outputs = []
        for blind_index, original_index in enumerate(permutation):
            label, x, kind, path, prior_lufs = decoded[original_index]
            safe = x * attenuation
            peak = _peak_db(safe)
            if peak > ceiling_dbtp + 0.025 or not np.isfinite(safe).all():
                raise ValueError("Output peak/finiteness guard failed")
            binary = io.BytesIO()
            sf.write(binary, safe, rate, format="FLAC", subtype="PCM_24")
            blob = binary.getvalue()
            decoded_back, fs = sf.read(io.BytesIO(blob), dtype="float64", always_2d=True)
            if fs != rate or decoded_back.shape != safe.shape or not np.isfinite(decoded_back).all():
                raise ValueError("Encoded FLAC roundtrip failed")
            if _peak_db(decoded_back) > ceiling_dbtp + 0.03:
                raise ValueError("Encoded FLAC exceeded peak ceiling")
            total_bytes += len(blob)
            if total_bytes > 85_000_000:
                raise ValueError("HTML exceeds 85 MB audio cap; split batches")
            outputs.append({
                "letter": chr(ord("A") + blind_index),
                "identity": label,
                "kind": kind,
                "audio": "data:audio/flac;base64," + base64.b64encode(blob).decode("ascii"),
            })
            qa.append({"group": group_id, "blind": outputs[-1]["letter"], "identity": label,
                       "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "source_lufs": round(prior_lufs, 3), "peak_dbtp_4x": round(peak, 3),
                       "encoded_flac_sha256": hashlib.sha256(blob).hexdigest()})
        out_groups.append({"id": group_id, "title": title, "note": note,
                           "duration": seconds, "rate": rate, "safety_trim_db": round(safety_trim_db, 3),
                           "clips": outputs})
    lab = {"schema": SCHEMA, "session_id": _session_fingerprint(out_groups),
           "groups": out_groups}
    data_json = json.dumps(lab, ensure_ascii=True)
    # Protect the HTML script element against injected text from local manifests.
    data_json = data_json.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = _TEMPLATE.replace("/*__PRIVATE_GROUP_DATA__*/", data_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return {"schema": SCHEMA, "groups": len(out_groups),
            "new_groups": len(groups_in), "clips": sum(len(g["clips"]) for g in out_groups),
            "new_clips": len(qa), "session_id": lab["session_id"],
            "embedded_flac_bytes": total_bytes,
            "html_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "audits": qa}


_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SKELLY // SOUND MATCH · Blind Listening Lab</title>
<style>
:root{color-scheme:dark;--bg:#080c0d;--panel:#121b1b;--edge:#2b3c38;--bright:#bbff68;--text:#f1f7ee;--muted:#9fb3a7}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 88% 0%,#173323 0,transparent 36%),var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.45}
main{max-width:1060px;margin:0 auto;padding:28px 17px 60px}.eyebrow{font-size:12px;letter-spacing:.27em;color:var(--bright)}h1{font-size:clamp(26px,4.3vw,44px);line-height:1.15;margin:8px 0}h2{font-size:20px;margin:0 0 5px}p{color:var(--muted);margin:7px 0}header{margin-bottom:22px}.info{font-size:13px;color:#b1bdb0}
.card{background:linear-gradient(135deg,#14201d,#0e1514);border:1px solid var(--edge);border-radius:14px;padding:20px;margin:18px 0}.top{display:flex;align-items:start;justify-content:space-between;gap:15px;flex-wrap:wrap}.flag{color:#b9df98;font-size:12px;border:1px solid #38503b;padding:5px 10px;border-radius:99px}
button,select,textarea{font:inherit;color:var(--text);background:#1b2824;border:1px solid #496153;border-radius:7px}button{cursor:pointer;padding:9px 13px}button:hover{border-color:#bbff68}button.active{background:#263f2c;border:2px solid var(--bright);padding:8px 12px}button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid var(--bright);outline-offset:2px}
.options{display:flex;gap:8px;flex-wrap:wrap;margin:17px 0}audio{width:100%;margin:8px 0 6px}label{display:block;font-size:13px;color:var(--muted);margin:10px 0 5px}select{padding:9px;min-width:155px;max-width:100%}.columns{display:grid;grid-template-columns:1fr 1fr;gap:12px}.columns>*{min-width:0}textarea{width:100%;min-height:70px;resize:vertical;padding:10px;background:#111b17}
.btnrow{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.btnrow .alt{background:#101916;color:#b7cbc0} .reveal{font-size:12px;color:#a6dca0}.identity{border:1px dashed #3c4c3f;border-radius:7px;padding:10px;font-size:12px;white-space:pre-wrap;color:#c1d6ba;display:none}.identity.visible{display:block}.control{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.control strong{font-size:13px;color:#c7dacb}.quickjump{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 6px}.quickjump a{color:#d5ecd5;text-decoration:none;font-size:12px;background:#12201a;border:1px solid #344d3e;border-radius:6px;padding:6px 9px}.quickjump a:hover,.quickjump a:focus-visible{border-color:var(--bright)}.review-progress{font-size:13px;color:var(--bright);margin:7px 0 12px}.tiny{font-size:12px;color:var(--muted)}#feedbackText{height:170px;white-space:pre-wrap}footer{color:#9caf9d;font-size:13px;margin-top:30px}#status{color:var(--bright)}
.reference-pane{border:1px solid #45624c;background:#11251c;border-radius:10px;padding:11px 13px;margin:14px 0 9px}.reference-pane strong{font-size:12px;color:var(--bright);letter-spacing:.06em}.reference-buttons{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}.reference-buttons button{background:#173422;color:#e8ffe0;border-color:#568159}.reference-buttons button.active{background:#315f37}.candidates-heading{font-size:12px;letter-spacing:.1em;color:#d4e9cb;margin:16px 0 5px}.score-note{font-size:13px;color:#b4c9b6}.issue-grid{display:flex;gap:5px;flex-wrap:wrap;margin:8px 0 3px}.issue-chip{display:inline-flex;align-items:center;gap:5px;margin:0;padding:5px 8px;border:1px solid #355244;border-radius:6px;font-size:12px;background:#101c17;color:#d7e8d7}.issue-chip input{accent-color:#baff7c}.single-rating{margin:8px 0 3px}.single-rating label{display:flex;flex-direction:column;align-items:flex-start;gap:6px}.single-rating select{display:block;min-width:230px;max-width:100%}.columns label select{display:block;margin-top:6px}.reference-note{font-size:11px;color:#b9cfc0;margin-top:5px}.issue-label{font-size:12px;color:#d0e2d0;margin-top:12px}
@media(max-width:600px){.columns{grid-template-columns:1fr}.card{padding:14px}} 
</style></head><body><main>
<header><div class="eyebrow">SKELLY / SOUND MATCH</div><h1>BLIND LISTENING LAB</h1><p><strong>ORIGINAL is your reference, never a voting choice.</strong> Compare the candidate letters against it. Switch at the same point to compare a phrase, or choose restart mode. Rate how close it sounds, then pick winners only when there are multiple candidates.</p><p class="info">Offline · private embedded audio · matched levels within each round · originals are always separate from candidate votes</p><label>Switch playback<select id="playbackMode" aria-label="Switch playback"><option value="aligned">Same point · synchronized</option><option value="restart">Restart at 0:00</option></select></label></header>
<nav class="quickjump" id="jump" aria-label="Jump to listening round"></nav><p class="review-progress" id="progress"></p>
<div id="groups"></div><section class="card"><h2>Send your winners & losers</h2><p>Export the completed feedback, or copy the text summary and paste it into our chat. You can listen again and change any vote.</p><div class="btnrow"><button id="copy">Copy feedback</button><button id="export">Download feedback JSON</button><button id="generate" class="alt">Refresh summary</button></div><p id="status" role="status"></p><textarea id="feedbackText" aria-label="Copyable listening results" readonly></textarea></section>
<footer>Comparison votes exclude original/reference clips. A match rating is subjective and not a native plugin validation. Historical Deuce MP3 origins remain lossy even though comparison clips are FLAC. Same-take offline research does not establish independent transfer, exact FL Studio settings, or a verified native VST3. A peak check uses 4× reconstruction, not certified BS.1770 metering.</footer>
</main><script>
const LAB = /*__PRIVATE_GROUP_DATA__*/;
const states={};
let currentAudio=null;
const root=document.getElementById('groups');
// New version prevents reference votes from an old HTML being reused as candidate votes.
const storageKey='skelly-blind-feedback-v3-reference-outside-'+LAB.session_id;
const loadState=()=>{try{return JSON.parse(localStorage.getItem(storageKey)||'{}')}catch(_){return {}}};
const saved=loadState();
const ISSUE_TAGS=['Too bright','Too dark / muffled','Needs upfront presence','Too quiet / weak','Compression wrong','Stereo / width wrong','Delay / reverb wrong','Modulation / movement missing','Gating / noise','Artifacts / harshness'];
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(states))}catch(_){}}
function el(tag,cls,text){const a=document.createElement(tag);if(cls)a.className=cls;if(text!==undefined)a.textContent=text;return a}
const isReference=c=>c.kind==='reference'||c.kind==='reference-stage';
const candidates=g=>g.clips.filter(c=>!isReference(c));
function feedback(){
 const result={schema:'skelly.blind-listening.feedback.v3',session_id:LAB.session_id,reference_outside_voting:true,
 results:LAB.groups.map(g=>{
  const st=states[g.id]||{};
  const allowed=new Set(candidates(g).map(c=>c.letter));
  const winner=st.uncertain?'':(allowed.has(st.winner)?st.winner:'');
  const loser=st.uncertain?'':(allowed.has(st.loser)?st.loser:'');
  return {vocal:g.title,group_id:g.id,reference:'ORIGINAL',candidate_letters:[...allowed],
   winner,loser,match_rating:st.match_rating||'',issues:st.issues||[],
   uncertain:!!st.uncertain,notes:st.notes||'',revealed:!!st.revealed};
 })};
 const summary=result.results.map(r=>{
  const verdict=r.candidate_letters.length===1?'Candidate '+r.candidate_letters[0]+', match '+(r.match_rating||'?')+'/5':
     'WINNER '+(r.winner||'?')+', LOSER '+(r.loser||'?')+', match '+(r.match_rating||'?')+'/5';
  return `${r.vocal}: ${r.uncertain?'UNSURE · ':''}${verdict} | issues: ${r.issues.join(', ')||'none'}${r.notes?' — '+r.notes:''}`;
 }).join('\n');
 document.getElementById('feedbackText').value=summary;
 document.getElementById('progress').textContent=`${result.results.filter(r=>r.uncertain||r.winner||r.loser||r.match_rating||r.notes||r.issues.length).length}/${LAB.groups.length} rounds reviewed`;
 return result;
}
function addSelect(parent,g,field,caption,eligible){
 const lab=el('label','',caption),select=el('select');select.setAttribute('aria-label',g.title+' '+caption);
 [['','Not chosen'],...eligible.map(c=>[c.letter,c.letter])].forEach(([v,t])=>{const o=el('option','',t);o.value=v;select.append(o)});
 select.value=states[g.id][field]||'';
 select.addEventListener('change',()=>{
  states[g.id][field]=select.value;
  if(select.value){states[g.id].uncertain=false;const check=parent.parentElement.querySelector('input[type=checkbox][data-uncertain]');if(check)check.checked=false;
    const opposite=field==='winner'?'loser':'winner';if(states[g.id][opposite]===select.value){states[g.id][opposite]='';const other=parent.querySelectorAll('select')[field==='winner'?1:0];if(other)other.value='';}}
  persist();feedback();
 });lab.append(select);parent.append(lab);
}
LAB.groups.forEach((g,index)=>{
 const refs=g.clips.filter(isReference),choices=candidates(g),allowed=new Set(choices.map(c=>c.letter));
 const prior=saved[g.id]||{};
 states[g.id]={winner:'',loser:'',match_rating:'',issues:[],notes:'',uncertain:false,revealed:false,...prior};
 for(const f of ['winner','loser'])if(!allowed.has(states[g.id][f]))states[g.id][f]='';
 if(!Array.isArray(states[g.id].issues))states[g.id].issues=[];
 if(!['','1','2','3','4','5'].includes(String(states[g.id].match_rating)))states[g.id].match_rating='';
 const card=el('section','card');card.id=`round-${index+1}`;
 const jump=el('a','',`${index+1} · ${g.title.split(' · ')[0]}`);jump.href=`#round-${index+1}`;document.getElementById('jump').append(jump);
 const top=el('div','top'),block=el('div');block.append(el('h2','',`${index+1}. ${g.title}`),el('p','',g.note));top.append(block,el('span','flag',`${choices.length} candidate${choices.length===1?'':'s'} · ${g.duration}s`));card.append(top);
 const audio=el('audio');audio.controls=true;audio.preload='none';audio.setAttribute('aria-label',g.title+' comparison audio');
 audio.addEventListener('play',()=>{if(currentAudio&&currentAudio!==audio)currentAudio.pause();currentAudio=audio});
 const selected=el('p','tiny','Select ORIGINAL or a candidate. Switch mode applies within this round.');
 const buttons=[];let active=null,selectionToken=0;
 function createPlayButton(c,caption,container){
  const b=el('button','',caption);b.type='button';b.setAttribute('aria-pressed','false');buttons.push(b);
  b.addEventListener('click',async()=>{
   if(currentAudio&&currentAudio!==audio)currentAudio.pause();
   if(active===c.letter){currentAudio=audio;if(audio.paused){try{await audio.play()}catch(e){selected.textContent='Press Play in the player.'}}else audio.pause();return}
   const position=document.getElementById('playbackMode').value==='aligned'&&active!==null&&Number.isFinite(audio.currentTime)?audio.currentTime:0;
   const token=++selectionToken;audio.pause();audio.src=c.audio;audio.load();
   const resetAtStart=()=>{if(token===selectionToken){try{if(position>0)audio.currentTime=Math.min(position,Number.isFinite(audio.duration)?Math.max(0,audio.duration-.01):position);else audio.currentTime=0}catch(_){}}};
   audio.addEventListener('loadedmetadata',resetAtStart,{once:true});resetAtStart();active=c.letter;currentAudio=audio;
   buttons.forEach(x=>{x.classList.remove('active');x.setAttribute('aria-pressed','false')});b.classList.add('active');b.setAttribute('aria-pressed','true');
   selected.textContent=`Now playing ${caption.replace('▶ ','')} at ${position.toFixed(1)}s.`;
   try{await audio.play()}catch(e){selected.textContent=`Selected ${caption} at 0:00. Press Play in the player.`}
  });container.append(b);
 }
 if(refs.length){
  const refBox=el('div','reference-pane');refBox.append(el('strong','', 'ORIGINAL / SOURCE REFERENCES — NOT IN THE VOTE'));
  const refBtns=el('div','reference-buttons');
  refs.forEach(c=>createPlayButton(c,c.kind==='reference'?'▶ ORIGINAL':'▶ SOURCE CONTEXT',refBtns));
  refBox.append(refBtns,el('div','reference-note','Use these as the sound targets or source context. Only candidate letters below can win or lose.'));
  card.append(refBox);
 }
 card.append(el('div','candidates-heading','CANDIDATES — COMPARE AGAINST ORIGINAL'));
 const opts=el('div','options');choices.forEach(c=>createPlayButton(c,'▶ '+c.letter,opts));card.append(opts,audio,selected);
 if(choices.length>=2){const fields=el('div','columns');addSelect(fields,g,'winner','🏆 Closest candidate',choices);addSelect(fields,g,'loser','👎 Weakest candidate',choices);card.append(fields)}
 else {card.append(el('p','score-note','One candidate: no forced winner/loser. Rate how closely it matches ORIGINAL.'));}
 const single=el('div','single-rating'),ratingLabel=el('label','', 'How close to the original is the best/current candidate?');const score=el('select');score.setAttribute('aria-label',g.title+' similarity rating');
 [['','Not rated'],['1','1 / 5 · Very far'],['2','2 / 5 · Far'],['3','3 / 5 · Getting close'],['4','4 / 5 · Close'],['5','5 / 5 · Nearly exact']].forEach(([v,t])=>{const option=el('option','',t);option.value=v;score.append(option)});score.value=states[g.id].match_rating||'';
 score.addEventListener('change',()=>{states[g.id].match_rating=score.value;persist();feedback()});ratingLabel.append(score);single.append(ratingLabel);card.append(single);
 const uncertainLabel=el('label','tiny'),uncertain=el('input');uncertain.type='checkbox';uncertain.dataset.uncertain='1';uncertain.checked=!!states[g.id].uncertain;uncertain.setAttribute('aria-label',g.title+' not sure yet');
 uncertain.addEventListener('change',()=>{states[g.id].uncertain=uncertain.checked;if(uncertain.checked){states[g.id].winner='';states[g.id].loser='';card.querySelectorAll('.columns select').forEach(s=>s.value='')}persist();feedback()});
 uncertainLabel.append(uncertain,document.createTextNode(' Unsure / not ready to choose'));card.append(uncertainLabel);
 card.append(el('div','issue-label','What is missing? (optional · choose multiple)'));
 const issueGrid=el('div','issue-grid');ISSUE_TAGS.forEach(tag=>{const lab=el('label','issue-chip'),box=el('input');box.type='checkbox';box.checked=states[g.id].issues.includes(tag);
  box.addEventListener('change',()=>{const values=new Set(states[g.id].issues);if(box.checked)values.add(tag);else values.delete(tag);states[g.id].issues=[...values];persist();feedback()});lab.append(box,document.createTextNode(tag));issueGrid.append(lab)});card.append(issueGrid);
 const notesLabel=el('label','', 'Notes: what should I fix?');const notes=el('textarea');notes.placeholder='Example: B needs more upfront presence, but less top-end boost.';notes.value=states[g.id].notes;
 notes.addEventListener('input',()=>{states[g.id].notes=notes.value;persist();feedback()});notesLabel.append(notes);card.append(notesLabel);
 const controls=el('div','btnrow'),show=el('button','alt',states[g.id].revealed?'Hide identities':'Reveal candidate identities'),identity=el('div','identity');
 identity.textContent=g.clips.map(c=>`${isReference(c)?'ORIGINAL / SOURCE CONTEXT':c.letter} — ${c.identity}${c.kind==='reference'?' [original reference]':''}`).join('\n');
 identity.classList.toggle('visible',!!states[g.id].revealed);show.addEventListener('click',()=>{states[g.id].revealed=!states[g.id].revealed;identity.classList.toggle('visible',states[g.id].revealed);show.textContent=states[g.id].revealed?'Hide identities':'Reveal candidate identities';persist();feedback()});
 controls.append(show);card.append(controls,identity);root.append(card);
});
const status=document.getElementById('status');
document.getElementById('generate').onclick=()=>{feedback();status.textContent='Summary refreshed.'};
document.getElementById('copy').onclick=async()=>{const summary=`SESSION ${LAB.session_id}\nORIGINAL is never a voting option.\n`+document.getElementById('feedbackText').value;try{await navigator.clipboard.writeText(summary);status.textContent='Feedback copied. Paste it into the chat.'}catch(e){const ta=document.getElementById('feedbackText');ta.focus();ta.select();status.textContent='Select and copy the highlighted summary (Ctrl+C).'}};
document.getElementById('export').onclick=()=>{const b=new Blob([JSON.stringify(feedback(),null,2)],{type:'application/json'});const a=el('a');a.href=URL.createObjectURL(b);a.download='SKELLY_LISTENING_FEEDBACK_CANDIDATES_ONLY.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),3000);status.textContent='Feedback JSON downloaded.'};
feedback();
</script></body></html>'''


def remix_lab(source_html: Path, output_html: Path) -> dict:
    """Rebuild a trusted private listening lab with the latest UI only.

    Reuses all private FLAC bytes and every original A/B letter. Neither DSP nor
    loudness is altered. This avoids a costly re-encode or changing older votes.
    """
    if output_html.exists():
        raise FileExistsError(f"Refusing to overwrite: {output_html}")
    groups, audio_bytes = _read_prior_lab(source_html)
    data = {"schema": SCHEMA, "session_id": _session_fingerprint(groups), "groups": groups}
    escaped = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = _TEMPLATE.replace("/*__PRIVATE_GROUP_DATA__*/", escaped)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")
    return {"schema": SCHEMA, "groups": len(groups),
            "clips": sum(len(group["clips"]) for group in groups),
            "session_id": data["session_id"], "audio_bytes": audio_bytes,
            "html_bytes": output_html.stat().st_size,
            "html_sha256": hashlib.sha256(output_html.read_bytes()).hexdigest()}


def externalize_lab(source_html: Path, output_html: Path) -> dict:
    """Convert trusted private self-contained HTML to fast, offline HTML+FLAC.

    The standalone source is unchanged. The destination and its audio folder
    must not exist. Files are named only by round/letter/hash to avoid
    disclosing source identities through filenames before blind listening.
    """
    if output_html.exists():
        raise FileExistsError(f"Refusing to overwrite: {output_html}")
    asset_dir = output_html.parent / (output_html.stem + "_audio")
    if asset_dir.exists():
        raise FileExistsError(f"Refusing to overwrite: {asset_dir}")
    groups, total_bytes = _read_prior_lab(source_html)
    old_html = source_html.read_text(encoding="utf-8")
    pos = old_html.index("const LAB = ") + len("const LAB = ")
    old_doc, _ = json.JSONDecoder().raw_decode(old_html[pos:])
    session_id = old_doc.get("session_id") or _session_fingerprint(groups)
    # Preflight all bytes and names before creating any outputs.
    assets: list[tuple[str,bytes]] = []
    fast_groups: list[dict] = []
    for group_index, group in enumerate(groups, start=1):
        converted = {**group, "clips": []}
        for clip in group["clips"]:
            blob = base64.b64decode(clip["audio"].split(",",1)[1], validate=True)
            # This is a privacy-preserving blind filename, not a label.
            filename = f"round_{group_index:03d}_{clip['letter']}_{hashlib.sha256(blob).hexdigest()[:12]}.flac"
            relative = f"{asset_dir.name}/{filename}"
            assets.append((filename, blob))
            converted["clips"].append({**clip, "audio": relative})
        fast_groups.append(converted)
    if len(assets) != sum(len(g['clips']) for g in groups) or sum(len(b) for _,b in assets) != total_bytes:
        raise ValueError("Private FLAC export mismatch")
    fast_doc = {"schema": SCHEMA, "session_id": session_id, "groups": fast_groups}
    escaped = json.dumps(fast_doc, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = _TEMPLATE.replace("/*__PRIVATE_GROUP_DATA__*/", escaped)
    html = html.replace("Offline only · embedded audio", "Offline only · local FLAC assets")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir()
    for filename, blob in assets:
        (asset_dir/filename).write_bytes(blob)
    output_html.write_text(html,encoding="utf-8")
    return {"schema": SCHEMA, "groups": len(groups), "clips": len(assets),
            "session_id": session_id, "asset_dir": str(asset_dir),
            "audio_bytes": total_bytes, "html_bytes": output_html.stat().st_size,
            "html_sha256": hashlib.sha256(output_html.read_bytes()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", help="private manifest or previous lab for --remix/--externalize")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-lufs", type=float, default=-18.0)
    parser.add_argument("--ceiling-dbtp", type=float, default=-1.2)
    parser.add_argument("--seed", type=int, default=None, help="deterministic QA only; omit for private random labels")
    parser.add_argument("--append-from", type=Path, help="reuse existing private HTML clips and their letter mapping")
    parser.add_argument("--externalize", action="store_true", help="convert existing private HTML into small HTML plus local FLAC assets")
    parser.add_argument("--remix", action="store_true", help="rebuild HTML UI from existing private HTML without re-encoding audio")
    args = parser.parse_args()
    if args.manifest is None:
        parser.error("Manifest or previous HTML is required")
    if args.remix and args.externalize:
        parser.error("Use --remix or --externalize, not both")
    if args.remix:
        if args.append_from is not None:
            parser.error("--remix and --append-from are separate operations")
        stats = remix_lab(args.manifest, args.output)
    elif args.externalize:
        if args.append_from is not None:
            parser.error("--externalize and --append-from are separate operations")
        stats = externalize_lab(args.manifest, args.output)
    else:
        schema=json.loads(args.manifest.read_text(encoding='utf-8')).get('schema')
        if schema=='skelly.verified-listening-manifest.v1':
            if args.append_from is not None:parser.error('Audited sessions use explicit version provenance, not legacy append')
            from .verified_listening_lab import make_lab as make_verified_lab
            stats=make_verified_lab(args.manifest,args.output)
        else:
            stats = make_lab(args.manifest, args.output, target_lufs=args.target_lufs,
                             ceiling_dbtp=args.ceiling_dbtp, seed=args.seed,
                             append_from=args.append_from)
    print(json.dumps({k: v for k, v in stats.items() if k != 'audits'}, indent=2))


if __name__ == "__main__":
    main()
