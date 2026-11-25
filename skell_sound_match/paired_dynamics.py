"""Independent causal linked dynamics model learned from aligned audio pairs.
Offline research, not an implementation of a particular vendor compressor/gate.
"""
from dataclasses import dataclass
import numpy as np
from scipy import signal, optimize
from .reference_transfer import _audio


@dataclass(frozen=True)
class Dynamics:
    attack_ms: float=2.
    release_ms: float=60.
    threshold_db: float=-45.
    expansion: float=0.
    compressor_db: float=-18.
    compression: float=0.
    gain: float=1.

    def checked(self):
        for v,lo,hi in ((self.attack_ms,.1,30),(self.release_ms,5,350),
                        (self.threshold_db,-85,-15),(self.expansion,0,12),
                        (self.compressor_db,-45,0),(self.compression,0,.9),(self.gain,.05,8)):
            if not np.isfinite(v) or not lo<=v<=hi: raise ValueError('invalid dynamics recipe')
        if self.attack_ms>self.release_ms: raise ValueError('attack exceeds release')
        return self


def _gain(x,rate,r):
    p=np.max(np.abs(x),axis=1).astype('float64')**2
    def detector(ms):
        a=-np.expm1(-1000/(ms*rate))
        return signal.lfilter([a],[1,a-1],p)
    env=10*np.log10(np.maximum(np.maximum(detector(r.attack_ms),detector(r.release_ms)),1e-16))
    db=-r.expansion*np.maximum(r.threshold_db-env,0)-r.compression*np.maximum(env-r.compressor_db,0)
    return 10**(np.maximum(db,-90)/20)


def render(source,rate,recipe):
    x=_audio(source,rate);recipe.checked()
    return (x*(_gain(x,rate,recipe)*recipe.gain)[:,None]).astype('float32')


def masks(source,rate,scale):
    level=np.max(abs(source),axis=1)
    a=-np.expm1(-1/(.02*rate));env=np.sqrt(signal.lfilter([a],[1,a-1],level.astype('float64')**2))
    active=level>scale*.06;quiet=level<scale*.012;onset=active&(env<scale*.025)
    return active,quiet,onset


def errors(out,target,regions):
    return [float(np.sum((out[m].astype('float64')-target[m])**2)/max(1e-15,np.sum(target[m].astype('float64')**2))) if m.any() else None for m in regions]


def fit_gate(source,target,rate,seed=24):
    """Fit gain and expansion only on first 2/3 of supplied training pair.

    The last third selects candidates; external holdout remains caller-owned.
    A gain-only baseline competes with a bounded dual-detector expansion model.
    """
    x,y=_audio(source,rate),_audio(target,rate)
    if x.shape!=y.shape: raise ValueError('paired geometry differs')
    cut=2*len(x)//3;scale=float(np.max(abs(x[:cut])))
    ms=masks(x,rate,scale);a=tuple(m[:cut] for m in ms);b=tuple(m[cut:] for m in ms)
    if any(m.sum()<limit for m,limit in zip(a+b,(100,100,40,100,100,40))): raise ValueError('insufficient region coverage')
    def candidate(p,full=False):
        r=Dynamics(*map(float,p));r.checked();v=x if full else x[:cut]
        g=_gain(v,rate,r);o=v*g[:,None];z=o[:cut][a[0]];t=y[:cut][a[0]]
        gain=float(np.clip(np.sum(z*t)/max(1e-15,np.sum(z*z)),.05,8));r=Dynamics(*map(float,p),gain=gain)
        return r,o*gain
    base,bo=candidate((2,60,-45,0,-18,0),True);bt=errors(bo[:cut],y[:cut],a);bv=errors(bo[cut:],y[cut:],b)
    def objective(e,baseline):
        return sum(v/max(z,1e-9) for v,z in zip(e,baseline))/3
    count=0
    def loss(p):
        nonlocal count
        count+=1
        if p[0]>p[1]: return 1e6
        _,o=candidate((*p,-18,0));e=errors(o,y[:cut],a)
        return objective(e,bt)+10*sum(max(0,v/max(z,1e-9)-1.05)**2 for v,z in zip(e,bt))
    opt=optimize.differential_evolution(loss,[(.1,15),(15,250),(-75,-25),(0,12)],seed=seed,maxiter=10,popsize=5,polish=False)
    # Evaluate the final population on the internal validation set only.
    best=base;bestval=1.;bestt,bestv=bt,bv
    for p in opt.population:
        r,o=candidate((*p,-18,0),True);et=errors(o[:cut],y[:cut],a);ev=errors(o[cut:],y[cut:],b)
        score=objective(ev,bv)
        if score<bestval*.999 and all(v<=1.05*max(z,1e-9) for v,z in zip(et,bt)) and all(v<=1.05*max(z,1e-9) for v,z in zip(ev,bv)):
            best,bestval,bestt,bestv=r,score,et,ev
    return best,base,{'evaluations':count,'validation_candidates':len(opt.population),'train_before':bt,'train_after':bestt,'validation_before':bv,'validation_after':bestv,'scale':scale}
