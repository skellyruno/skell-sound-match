"""Independent offline linked compressor identification from aligned audio.

A dual-power detector with soft knee, parallel mix and optional peak/RMS blend.
No source plugin code. The detector is a model, not a vendor attack/release law.
"""
from dataclasses import dataclass, replace
import numpy as np
from scipy import signal, optimize
from .reference_transfer import _audio

@dataclass(frozen=True)
class Compressor:
    fast_ms: float = 2.
    slow_ms: float = 80.
    threshold: float = -18.
    slope: float = 0.
    knee: float = 6.
    peak_mix: float = 0.
    wet: float = 1.
    makeup: float = 1.

    def checked(self):
        bounds=((.1,40),(10,400),(-60,0),(0,.98),(0,24),(0,1),(0,1),(.05,8))
        for v,(lo,hi) in zip(vars(self).values(),bounds):
            if not np.isfinite(v) or not lo<=v<=hi: raise ValueError('invalid compressor recipe')
        if self.fast_ms>self.slow_ms: raise ValueError('fast exceeds slow')
        return self


def gain_curve(level, threshold, slope, knee):
    d=level-threshold
    if knee == 0: return -slope*np.maximum(d,0)
    return -slope*np.where(d<=-knee/2,0,np.where(d>=knee/2,d,(d+knee/2)**2/(2*knee)))


def _gain(power, peak, rate, r):
    p=power+r.peak_mix*(peak-power)
    def detect(ms):
        a=-np.expm1(-1000/(ms*rate))
        return signal.lfilter([a],[1,a-1],p)
    level=10*np.log10(np.maximum(np.maximum(detect(r.fast_ms),detect(r.slow_ms)),1e-15))
    g=10**(gain_curve(level,r.threshold,r.slope,r.knee)/20)
    return (1-r.wet)+r.wet*g


def render(x, rate, recipe):
    x=_audio(x,rate);r=recipe.checked()
    p=x.astype(np.float64)**2
    return (x*(_gain(p.mean(1),p.max(1),rate,r)*r.makeup)[:,None]).astype(np.float32)


def metrics(x,y,rate):
    """Paired, aligned signals only; no independent performance comparisons."""
    x,y=_audio(x,rate),_audio(y,rate)
    if x.shape!=y.shape: raise ValueError('paired geometry differs')
    out={'relative_rms':float(np.linalg.norm((x-y).astype(np.float64))/max(1e-12,np.linalg.norm(y.astype(np.float64))))}
    for ms in (10,50,200):
        n=int(rate*ms/1000);k=len(y)//n
        if k<3: raise ValueError('insufficient frames')
        a=np.mean(x[:n*k].reshape(k,n,2)**2,axis=(1,2),dtype=np.float64)
        b=np.mean(y[:n*k].reshape(k,n,2)**2,axis=(1,2),dtype=np.float64)
        m=b>max(1e-12,b.max()*1e-4)
        if m.sum()<3: raise ValueError('insufficient active frames')
        out[f'env_{ms}_db']=float(np.mean(abs(10*np.log10(np.maximum(a[m],1e-15)/b[m]))))
    out['crest_gap_db']=float(abs(20*np.log10(max(1e-12,np.max(abs(x)))/max(1e-12,np.sqrt(np.mean(x*x))))-20*np.log10(max(1e-12,np.max(abs(y)))/max(1e-12,np.sqrt(np.mean(y*y))))))
    return out


def fit(source,target,rate,seed=24):
    """Fit on first 40%, choose on next 20%, never optimize on final 40%.

    Fast search uses 1 ms aggregate power and sample-wise projection within each
    frame. Shortlist evaluated with full-rate renderer. Includes gain-only baseline.
    Require strong zero-offset correlation to avoid fitting unrelated or shifted takes.
    """
    x,y=_audio(source,rate),_audio(target,rate)
    if x.shape!=y.shape: raise ValueError('paired geometry differs')
    n=max(1,int(rate/1000));k=len(x)//n;t=int(.4*k);v=int(.6*k)
    if t<500 or v-t<200: raise ValueError('insufficient training duration')
    a=x[:t*n].astype(np.float64);b=y[:t*n].astype(np.float64)
    corr=float(np.sum(a*b)/max(1e-12,np.linalg.norm(a)*np.linalg.norm(b)))
    if corr<.8: raise ValueError('insufficient aligned waveform correlation')
    # Aggregate input detector and projection, no target audio in rendering.
    a=a.reshape(t,n,2);b=b.reshape(t,n,2);p=(a*a).mean((1,2));pk=(a*a).max(2).mean(1)
    dot=(a*b).mean((1,2));q=(b*b).mean((1,2));active=q>max(q.max()*1e-4,1e-12)
    def make(g):return float(np.clip(np.sum(g[active]*dot[active])/max(1e-15,np.sum(g[active]**2*p[active])),.05,8))
    base=Compressor(makeup=make(np.ones(t)));count=0
    def loss(params):
        nonlocal count
        count+=1
        r=Compressor(*map(float,params))
        if r.fast_ms>r.slow_ms:return 1e6
        g=_gain(p,pk,rate/n,r);g*=make(g)
        e=np.maximum(0,g*g*p-2*g*dot+q)
        return float(np.mean(e[active])/max(1e-15,np.mean(q[active]))+.025*np.mean(abs(10*np.log10(np.maximum(g[active]**2*p[active],1e-15)/q[active]))))
    opt=optimize.differential_evolution(loss,[(.1,40),(10,400),(-60,0),(0,.98),(0,24),(0,1),(0,1)],seed=seed,popsize=5,maxiter=18,polish=False)
    # Full-rate calibration only on fit section; rank candidates on validation.
    src=x[:v*n];dst=y[:v*n];ix=t*n
    baseline=metrics(render(src,rate,base)[ix:],dst[ix:],rate)
    def score(m):return m['relative_rms']+.025*m['env_10_db']+.015*m['env_50_db']+.01*m['env_200_db']
    best=base;bm=baseline
    for p in opt.population:
        r=Compressor(*map(float,p))
        if r.fast_ms>r.slow_ms:continue
        z=render(src,rate,r);zz=z[:ix].astype(np.float64);tt=dst[:ix].astype(np.float64)
        r=replace(r,makeup=float(np.clip(np.sum(zz*tt)/max(1e-15,np.sum(zz*zz)),.05,8)))
        m=metrics((z*r.makeup)[ix:],dst[ix:],rate)
        if score(m)<score(bm)*.999 and all(m[k]<=baseline[k]+tol for k,tol in [('relative_rms',.002),('env_10_db',.05),('env_50_db',.05),('env_200_db',.05),('crest_gap_db',.5)]):best,bm=r,m
    return best,base,{'evaluations':count,'validation_candidates':len(opt.population),'correlation':corr,'validation_before':baseline,'validation_after':bm,'split_frame':v*n}
