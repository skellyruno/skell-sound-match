"""Estimate recurrent echo timing from isolated aligned pre/post stage recordings.
The fitted taps are diagnostics, never replayed as target-dependent audio.
"""
import numpy as np
from scipy import signal as sig

def estimate_period(x,t,sr=44100,lo=.08,hi=.6):
 """Select a recurrence period on aligned training samples only. Multiple repeats reduce ambiguity."""
 x=np.asarray(x,dtype='d');t=np.asarray(t,dtype='d')
 if x.shape!=t.shape or x.ndim!=2 or x.shape[1]!=2 or len(x)<4096 or not np.isfinite(x).all() or not np.isfinite(t).all() or not 8000<=sr<=192000 or not 0<lo<hi:raise ValueError('invalid paired stage audio')
 n=len(x);m=x.mean(1);y=t.mean(1);den=np.dot(m,m)
 if den<1e-10:raise ValueError('silent source')
 c=sig.correlate(y,m,method='fft')[n-1:]/den;start=max(1,int(sr*lo));end=min(int(sr*hi),n//3)
 if end<=start:raise ValueError('insufficient duration')
 # Strong candidates at a fundamental and its harmonics. Search nearby samples,
 # then fit causal, repeated copies to the earlier region (no replay FIR).
 idx=np.arange(start,end);z=np.abs(c[idx])+.7*np.abs(c[2*idx])+.4*np.abs(c[3*idx]);p=sig.find_peaks(z,distance=max(1,int(.015*sr)))[0];p=sorted(p,key=lambda k:-z[k])[:6]
 cand=sorted(set(int(idx[k])+off for k in p for off in range(-2,3) if start<=int(idx[k])+off<end))
 if not cand:raise ValueError('no repeat candidate')
 # Fit channel-specific repeated tap gains on downsampled rows, not downsampled lags.
 N=min(8,n//start);sel=np.arange(0,n,4);target=t[sel];scale=max(float(np.mean(target*target)),1e-14);best=None
 for d in cand:
  columns=np.column_stack([np.where(sel>=d*j,m[np.maximum(0,sel-d*j)],0.) for j in range(N)])
  G=columns.T@columns;h=np.linalg.solve(G+np.eye(N)*max(1e-9,np.trace(G)/N*1e-5),columns.T@target);err=float(np.sqrt(np.mean((columns@h-target)**2)/scale))
  if best is None or err<best['error']:best=dict(samples=int(d),seconds=float(d/sr),error=err,coefficients=h.tolist())
 return best
