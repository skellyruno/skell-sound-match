#!/usr/bin/env python3
"""Skelly Deuce v1.3 additive, reversible EQ / saturation audition layer.

Fully offline, same-sample-rate as model. Audio-only replay. Does not recover
original proprietary plug-in algorithms; intended for listening comparison.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy import signal
import vocalmatch_v12 as vm
import skelly_soundmatch_v08 as core


def peaking(x, sr, f, db, q):
    if db==0: return x
    if not (15 < f < .45*sr and 0.2 <= q <= 8 and abs(db) <= 12):
        raise ValueError('Invalid parametric EQ')
    A=10**(db/40); w=2*np.pi*f/sr; c=np.cos(w); alpha=np.sin(w)/(2*q)
    b=np.array([1+alpha*A,-2*c,1-alpha*A]);a=np.array([1+alpha/A,-2*c,1-alpha/A])
    return signal.lfilter(b/a[0],a/a[0],x)


def high_shelf(x,sr,f,db,q=0.7):
    if db==0:return x
    if not (20 < f < .45*sr and .3 <= q <= 2 and abs(db)<=12):raise ValueError('Invalid high shelf')
    A=10**(db/40);w=2*np.pi*f/sr;c=np.cos(w);alpha=np.sin(w)/(2*q);s=2*np.sqrt(A)*alpha
    b=A*np.array([(A+1)+(A-1)*c+s,-2*((A-1)+(A+1)*c),(A+1)+(A-1)*c-s]);a=np.array([(A+1)-(A-1)*c+s,2*((A-1)-(A+1)*c),(A+1)-(A-1)*c-s]);return signal.lfilter(b/a[0],a/a[0],x)


def render(dry,sr,model):
    if sr!=model['sample_rate']:raise ValueError('Input sample rate differs from model')
    if len(dry)>sr*90:raise ValueError('More than 90 seconds is not supported')
    if not np.isfinite(dry).all():raise ValueError('Nonfinite input')
    m=dict(model['v12_base']);m.pop('post_saturation',None)
    unshaped=vm.render(dry,sr,m)
    p=model['post']
    sat=vm.apply_post_saturation(unshaped,sr,{'threshold':p['saturation_threshold'],'oversampling':4,'mix':1.0})
    mix=p['saturation_mix']
    if not 0<=mix<=1:raise ValueError('Saturation mix must be in 0..1')
    y=(1-mix)*unshaped+mix*sat
    y=peaking(y,sr,p['mid_frequency_hz'],p['mid_gain_db'],p['mid_q'])
    y=high_shelf(y,sr,p['air_frequency_hz'],p['air_gain_db'],.7)
    if not np.isfinite(y).all():raise ValueError('Invalid result')
    return y


def export(dry,sr,model,path,lufs=-20):
    path=Path(path)
    if path.exists():raise FileExistsError(str(path))
    y=render(dry,sr,model)
    stereo=np.column_stack((y,y))
    measured=float(pyln.Meter(sr).integrated_loudness(stereo))
    if not np.isfinite(measured):raise ValueError('Invalid loudness')
    stereo*=10**((lufs-measured)/20)
    truepeak=20*np.log10(max(abs(signal.resample_poly(stereo[:,0],4,1)))+1e-12)
    if truepeak>-1:raise ValueError('Candidate exceeds -1 dBTP; do not silently attenuate')
    path.parent.mkdir(parents=True,exist_ok=True)
    sf.write(path,stereo,sr,subtype='PCM_24')
    chk,s=sf.read(path,always_2d=True)
    assert s==sr and len(chk)==len(dry) and np.isfinite(chk).all()
    return {'path':str(path),'lufs':float(pyln.Meter(sr).integrated_loudness(chk)),'truepeak_dbtp':float(20*np.log10(max(abs(signal.resample_poly(chk[:,0],4,1)))+1e-12)),'samples':len(dry)}

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--dry',required=True);a.add_argument('--model',required=True);a.add_argument('--out',required=True)
    args=a.parse_args()
    m=json.loads(Path(args.model).read_text())
    dry,sr=core.load(args.dry)
    print(json.dumps(export(dry,sr,m,args.out),indent=2))
