"""Causal all-pass phase diagnostic. No native deployment; output derived only from source."""
import numpy as np
from scipy import signal, optimize

def fit_allpass(source,target,sr=44100,sections=2):
    x=np.asarray(source,float); t=np.asarray(target,float)
    if x.shape!=t.shape or x.ndim!=2 or x.shape[1]!=2 or len(x)<4096 or not np.isfinite(x).all() or not np.isfinite(t).all() or not 32000<=sr<=192000 or sections not in (1,2,3):raise ValueError('invalid aligned audio')
    f,p=signal.welch(x,sr,nperseg=2048,axis=0);_,q=signal.welch(t,sr,nperseg=2048,axis=0);_,c=signal.csd(x,t,sr,nperseg=2048,axis=0);p=p.sum(1);q=q.sum(1);c=c.sum(1)
    mask=(f>=70)&(f<=min(15000,sr*.45))&(p>p.max()*1e-7)&(q>q.max()*1e-7);f,p,q,c=f[mask],p[mask],q[mask],c[mask]
    if len(f)<8:raise ValueError('insufficient phase support')
    z=np.exp(-2j*np.pi*f/sr);z2=z*z;coh=np.clip(abs(c)**2/np.maximum(p*q,1e-30),0,1);wanted=c/np.maximum(abs(c),1e-30);w=np.sqrt(coh)*np.sqrt(q/np.max(q));w/=max(np.sqrt(np.mean(w*w)),1e-8)
    def h(v,pol):
        fc=np.exp(v[:sections]);Q=np.exp(v[sections:]);omega=2*np.pi*fc/sr;alpha=np.sin(omega)/(2*Q);cs=np.cos(omega);a1=-2*cs/(1+alpha);a2=(1-alpha)/(1+alpha);return pol*np.prod((a2[:,None]+a1[:,None]*z+z2)/(1+a1[:,None]*z+a2[:,None]*z2),axis=0)
    def obj(v,pol):
        e=w*(h(v,pol)-wanted);return np.r_[e.real,e.imag]
    best=None
    for pol in [1,-1]:
        for start in [np.geomspace(100,2400,sections),np.geomspace(400,6500,sections)]:
            init=np.log(np.r_[start,[.7]*sections]);fit=optimize.least_squares(obj,init,args=(pol,),bounds=(np.log(np.r_[[40]*sections,[.25]*sections]),np.log(np.r_[[14000]*sections,[8.]*sections])),max_nfev=40,ftol=1e-4,xtol=1e-4)
            err=float(np.mean(fit.fun**2));v=np.exp(fit.x)
            if best is None or err<best['fit_error']:best=dict(frequency=v[:sections].tolist(),q=v[sections:].tolist(),polarity=pol,fit_error=err,coherence=float(np.mean(coh)))
    return best

def apply_allpass(source,settings,sr=44100):
    x=np.asarray(source,float);sos=[]
    for f,q in zip(settings['frequency'],settings['q']):
        w=2*np.pi*np.clip(f,40,sr*.45)/sr;a=np.sin(w)/(2*q);a1=-2*np.cos(w)/(1+a);a2=(1-a)/(1+a);sos.append([a2,a1,1,1,a1,a2])
    return (signal.sosfilt(sos,x,axis=0)*settings['polarity']).astype(np.float32)
