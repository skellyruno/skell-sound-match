"""Guarded MIMO transfer from dry-derived anchors; frequency-local ridge with compact FIR support."""
import numpy as np
from scipy import signal,fft,ndimage

def fit(x,t,start,stop,reg,nfft=2048,lead=64,length=512,smooth=1.5):
    a=x[start:stop];b=t[start:stop];h=nfft//2
    if len(a)<nfft*4:raise ValueError('short training interval')
    scale=np.maximum(np.sqrt(np.mean(a*a,axis=0)),max(np.sqrt(np.mean(a*a))*.015,1e-7));a=a/scale
    w=signal.windows.hann(nfft,sym=False).astype('f');idx=np.arange(0,len(a)-nfft+1,h)
    A=fft.rfft(np.stack([a[i:i+nfft]*w[:,None] for i in idx]),axis=1);B=fft.rfft(np.stack([b[i:i+nfft]*w[:,None] for i in idx]),axis=1)
    G=np.einsum('tfi,tfj->fij',A.conj(),A,optimize=True);R=np.einsum('tfi,tfo->fio',A.conj(),B,optimize=True)
    if smooth:
        G=ndimage.gaussian_filter1d(G,smooth,axis=0);R=ndimage.gaussian_filter1d(R,smooth,axis=0)
    diag=np.diagonal(G,axis1=1,axis2=2).real;floor=max(float(np.mean(diag))*.001,1e-8);pen=np.maximum(diag,np.maximum(diag.mean(1,keepdims=True)*.03,floor));k=np.arange(x.shape[1]);G[:,k,k]+=reg*pen+1e-8
    H=np.linalg.solve(G,R)/scale[None,:,None];ir=fft.irfft(H,n=nfft,axis=0);ir=np.concatenate([ir[-lead:],ir[:length]],axis=0);fade=min(64,lead,length//2);ir[:fade]*=np.linspace(0,1,fade)[:,None,None];ir[-fade:]*=np.linspace(1,0,fade)[:,None,None];return ir.astype('f')

def apply(x,ir,lead):
    out=np.zeros((len(x),ir.shape[2]),'f')
    for i in range(x.shape[1]):
        for j in range(ir.shape[2]):out[:,j]+=signal.oaconvolve(x[:,i],ir[:,i,j])[lead:lead+len(x)]
    return out
