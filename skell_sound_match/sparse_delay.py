"""Audio-only paired echo identification; a small transferable linear model.

Fit aligned same-take stage prints only. Training residual correlations propose
causal taps; ridge regression fits direct and 3.5 kHz low-pass stereo matrices.
No saved settings, reference audio segments or vendor DSP are required to render.
"""
from dataclasses import dataclass
import numpy as np
from scipy import signal
from .reference_transfer import _audio


def shifted(x,lag):
    if lag==0:return x
    z=np.zeros_like(x);z[lag:]=x[:-lag];return z


def basis(x,rate):
    lo=signal.sosfilt(signal.butter(1,3500,fs=rate,output='sos'),x,axis=0).astype('float32')
    return np.column_stack([x,lo])


@dataclass(frozen=True)
class SparseDelay:
    rate: int
    lags: tuple
    matrix: tuple

    def checked(self):
        c=np.asarray(self.matrix,dtype=float)
        if (not isinstance(self.rate,int) or not 32000<=self.rate<=192000
                or not 1<=len(self.lags)<=6 or self.lags[0]!=0
                or len(set(self.lags))!=len(self.lags)
                or any(type(k)!=int or k<0 or k>int(2.2*self.rate) for k in self.lags)
                or c.shape!=(4*len(self.lags),2) or not np.isfinite(c).all() or np.max(abs(c))>8):
            raise ValueError('invalid sparse delay recipe')
        return c

    def render(self,x,rate):
        c=self.checked();x=_audio(x,rate);a=basis(x,rate)
        lags=[int(round(k*rate/self.rate)) for k in self.lags]
        return sum(shifted(a,k)@c[i*4:(i+1)*4] for i,k in enumerate(lags)).astype('float32')


def fit(source,target,rate,max_taps=5):
    """Fit only training stage pairs. Caller verifies alignment and holds out data."""
    x=_audio(source,rate);y=_audio(target,rate)
    if x.shape!=y.shape or type(max_taps)!=int or not 0<=max_taps<=5:
        raise ValueError('invalid pair or tap count')
    n=len(x);xx=basis(x,rate);yy=y
    mask=(np.abs(x)<.9999).all(axis=1)&(np.abs(yy)<.9999).all(axis=1)
    idx=np.flatnonzero(mask)[::4];lags=[0]
    if len(idx)<512 or np.sum(x[idx]**2)<1e-10 or np.sum(y[idx]**2)<1e-10:
        raise ValueError('insufficient unclipped training signal')
    def solve(lags):
        a=np.column_stack([shifted(xx,k) for k in lags])[idx].astype('float64');b=yy[idx].astype('float64');g=a.T@a;ridge=max(1e-12,np.trace(g)/len(g)*1e-6)
        return np.linalg.solve(g+ridge*np.eye(len(g)),a.T@b)
    def render(lags,c):
        return sum(shifted(xx,k)@c[i*4:(i+1)*4] for i,k in enumerate(lags))
    c=solve(lags);prev=np.mean((render(lags,c)[mask]-yy[mask])**2)
    for _ in range(max_taps):
        residual=(yy-render(lags,c))*mask[:,None];limit=min(int(2.2*rate),n-1);corr=np.zeros(limit+1)
        for i in range(2):
            for j in range(2):
                v=signal.correlate(residual[:,j],xx[:,i],mode='full',method='fft')[n-1:n+limit];corr+=v*v
        corr[:int(rate*.065)]=0
        for k in lags:corr[max(0,k-int(rate*.004)):min(len(corr),k+int(rate*.004)+1)]=0
        lag=int(np.argmax(corr))
        if corr[lag]<=0:break
        q=lags+[lag];coef=solve(q);out=render(q,coef);err=np.mean((out[mask]-yy[mask])**2)
        if err>=prev*.995 or np.max(abs(coef))>8:break
        lags,c,prev=q,coef,err
    r=SparseDelay(int(rate),tuple(lags),tuple(tuple(row) for row in c.tolist()));r.checked();return r
