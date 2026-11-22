"""Causal multi-input stereo echo identification; private learned models only."""
from __future__ import annotations
import numpy as np
from scipy import signal,linalg


def _basis(x,index,delay,repeats):
    positions=[(0,c) for c in range(x.shape[1])]
    positions += [(round(delay*k)+offset,c) for k in range(1,repeats+1) for offset in (-16,-8,0,8,16) for c in range(x.shape[1])]
    a=np.column_stack([np.where(index-lag>=0,x[np.clip(index-lag,0,len(x)-1),ch],0.) for lag,ch in positions])
    return a,positions


def fit(source,effect_print,sr,train_end,search=(.08,1.3)):
    x=np.asarray(source);y=np.asarray(effect_print)
    if x.shape!=y.shape or x.ndim!=2 or x.shape[1]!=2 or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Expected finite stereo stage pair')
    if not 3*sr<train_end<=len(x):raise ValueError('Insufficient training')
    end=round(train_end*.7);wet=y-x;low=round(search[0]*sr);high=min(round(search[1]*sr),end-1)
    strengths=np.zeros(high-low)
    for c in range(2):
        for d in range(2):
            cc=signal.fftconvolve(wet[:end,c],x[:end,d][::-1])[end-1:]
            strengths+=np.abs(cc[low:high])
    delay=low+int(np.argmax(strengths));train=np.arange(0,end,8);val=np.arange(round(train_end*.76),train_end,8)
    best=None
    for repeats in (2,3,4):
        a,_=_basis(x,train,delay,repeats);b,_=_basis(x,val,delay,repeats);gram=a.T@a
        for ridge in (.001,.01,.1):
            w=linalg.solve(gram+max(float(np.trace(gram))/len(gram)*ridge,1e-12)*np.eye(len(gram)),a.T@wet[train],assume_a='pos')
            err=float(np.mean((b@w-wet[val])**2))
            if best is None or err<best[0]:best=(err,repeats,ridge)
    _,repeats,ridge=best;idx=np.arange(0,train_end,8);a,positions=_basis(x,idx,delay,repeats);gram=a.T@a
    w=linalg.solve(gram+max(float(np.trace(gram))/len(gram)*ridge,1e-12)*np.eye(len(gram)),a.T@wet[idx],assume_a='pos')
    h=np.zeros((max(lag for lag,ch in positions)+1,2,2))
    for row,(lag,ch) in zip(w,positions):h[lag,ch]+=row
    return {'sample_rate':sr,'impulse':h},{'first_echo_ms':delay/sr*1000,'repeats':repeats,'ridge':ridge,'selection':'nested train-only stereo-input echo fit'}


def render(source,sr,model):
    h=model['impulse'];x=np.asarray(source)
    if model['sample_rate']!=sr or x.ndim!=2 or x.shape[1]!=2 or not np.isfinite(x).all() or not np.isfinite(h).all():raise ValueError('Invalid stereo replay')
    z=x.copy()
    for c in range(2):
        for d in range(2):z[:,d]+=signal.fftconvolve(x[:,c],h[:,c,d])[:len(x)]
    return z
