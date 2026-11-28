"""Offline context-conditioned M/S energy correction. Target-free replay.
No vendor parity or real-time claim. Centered STFT uses future samples.
"""
import numpy as np
from scipy import signal, fft, ndimage
N=2048; H=256; SR=44100
EDGES=np.array([0,70,150,300,600,1200,2400,4800,9600,18000,22051.])
CENTERS=np.sqrt(np.maximum(EDGES[:-1],10)*EDGES[1:]); FREQ=np.arange(N//2+1)*SR/N
NB=len(CENTERS); BAND=np.clip(np.searchsorted(EDGES,FREQ,side='right')-1,0,NB-1)
WIN=signal.windows.hann(N,sym=False).astype('f')
def ms(x):return np.column_stack([x.mean(1),(x[:,0]-x[:,1])*.5]).astype('f')
def lr(x):return np.column_stack([x[:,0]+x[:,1],x[:,0]-x[:,1]]).astype('f')
def spec(x):
    v=np.lib.stride_tricks.sliding_window_view(np.pad(ms(x),((N//2,N//2+H),(0,0))),N,axis=0)[::H];return fft.rfft(v*WIN[None,None,:],axis=-1).astype('complex64')
def power(z):return np.stack([np.sum(abs(z[:,:,BAND==j])**2,axis=2) for j in range(NB)],axis=2)
def synth(z,n):
    v=fft.irfft(z,n=N,axis=-1)*WIN[None,None,:];out=np.zeros(((len(v)-1)*H+N,2),'f');w=np.zeros(len(out),'f')
    for i,a in enumerate(v):out[i*H:i*H+N]+=a.T;w[i*H:i*H+N]+=WIN**2
    return lr(out[N//2:N//2+n]/np.maximum(w[N//2:N//2+n,None],1e-8))
def smooth(a,ms):
    alpha=np.exp(-H/(SR*.001*ms));return signal.lfilter([1-alpha],[1,-alpha],a,axis=0).astype('f')
def features(p,q,c,k):
    d=p[:,0,k]+p[:,1,k];s=q[:,c,k];dt=p.sum((1,2));st=q.sum((1,2));log=lambda a:np.clip(.5*np.log(np.maximum(a,1e-7)),-8,9)
    D,S,T,U=map(log,(d,s,dt,st));A=[D,S,T,U,log(smooth(d,60)),log(smooth(s,60)),log(smooth(d,250)),log(smooth(s,250)),D-T,S-U,S-log(smooth(s,150)),T-log(smooth(dt,150))]
    return np.column_stack(A).astype('f')
def prepare(x,y):return power(spec(x)),power(spec(y))
def fit(p,q,r,st,stop,reg,kind):
    ix=np.arange(len(p))*H;mask=(ix>=st+N)&(ix<stop-N)
    if mask.sum()<16:raise ValueError('insufficient training frames')
    M=np.zeros((2,NB,13),'f');mu=np.zeros((2,NB,12),'f');sd=np.ones_like(mu)
    for c in range(2):
        for k in range(NB):
            a,b=q[mask,c,k],r[mask,c,k];floor=max(float(np.mean(b))*1e-4,1e-8)
            M[c,k,0]=np.clip(.5*np.log((b.sum()+floor)/(a.sum()+floor)),-2,2)
            if not kind:continue
            V=features(p,q,c,k)[mask];mu[c,k]=V.mean(0);sd[c,k]=np.maximum(V.std(0),.5);V=np.clip((V-mu[c,k])/sd[c,k],-4,4)
            A=np.column_stack([np.ones(len(V)),V]);target=np.clip(.5*np.log((b+floor)/(a+floor)),-2,2);w=np.clip(np.sqrt(b/(b+floor*25)),.03,1);G=A.T@(A*w[:,None]);R=A.T@(w*target);pen=np.maximum(np.diag(G),1)*reg;pen[0]=.001;M[c,k]=np.linalg.solve(G+np.diag(pen),R)
    return M,mu,sd

def gains(p,q,model,amount):
    M,mu,sd=model;g=np.empty(q.shape,'f')
    for c in range(2):
        for k in range(NB):
            V=np.clip((features(p,q,c,k)-mu[c,k])/sd[c,k],-4,4);g[:,c,k]=M[c,k,0]+V@M[c,k,1:]
    return np.exp(ndimage.gaussian_filter1d(np.clip(g*amount,-2,2),1.5,axis=0))
def apply(x,y,model,amount,pq=None):
    if not amount:return y.copy()
    p,q=prepare(x,y) if pq is None else pq;g=gains(p,q,model,amount);Z=spec(y)
    i=np.clip(np.searchsorted(CENTERS,FREQ)-1,0,NB-2);w=np.clip((np.log(np.maximum(FREQ,1))-np.log(CENTERS[i]))/(np.log(CENTERS[i+1])-np.log(CENTERS[i])),0,1).astype('f')
    for c in range(2):Z[:,c,:]*=g[:,c,i]*(1-w)+g[:,c,i+1]*w
    return synth(Z,len(y))
