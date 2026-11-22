"""Create a private, self-contained four-or-many-preset blind listening HTML.

Public code. NEVER add generated HTML (which embeds private vocal audio),
reference audio, fitted filters or private manifests to a public repository.
"""
from __future__ import annotations

import argparse
import base64
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


def make_lab(manifest: Path, output: Path, *, target_lufs: float = -18.0,
             ceiling_dbtp: float = -1.2, seed: int | None = None) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite: {output}")
    if not -30.0 <= target_lufs <= -12.0 or not -12.0 <= ceiling_dbtp <= -0.5:
        raise ValueError("Unsafe target loudness/peak ceiling")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    groups_in = doc.get("groups")
    if not isinstance(groups_in, list) or not 1 <= len(groups_in) <= 100:
        raise ValueError("Expected between 1 and 100 listening groups")
    randomizer = random.Random(seed) if seed is not None else random.SystemRandom()
    out_groups: list[dict] = []
    qa: list[dict] = []
    total_bytes = 0
    ids: set[str] = set()
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
    data_json = json.dumps({"schema": SCHEMA, "groups": out_groups}, ensure_ascii=True)
    # Protect the HTML script element against injected text from local manifests.
    data_json = data_json.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = _TEMPLATE.replace("/*__PRIVATE_GROUP_DATA__*/", data_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return {"schema": SCHEMA, "groups": len(out_groups), "clips": len(qa),
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
.btnrow{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.btnrow .alt{background:#101916;color:#b7cbc0} .reveal{font-size:12px;color:#a6dca0}.identity{border:1px dashed #3c4c3f;border-radius:7px;padding:10px;font-size:12px;white-space:pre-wrap;color:#c1d6ba;display:none}.identity.visible{display:block}.control{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.control strong{font-size:13px;color:#c7dacb}.tiny{font-size:12px;color:var(--muted)}#feedbackText{height:170px;white-space:pre-wrap}footer{color:#9caf9d;font-size:13px;margin-top:30px}#status{color:var(--bright)}
@media(max-width:600px){.columns{grid-template-columns:1fr}.card{padding:14px}} 
</style></head><body><main>
<header><div class="eyebrow">SKELLY / SOUND MATCH</div><h1>BLIND LISTENING LAB</h1><p>Switch A/B/C at the same playback time. Pick your favorite and loser for each vocal, then export the results back to ChatGPT.</p><p class="info">Offline only · embedded audio · no uploads · level-matched within each comparison · source identities remain hidden until reveal</p></header>
<div id="groups"></div><section class="card"><h2>Send your winners & losers</h2><p>Export the completed feedback, or copy the text summary and paste it into our chat. You can listen again and change any vote.</p><div class="btnrow"><button id="copy">Copy feedback</button><button id="export">Download feedback JSON</button><button id="generate" class="alt">Refresh summary</button></div><p id="status" role="status"></p><textarea id="feedbackText" aria-label="Copyable listening results" readonly></textarea></section>
<footer>Historical Deuce MP3 origins remain lossy even though comparison clips are FLAC. Same-take offline research does not establish independent transfer, exact FL Studio settings, or a verified native VST3. A peak check uses 4× reconstruction, not certified BS.1770 metering.</footer>
</main><script>
const LAB = /*__PRIVATE_GROUP_DATA__*/;
const states={};
let currentAudio=null;
const root=document.getElementById('groups');
const loadState=()=>{try{return JSON.parse(localStorage.getItem('skelly-blind-feedback-v1')||'{}')}catch(_){return {}}};
const saved=loadState();
function persist(){try{localStorage.setItem('skelly-blind-feedback-v1',JSON.stringify(states))}catch(_){}}
function el(tag,cls,text){const a=document.createElement(tag);if(cls)a.className=cls;if(text!==undefined)a.textContent=text;return a}
function feedback(){const result={schema:'skelly.blind-listening.feedback.v1',results:LAB.groups.map(g=>({vocal:g.title,group_id:g.id,winner:states[g.id]?.winner||'',loser:states[g.id]?.loser||'',notes:states[g.id]?.notes||'',revealed:!!states[g.id]?.revealed}))};document.getElementById('feedbackText').value=result.results.map(r=>`${r.vocal}: WINNER ${r.winner||'?'}, LOSER ${r.loser||'?'}${r.notes?' — '+r.notes:''}`).join('\n');return result}
function addSelect(parent,g,field,caption){const lab=el('label','',caption);const select=el('select');select.setAttribute('aria-label',g.title+' '+caption);[['','Not chosen'],...g.clips.map(c=>[c.letter,c.letter])].forEach(([v,t])=>{const opt=el('option','',t);opt.value=v;select.append(opt)});select.value=states[g.id][field]||'';select.addEventListener('change',()=>{states[g.id][field]=select.value;persist();feedback()});lab.append(select);parent.append(lab)}
LAB.groups.forEach((g,index)=>{
 states[g.id]={winner:'',loser:'',notes:'',revealed:false,...saved[g.id]};
 const card=el('section','card');const top=el('div','top');const block=el('div');block.append(el('h2','',`${index+1}. ${g.title}`),el('p','',g.note));top.append(block,el('span','flag',`${g.clips.length} versions · ${g.duration}s`));card.append(top);
 const options=el('div','options');const audio=el('audio');audio.controls=true;audio.preload='none';audio.setAttribute('aria-label',g.title+' synchronized audio player');const selected=el('p','tiny','Select a version to start. Switching keeps the current time.');
 let active=null;const buttons=[];g.clips.forEach(c=>{const b=el('button','',`▶ ${c.letter}`);buttons.push(b);b.addEventListener('click',async()=>{const pos=audio.currentTime||0;const wasPlaying=!audio.paused;if(currentAudio&&currentAudio!==audio){currentAudio.pause()}if(active===c.letter){if(audio.paused){try{await audio.play()}catch(e){selected.textContent='Press Play in the audio player.'}}else{audio.pause()}return}audio.pause();audio.src=c.audio;audio.load();audio.currentTime=Math.max(0,Math.min(pos,g.duration-.1));active=c.letter;currentAudio=audio;buttons.forEach(x=>x.classList.remove('active'));b.classList.add('active');selected.textContent=`Now listening to ${c.letter}. Switch letters without restarting.`;try{await audio.play()}catch(e){selected.textContent=`Selected ${c.letter}. Press Play in the player.`}});options.append(b)});
 card.append(options,audio,selected);
 const fields=el('div','columns');addSelect(fields,g,'winner','🏆 Best / winner ');addSelect(fields,g,'loser','👎 Weakest / loser ');card.append(fields);
 const notesLabel=el('label','', 'What sounds better or worse? (tone, compression, sibilance, width, reverb, delay, artifacts)');const notes=el('textarea');notes.placeholder='Example: B is cleaner, C has better reverb, A is too harsh.';notes.value=states[g.id].notes;notes.addEventListener('input',()=>{states[g.id].notes=notes.value;persist();feedback()});notesLabel.append(notes);card.append(notesLabel);
 const controls=el('div','btnrow');const show=el('button','alt',states[g.id].revealed?'Hide identities':'Reveal identities');const identity=el('div','identity');identity.textContent=g.clips.map(c=>`${c.letter} — ${c.identity}${c.kind==='reference'?' [original reference]':''}`).join('\n');identity.classList.toggle('visible',!!states[g.id].revealed);show.addEventListener('click',()=>{states[g.id].revealed=!states[g.id].revealed;identity.classList.toggle('visible',states[g.id].revealed);show.textContent=states[g.id].revealed?'Hide identities':'Reveal identities';persist();feedback()});controls.append(show);card.append(controls,identity);root.append(card)
});
const status=document.getElementById('status');document.getElementById('generate').onclick=()=>{feedback();status.textContent='Summary refreshed.'};document.getElementById('copy').onclick=async()=>{const text=feedback().results.map(x=>`${x.vocal}: ${x.winner||'?'} beats ${x.loser||'?'}; notes: ${x.notes||'none'}`).join('\n');try{await navigator.clipboard.writeText(text);status.textContent='Feedback copied. Paste it into the ChatGPT conversation.'}catch(e){const ta=document.getElementById('feedbackText');ta.focus();ta.select();status.textContent='Select and copy the highlighted summary (Ctrl+C).'}};
document.getElementById('export').onclick=()=>{const b=new Blob([JSON.stringify(feedback(),null,2)],{type:'application/json'});const a=el('a');a.href=URL.createObjectURL(b);a.download='SKELLY_LISTENING_WINNERS_LOSERS.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),3000);status.textContent='Feedback JSON downloaded.'};
feedback();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="private JSON manifest of groups and clips")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-lufs", type=float, default=-18.0)
    parser.add_argument("--ceiling-dbtp", type=float, default=-1.2)
    parser.add_argument("--seed", type=int, default=None, help="deterministic QA only; omit for private random labels")
    args = parser.parse_args()
    stats = make_lab(args.manifest, args.output, target_lufs=args.target_lufs,
                     ceiling_dbtp=args.ceiling_dbtp, seed=args.seed)
    print(json.dumps({k: v for k, v in stats.items() if k != 'audits'}, indent=2))


if __name__ == "__main__":
    main()