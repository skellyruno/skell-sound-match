"""Offline, deterministic descriptors for reference retrieval, not source identity.

Inspired by cross-modal retrieval research, not a CLVAP model or trained weights.
Keep stage labels and same-take validation separate from acoustic similarity.
"""
from dataclasses import dataclass
import numpy as np
from scipy import signal, fft

BANDS = np.array([50,100,180,320,560,1000,1800,3200,5600,10000,14000])
WEIGHTS = np.array([1., .7, .6, .8])


def _db(p):
    return 10*np.log10(np.maximum(p, 1e-15))


def descriptor(audio, rate):
    """Four fixed groups: spectral shape, dynamics, motion, stereo. No pitch/key.

    Stereo features use channel powers (not just mono) to retain antiphase audio.
    At least 1 s, 32 kHz or more: reject unsupported input instead of silently
    matching missing high bands. Returns tuples of finite float64 arrays.
    """
    x = np.asarray(audio, dtype=np.float64)
    if x.ndim == 1:
        x = x[:,None]
    if x.ndim != 2 or x.shape[1] not in (1,2) or not np.isfinite(x).all():
        raise ValueError('expected finite mono/stereo audio')
    if not np.isfinite(rate) or rate < 32000 or rate > 384000 or int(rate)!=rate or len(x) < rate or len(x)>60*rate:
        raise ValueError('unsupported rate or excerpt outside 1–60 seconds')
    if x.shape[1] == 1:
        x = np.repeat(x,2,axis=1)
    # Consistent 32 kHz analysis, never used to render the original audio.
    from fractions import Fraction
    ratio = Fraction(32000, int(rate))
    if ratio != 1:
        x = signal.resample_poly(x,ratio.numerator,ratio.denominator,axis=0)
    scale = np.max(np.abs(x))
    if scale < 1e-6:
        raise ValueError('silent excerpt')
    x = x / scale
    n=1024; hop=320
    frames = np.lib.stride_tricks.sliding_window_view(x,n,axis=0)[::hop]
    power = np.mean(frames**2,axis=(1,2))
    if power.max() < 1e-12:
        raise ValueError('silent excerpt')
    active = power > max(power.max()*1e-5,1e-12)
    w=np.hanning(n)
    z=fft.rfft(frames*w,axis=-1)
    p=np.mean(np.abs(z)**2,axis=1)
    hz=fft.rfftfreq(n,1/32000)
    band=np.stack([p[:,(hz>=a)&(hz<b)].mean(axis=1) for a,b in zip(BANDS[:-1],BANDS[1:])],axis=1)
    logband=_db(band)
    shape=logband[active]-np.mean(logband[active],axis=1,keepdims=True)
    tone=np.r_[np.median(shape,axis=0),np.percentile(shape,75,axis=0)-np.percentile(shape,25,axis=0)]/10
    env=_db(power); env-=np.percentile(env[active],90)
    dynamics=np.r_[np.percentile(env,[10,25,50,75,95])/10, active.mean(),np.mean(np.abs(np.diff(env)))/10]
    # Fixed time scales, normalized to clip level: fast syllables and slower tails.
    motion=np.array([np.mean(np.abs(env[d:]-env[:-d]))/10 for d in (1,3,10,25,50)])
    l,r=frames[:,0,:],frames[:,1,:]
    mid=(l+r)*.5;side=(l-r)*.5
    mp=np.mean(mid**2,axis=1);sp=np.mean(side**2,axis=1)
    # Bound mono and antiphase extremes and avoid negative infinities.
    sm=np.clip(_db(sp)-_db(mp),-60,60)
    corr=np.sum(l*r,axis=1)/np.maximum(np.sqrt(np.sum(l*l,axis=1)*np.sum(r*r,axis=1)),1e-15)
    stereo=np.r_[np.percentile(sm[active],[25,50,75])/20,np.percentile(corr[active],[25,50,75])]
    return (tone,dynamics,motion,stereo)


def distances(query, bank, weights=WEIGHTS):
    """Mean absolute feature distances per group; weights are explicit.

    A zero weight can reproduce the tone-only baseline. Never use this rank
    as proof of sample alignment, processing order or listening approval.
    """
    w=np.asarray(weights,dtype=float)
    if w.shape!=(4,) or not np.isfinite(w).all() or np.any(w<0) or w.sum()<=0:
        raise ValueError('invalid group weights')
    rows=[]
    for item in bank:
        if len(query)!=4 or len(item)!=4:
            raise ValueError('invalid descriptor')
        d=[]
        for a,b in zip(query,item):
            a,b=np.asarray(a),np.asarray(b)
            if a.shape!=b.shape or a.ndim!=1 or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():
                raise ValueError('invalid descriptor group')
            d.append(np.mean(np.abs(a-b)))
        rows.append(d)
    return np.asarray(rows,dtype=float).reshape(-1,4) @ (w/w.sum())


@dataclass(frozen=True)
class Match:
    key: str
    distance: float


def rank(query, entries, *, allowed_keys=None, weights=WEIGHTS):
    """Optional explicitly verified stage/family allowlist. Empty means no hits."""
    rows=list(entries)
    keys=[k for k,_ in rows]
    if len(set(keys))!=len(keys):
        raise ValueError('duplicate retrieval keys')
    if allowed_keys is not None:
        allowed=set(allowed_keys)
        rows=[(k,v) for k,v in rows if k in allowed]
    scores=distances(query,[v for _,v in rows],weights)
    return sorted((Match(k,float(s)) for (k,_),s in zip(rows,scores)),key=lambda r:(r.distance,r.key))

# Experimental preset selected on historical middle sections, NOT universally
# calibrated or an identity classifier. Keep caller's explicit stage allowlist.
EXPERIMENTAL_WEIGHTS = (1.,0.,0.,.35)


def prototypes(audio, rate):
    """Whole enrollment excerpt plus halves, never reads a query excerpt."""
    x=np.asarray(audio)
    whole=descriptor(x,rate)
    parts=[whole]
    for section in (x[:len(x)//2],x[len(x)//2:]):
        try:
            parts.append(descriptor(section,rate))
        except ValueError:
            pass # silent/short enrollment half; keep valid whole
    return tuple(parts)


def rank_prototypes(query, entries, *, allowed_keys=None, weights=EXPERIMENTAL_WEIGHTS):
    """Rank each reference by nearest enrollment prototype, no vote promotion."""
    rows=list(entries)
    keys=[k for k,_ in rows]
    if len(set(keys))!=len(keys):
        raise ValueError('duplicate retrieval keys')
    allowed=None if allowed_keys is None else set(allowed_keys)
    result=[]
    for k,bank in rows:
        if allowed is not None and k not in allowed:
            continue
        bank=list(bank)
        if not bank:
            raise ValueError('empty prototype bank')
        result.append(Match(k,float(np.min(distances(query,bank,weights)))))
    return sorted(result,key=lambda r:(r.distance,r.key))
