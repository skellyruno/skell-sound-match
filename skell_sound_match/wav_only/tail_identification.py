"""Earlier-region echo timing diagnostics for aligned paired recordings.
These are lag candidates, not proof of an exact delay or replay model.
Validate actual native effect renders on a separately reserved region.
"""
import numpy as np
from scipy import signal as sig

def measure_tail_lags(source, target, sample_rate=44100):
 """Earlier-training echo candidates from audio correlation AND envelope residual.
 Discrete lags only; envelope regression ranks potential repeated echoes, not a replay model.
 """
 source=np.asarray(source,dtype=np.float64);target=np.asarray(target,dtype=np.float64)
 if source.shape!=target.shape or source.ndim!=2 or source.shape[1]!=2 or len(source)<100 or not 8000<=sample_rate<=192000:
  raise ValueError("expected aligned stereo audio and a supported sample rate")
 if not np.isfinite(source).all() or not np.isfinite(target).all():raise ValueError("nonfinite input")
 if np.mean(source**2)<1e-16 or np.mean(target**2)<1e-16:return []
 SR=sample_rate
 n=len(source); m=source.mean(1); tm=target.mean(1); ts=(target[:,0]-target[:,1])*.5
 out=[]; lo=int(.05*SR);hi=min(int(1.8*SR),n//2)
 if hi>lo:
  den=max(np.dot(m,m),1e-10)
  corr=[sig.correlate(ch,m,method='fft')[n-1:n+hi]/den for ch in (tm,ts)]
  z=np.maximum(abs(corr[0]),abs(corr[1]));peaks=sig.find_peaks(z[lo:hi],distance=int(.05*SR))[0]+lo
  for j in sorted(peaks,key=lambda j:-z[j])[:4]:out.append((j/SR,float(z[j]),'audio'))
 # Estimate candidates by power-envelope regression from mono/side energies.
 hop=max(1,round(SR*.01));N=n//hop
 if N>20:
  v=np.mean(source[:N*hop].reshape(N,hop,2)**2,axis=(1,2));y=np.mean(target[:N*hop].reshape(N,hop,2)**2,axis=(1,2));v=v/(v.max()+1e-12);y=y/(y.max()+1e-12)
  # Fit nonnegative energy residual to preceding source frames and multiple echoes.
  a=np.arange(N); lags=np.arange(0,min(N//2,181));X=np.column_stack([np.where(a>=k,v[np.maximum(0,a-k)],0) for k in lags]);w=1/np.sqrt(y+.02)
  from scipy.optimize import nnls
  active=[0]; residual=y.copy()
  for _ in range(5):
   scores=(X*w[:,None]).T@(residual*w);scores[:5]=-np.inf
   for k in active:scores[max(0,k-3):k+4]=-np.inf
   k=int(np.argmax(scores));
   if scores[k]<=0:break
   active.append(k);coefs,_=nnls(X[:,active]*w[:,None],y*w);residual=y-X[:,active]@coefs
  for k,c in zip(active[1:],coefs[1:] if len(active)>1 else []):
   if c>.008:out.append((k*hop/SR,float(np.sqrt(c)),'envelope'))
 return out

