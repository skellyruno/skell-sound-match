"""Offline 44.1 kHz stereo dynamic-band correction, fit on a paired training prefix.
Frozen input-only replay; two-frame delayed gain interpolation. No new echo/room.
"""
import numpy as np
from scipy import signal
SR=44100
H=441

def audio(x):
    x=np.asarray(x,dtype='f')
    if x.ndim!=2 or x.shape[1]!=2 or not 1<=len(x)<=3000000 or not np.isfinite(x).all() or np.max(abs(x))>32:
        raise ValueError('invalid stereo source')
    return x

def edges_ok(edges):
    return isinstance(edges,(tuple,list)) and 1<=len(edges)<=8 and all(type(e) is int and 40<=e<=18000 for e in edges) and list(edges)==sorted(set(edges))

def split(x,edges):
    lows=[signal.sosfilt(signal.butter(2,k,fs=SR,btype='lowpass',output='sos').astype('f'),x,axis=0).astype('f') for k in edges]
    return [lows[0]]+[v-u for u,v in zip(lows,lows[1:])]+[x-lows[-1]]

def power(x):
    n=(len(x)+H-1)//H*H;v=np.pad(x,((0,n-len(x)),(0,0)))
    return np.sqrt(np.mean(v.reshape(-1,H,2)**2,axis=(1,2)))

def smooth(x,k):return signal.lfilter([k],[1,k-1],x,zi=[(1-k)*x[0]])[0]

def descriptors(z,sc):
    e=20*np.log10(np.maximum(power(z),1e-7));e=np.clip(e-sc,-65,25)/20
    fast=smooth(e,.6);slow=smooth(e,.08)
    return np.column_stack([np.ones(len(e)),fast,slow,np.clip(fast-slow,-1.5,1.5)])

def fit(source,target,*,edges,regularization):
    z=audio(source);t=audio(target);a=len(z);n=a//H-1
    if z.shape!=t.shape or n<10 or not edges_ok(edges) or not np.isfinite(regularization) or not .001<=regularization<=2:
        raise ValueError('invalid training geometry or recipe')
    sc=20*np.log10(max(float(np.sqrt(np.mean(z.astype('d')**2))),1e-5));glob=descriptors(z,sc);out=[]
    for u,v in zip(split(z,edges),split(t,edges)):
        x=power(u)[:n];y=power(v)[:n];A=np.column_stack([glob[:n],descriptors(u,sc)[:n,1:]]);mask=(y>max(y.max()*.012,1e-6))&(x>1e-7);A=A[mask];tar=np.clip(20*np.log10((y[mask]+1e-7)/(x[mask]+1e-7)),-14,14);g=A.T@A;w=np.linalg.solve(g+np.diag([.02]+[regularization]*6)*max(1,len(A)),A.T@tar);out.append(np.clip(w,-12,12).tolist())
    return dict(edges=list(edges),scale=sc,weights=out,reg=regularization)

def replay(source,recipe,strength):
    z=audio(source);edges=recipe['edges'];sc=recipe['scale'];w=np.asarray(recipe['weights'],dtype='d')
    if not edges_ok(edges) or not np.isfinite(sc) or not -100.000001<=sc<=31 or w.shape!=(len(edges)+1,7) or not np.isfinite(w).all() or np.max(abs(w))>12 or not np.isfinite(strength) or not 0<=strength<=1:
        raise ValueError('invalid frozen recipe')
    glob=descriptors(z,sc);y=z.copy()
    for u,coef in zip(split(z,edges),w):
        A=np.column_stack([glob,descriptors(u,sc)[:,1:]]);g=np.clip(A@coef*strength,-12,12);g=smooth(g,.45)
        gain=10**(np.interp(np.arange(len(z))/H,np.arange(len(g)+2),np.r_[0.,0.,g])/20);y+=u*(gain[:,None]-1).astype('f')
    if not np.isfinite(y).all():raise ValueError('nonfinite render')
    return y
