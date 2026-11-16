#!/usr/bin/env python3
"""One-command presetless vocal matching: dry + reference -> safe first pass -> v0.7 trial.

Strictly offline/experimental. First-pass uses protected VocalMatch v3 heuristics;
optional verified guide JSON overlays real settings; final stage uses a bounded
training-only, same-take model. Each stage is saved and never auto-promoted.
"""
from __future__ import annotations
import argparse,json,pathlib
import numpy as np
import soundfile as sf
import vocal_match_skelly_v3 as vm
from vocal_match_v07 import refine,sha256,check_pair


def run(dry,reference,outdir,quality='off',guide=None,skip='pitch,modulation,delay,reverb'):
    outdir=pathlib.Path(outdir)
    if outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError('Output directory is not empty: preserve earlier work and choose a new directory')
    outdir.mkdir(parents=True,exist_ok=True)
    x,sr,_=vm.load(dry);target,rs,tc=vm.load(reference)
    if sr!=rs:raise ValueError('Sample-rate mismatch: export both sources at the same sample rate')
    if abs(len(x)-len(target))>sr//20:raise ValueError('Same-take timing differs by more than 50ms')
    m=min(len(x),len(target));x=x[:m];target=target[:m];tc=tc[:m]
    if m<9*sr:raise ValueError('Need at least nine seconds of vocal for two-stage matching')
    opts={s.strip() for s in skip.split(',') if s.strip()}
    invalid=opts-set(vm.EFFECTS)
    if invalid:raise ValueError(f'Unsupported skipped effect(s): {sorted(invalid)}')
    settings=vm.analyze(x,target,sr,opts,quality,mixed_channels=tc)
    if guide:
        settings=vm.apply_guide(settings,json.loads(pathlib.Path(guide).read_text()))
    y=vm.render(x,sr,settings)
    y,guard=vm.safe_output(y,sr)
    first=outdir/'VocalMatch_FirstPass.wav'
    sf.write(first,np.stack([y,y],axis=1),sr,subtype='PCM_24')
    (outdir/'VocalMatch_FirstPass_Settings.json').write_text(json.dumps(settings,indent=2,default=float))
    result={'dry_sha256':sha256(dry),'reference_sha256':sha256(reference),
            'firstpass_file':first.name,'firstpass_sha256':sha256(first),
            'firstpass_safety':guard, 'refinement':'not attempted',
            'manual_preset_guide':str(guide) if guide else None,
            'status':'offline experimental; no auto promotion'}
    try:
        # check alignment before optimization; don't mistake unrelated takes for signal processing
        check_pair(tc,np.stack([y,y],axis=1),sr)
        path,rep=refine(reference,first,outdir,'VocalMatch_Refined')
        result['refinement']={'output':path.name,'quality_gate_passed':rep['quality_gate_passed'],
                              'peak_safety':rep['safety']}
    except (ValueError,RuntimeError) as error:
        result['refinement']={'skipped':str(error),
                              'note':'First pass is preserved; this is not proof the sound cannot be matched.'}
    (outdir/'Pipeline_Report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dry',required=True);p.add_argument('--reference',required=True)
    p.add_argument('--output',required=True);p.add_argument('--quality',default='off',choices=['off','fast','normal','high'])
    p.add_argument('--guide',help='JSON with known preset overrides (optional)')
    p.add_argument('--skip',default='pitch,modulation,delay,reverb',help='Effects to leave out for main-vocal-only chain')
    a=p.parse_args()
    try:print(json.dumps(run(a.dry,a.reference,a.output,a.quality,a.guide,a.skip),indent=2))
    except Exception as exc:p.exit(1,'ERROR: '+str(exc)+'\n')
