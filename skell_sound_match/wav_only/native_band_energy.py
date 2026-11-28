"""Fit exact native eight-band bell energy using aligned training audio.
Diagnostic controls only; independent native rendering is required.
"""
import numpy as np
from scipy import signal as sig
from scipy.optimize import least_squares

def fit_energy_eq(x,t,sr=44100,regularization=.15,phase_weight=.15):
 x=np.asarray(x,dtype='d');t=np.asarray(t,dtype='d')
 if x.shape!=t.shape or x.ndim!=2 or x.shape[1]!=2 or len(x)<4096 or not np.isfinite(x).all() or not np.isfinite(t).all() or not 32000<=sr<=192000:raise ValueError('invalid aligned training input')
 f,px=sig.welch(x,sr,nperseg=2048,axis=0);_,pt=sig.welch(t,sr,nperseg=2048,axis=0);_,c=sig.csd(x,t,sr,nperseg=2048,axis=0)
 px=px.sum(1);pt=pt.sum(1);c=c.sum(1);mask=(f>=70)&(f<min(18000,sr*.46));f,px,pt,c=f[mask],px[mask],pt[mask],c[mask];floor=max(pt.sum()*1e-7,1e-16);edges=np.array([35,90,185,380,820,1700,3600,7500,17500.]);be=np.array([70,150,300,600,1200,2400,4800,9600,18000.]);M=np.stack([(f>=l)&(f<h) for l,h in zip(be[:-1],be[1:])]).astype('d');q=M@pt;z=np.exp(-2j*np.pi*f/sr);z2=z*z
 if px.sum()<1e-12 or pt.sum()<1e-12:raise ValueError('insufficient spectral energy')
 # The cross-spectrum contributes only where correlation is measurable.
 coh=np.clip(abs(c)**2/np.maximum(px*pt,1e-30),0,1);norm=np.sqrt(np.maximum(px*pt,floor**2));wt=np.sqrt(coh)*np.sqrt(pt/np.maximum(pt.max(),1e-30));wt/=max(np.sqrt(np.mean(wt*wt)),1e-8)
 def response(p):
  g=p[:8];q=.4*20**p[8:16];freq=edges[:-1]*(edges[1:]/edges[:-1])**p[16:24];A=10**(g/40);a=np.sin(2*np.pi*freq/sr)/(2*q);cs=np.cos(2*np.pi*freq/sr);return np.prod((1+(a*A)[:,None]-2*cs[:,None]*z+(1-a*A)[:,None]*z2)/(1+(a/A)[:,None]-2*cs[:,None]*z+(1-a/A)[:,None]*z2),axis=0)*10**(p[24]/20)
 def residual(p):
  h=response(p);energy=10*np.log10((M@(px*abs(h)**2)+floor)/(q+floor));complex_err=wt*(h*px-c)/norm
  return np.r_[energy,regularization*p[:8],.5*(p[16:24]-.5),phase_weight*complex_err.real,phase_weight*complex_err.imag, .03*p[24]]
 init=np.r_[[0.]*8,[.2]*8,[.5]*8,np.clip(20*np.log10(np.sqrt(pt.sum()/px.sum())),-12,12)];p=least_squares(residual,init,bounds=(np.r_[[-15.]*8,[0.]*16,-18.],np.r_[[15.]*8,[1.]*16,18.]),max_nfev=40,ftol=1e-4,xtol=1e-4).x
 return dict(params=[float(v) for k in range(8) for v in (p[16+k],.5+p[k]/30)],q=p[8:16].tolist(),gain=float(p[24]),training_residual=float(np.mean(abs(10*np.log10((M@(px*abs(response(p))**2)+floor)/(q+floor))))))
