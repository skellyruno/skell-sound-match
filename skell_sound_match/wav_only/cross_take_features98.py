"""Independent cross-performance style descriptors, offline 44.1 kHz."""
import numpy as np
from scipy import signal, fft
SR=44100; N=2048; H=512
EDGES=np.array([70,160,320,640,1280,2560,5120,10240,18000]); CENTERS=np.sqrt(EDGES[:-1]*EDGES[1:]); F=fft.rfftfreq(N,1/SR)
B=np.clip(np.searchsorted(EDGES,F,side='right')-1,0,len(CENTERS)-1); WIN=signal.windows.hann(N,sym=False).astype('f')
Q=np.array([.1,.25,.5,.75,.9]); EPS=1e-10
def spec(x):
    m=np.column_stack([x.mean(1),(x[:,0]-x[:,1])*.5]); a=np.pad(m,((N//2,N//2+H),(0,0))); z=np.lib.stride_tricks.sliding_window_view(a,N,axis=0)[::H];return fft.rfft(z*WIN,axis=-1)
def synth(z,n):
    fr=fft.irfft(z,n=N,axis=-1)*WIN; out=np.zeros((len(z)*H+N,2),'f'); w=np.zeros(len(out),'f')
    for i,a in enumerate(fr):out[i*H:i*H+N]+=a.T;w[i*H:i*H+N]+=WIN**2
    v=out[N//2:N//2+n]/np.maximum(w[N//2:N//2+n,None],1e-8);return np.column_stack([v[:,0]+v[:,1],v[:,0]-v[:,1]])
def power(z):
    p=np.abs(z)**2 / (N**2); return np.stack([p[:,:,B==k].sum(-1) for k in range(len(CENTERS))],axis=-1)
def descriptors(p):
    e=p[:,0].sum(-1); e_db=10*np.log10(e+EPS);active=e_db>max(-65,np.percentile(e_db,90)-32)
    if active.sum()<20:raise ValueError('too few active frames')
    v=p[active]; levels=e_db[active]; med=np.median(levels); rel=10*np.log10((v[:,0]+EPS)/(v[:,0].sum(1,keepdims=True)+EPS));groups=np.digitize(levels,np.quantile(levels,[.33,.67]));tone=np.stack([np.median(rel[groups==i],axis=0) if (groups==i).any() else np.median(rel,axis=0) for i in range(3)])
    stereo=10*np.log10((v[:,1].sum(0)+EPS)/(v[:,0].sum(0)+EPS));global_side=10*np.log10((v[:,1].sum()+EPS)/(v[:,0].sum()+EPS))
    return dict(tone=tone,level=np.quantile(levels-med,Q),side=stereo,global_side=global_side,median=med,cut=np.quantile(levels,[.33,.67]),active=int(active.sum()))
