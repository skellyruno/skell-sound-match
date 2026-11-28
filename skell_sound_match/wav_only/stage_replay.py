"""Offline input-only stage replay. 44.1 kHz stereo, fixed sparse causal echo law."""
import numpy as np
from scipy import signal

SR=44100

def wet_features(x):
    m=x.mean(1);s=(x[:,0]-x[:,1])*.5
    def lp(z,f):return signal.sosfilt(signal.butter(2,f,fs=SR,output='sos').astype('f'),z,axis=0).astype('f')
    return np.column_stack((m,s,lp(m,2200),lp(s,2200),lp(m,7000),lp(s,7000))).astype('f')

def replay_echo(source,*,delays,weights,direct_gain):
    x=np.asarray(source,dtype=np.float32)
    if x.ndim!=2 or x.shape[1]!=2 or not 1<=len(x)<=3000000 or not np.isfinite(x).all() or np.max(abs(x))>32:raise ValueError('invalid stereo audio')
    if not 1<=len(delays)<=64 or list(delays)!=sorted(set(delays)) or any(type(d) is not int or not 0<=d<=132300 for d in delays):raise ValueError('invalid causal delays')
    w=np.asarray(weights,dtype='f')
    if w.shape!=(len(delays),6,2) or not np.isfinite(w).all() or np.max(abs(w))>32 or not np.isfinite(direct_gain) or abs(direct_gain)>8:raise ValueError('invalid echo coefficients')
    B=wet_features(x);y=np.zeros_like(x)
    for d,k in zip(delays,w):
        if d<len(x):y[d:]+=B[:len(x)-d]@k
    y=x*direct_gain+y
    if not np.isfinite(y).all():raise ValueError('invalid output')
    return y
