#!/usr/bin/env python3
"""Reproducible, non-invasive audio stage comparison for aligned same-take WAVs."""
import argparse, json, math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

BANDS=[(60,120),(120,250),(250,500),(500,1000),(1000,2000),(2000,4000),(4000,6500),(6500,10000),(10000,16000)]

def read_mono(p):
    x,sr=sf.read(p,always_2d=True,dtype='float64')
    if not np.isfinite(x).all():raise ValueError(f'Nonfinite audio: {p}')
    side=np.sqrt(np.mean((x[:,0]-x[:,-1])**2)) if x.shape[1]>1 else 0
    mid=np.sqrt(np.mean(x.mean(axis=1)**2))
    return x.mean(axis=1),sr,{'channels':x.shape[1],'relative_stereo_difference_db':round(float(20*np.log10((side+1e-12)/(mid+1e-12))),1)}

def spectrum(a,sr):
    f,P=signal.welch(a,sr,nperseg=8192)
    return f,P

def bands_diff(a,b,sr):
    f,P=spectrum(a,sr);fb,Q=spectrum(b,sr)
    assert np.array_equal(f,fb)
    return {f'{lo}-{hi}Hz':round(float(10*np.log10((Q[(f>=lo)&(f<hi)].mean()+1e-20)/(P[(f>=lo)&(f<hi)].mean()+1e-20))),2)
            for lo,hi in BANDS if hi<sr/2}

def framelevels(x,sr,ms=20):
    w=max(1,round(sr*ms/1000));n=len(x)//w
    return 20*np.log10(np.sqrt(np.mean(x[:n*w].reshape(n,w)**2,axis=1))+1e-12)

def main():
    ap=argparse.ArgumentParser()
    for label in ('dry','record','main_only','combined','benchmark'):ap.add_argument('--'+label,required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    out=Path(args.out)
    if out.exists():raise FileExistsError(out)
    wave={}; details={};rates={}
    for k in ('dry','record','main_only','combined','benchmark'):
        wave[k],rates[k],details[k]=read_mono(getattr(args,k))
    if len(set(rates.values()))!=1:raise ValueError('Sample rate mismatch')
    if len({len(x) for x in wave.values()})!=1:raise ValueError('Length mismatch')
    sr=next(iter(rates.values()))
    pairs=(('dry','record'),('dry','main_only'),('dry','combined'),('record','combined'),('main_only','combined'),('benchmark','combined'))
    rec=[]
    for src,tgt in pairs:
        a,b=wave[src],wave[tgt]
        da,db=framelevels(a,sr),framelevels(b,sr)
        active=(da>-45)&(db>-45)
        # Envelope correlation is robust to host delay and unaligned phase.
        rec.append({'source':src,'target':tgt,'band_changes_db':bands_diff(a,b,sr),
           'active_envelope_difference_db_median':round(float(np.median(db[active]-da[active])),3) if active.any() else None,
           'level_adjusted_band_differences_db':{k:round(float(v-np.median(db[active]-da[active])),2) for k,v in bands_diff(a,b,sr).items()} if active.any() else {},
           'active_envelope_spread_db_p90_p10_source':round(float(np.diff(np.percentile(da[active],[10,90]))[0]),3) if active.any() else None,
           'active_envelope_spread_db_p90_p10_target':round(float(np.diff(np.percentile(db[active],[10,90]))[0]),3) if active.any() else None})
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'sample_rate':sr,'duration_sec':round(len(wave['dry'])/sr,3),'files':details,'comparisons':rec},indent=2)+'\n')
    print(json.dumps({'report':str(out),'comparisons':len(rec)}))
if __name__=='__main__':main()
