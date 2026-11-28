"""Guarded audio-only transfer refinement. Offline, no FST or vendor engine.
Temporal statistics are proxies for articulation and silence, not delay-time estimators.
"""
from dataclasses import replace
from math import gcd
import numpy as np
from scipy import signal
from .reference_transfer import _audio, profile, distance, Prepared, Recipe


def temporal_profile(x, rate):
    x = _audio(x, rate)
    if rate != 44100:
        g = gcd(int(rate), 44100)
        x = signal.resample_poly(x, 44100//g, int(rate)//g, axis=0)
    p = profile(x, 44100)
    hop = 441  # 10 ms, non-overlapping, standardized timebase
    f = x[:len(x)//hop*hop].reshape(-1, hop, 2)
    rms = np.sqrt(np.mean(f*f, axis=(1,2), dtype=np.float64))
    db = 20*np.log10(np.maximum(rms, 1e-8))
    active = np.flatnonzero(db > max(float(db.max())-40, -100))
    if len(active) < 20:
        raise ValueError('insufficient temporal coverage')
    # Ignore arbitrary leading/trailing file padding; retain internal pauses.
    db = db[active[0]:active[-1]+1]
    med = float(np.median(db[db > max(float(db.max())-40, -100)]))
    rel = np.clip(db-med, -60, 30)
    q = np.percentile(rel, [5,10,20,35])
    quiet = np.array([(rel < t).mean() for t in (-15,-25,-35)])
    # Gate/pause and articulation proxies. Condition changes on an active endpoint.
    slopes = []
    for lag in (1, 5):
        a,b=rel[:-lag],rel[lag:]
        delta=(b-a)[np.maximum(a,b)>-25]
        if len(delta)<10: raise ValueError('insufficient articulation coverage')
        slopes.extend(np.percentile(delta,[10,25,75,90]))
    return dict(p, quiet_db=q, quiet_fraction=quiet, articulation=np.array(slopes))


def compare(a,b):
    d=distance(a,b)
    d['quiet_db']=float(np.mean(abs(a['quiet_db']-b['quiet_db'])))
    d['quiet_fraction']=float(np.mean(abs(a['quiet_fraction']-b['quiet_fraction'])))
    d['articulation_db']=float(np.mean(abs(a['articulation']-b['articulation'])))
    d['guarded_score']=d['score']+.20*d['quiet_db']+4*d['quiet_fraction']+.35*d['articulation_db']
    return d


def refine(sources, reference, ref_rate, initial):
    """Training-only coordinate search from frozen recipe, with per-source guards.

    No new echo time inference from unpaired audio: can reduce existing echo/room,
    but cannot increase them. No reference waveform enters rendering. A rejection
    returns the exact initial recipe. Level fit uses training input only.
    """
    initial.checked()
    bases=[Prepared(x,sr) for x,sr in sources]
    if len(bases)<2: raise ValueError('need at least two training performances')
    target=temporal_profile(reference,ref_rate)
    def rows(q):
        return [compare(temporal_profile(b.render(q),b.rate),target) for b in bases]
    baseline=rows(initial)
    def objective(rr):
        v=[r['guarded_score'] for r in rr]
        return .75*np.mean(v)+.25*max(v)
    limits={'tone_db':.25,'dynamics_db':.25,'width_db':1.,'quiet_db':1.,'quiet_fraction':.025,'articulation_db':.4}
    count=1
    def assess(q):
        nonlocal count
        count+=1
        try: rr=rows(q)
        except ValueError: return float('inf'),None
        if any(r[k]>b[k]+tol for r,b in zip(rr,baseline) for k,tol in limits.items()): return float('inf'),rr
        return objective(rr),rr
    best=objective(baseline); r=initial; selected=baseline
    grids={'low':[-3,0,3],'body':[-3,0,3],'presence':[-3,0,3],'air':[-3,0,3],
           'compression':[-.15,0,.15],'gate':[-.25,0,.25],'stereo':[-.15,0,.15]}
    for _ in range(2):
        for key,offsets in grids.items():
            lo,hi={'compression':(0,.75),'gate':(0,1),'stereo':(0,.7)}.get(key,(-12,12))
            anchor=getattr(r,key)
            for val in sorted(set(float(np.clip(anchor+o,lo,hi)) for o in offsets)):
                q=replace(r,**{key:val});s,rr=assess(q)
                if s<best-1e-7:r,best,selected=q,s,rr
        for key in ('echo','room'):
            for val in (0.,.5*getattr(r,key)):
                q=replace(r,**{key:val});s,rr=assess(q)
                if s<best-1e-7:r,best,selected=q,s,rr
    if best>objective(baseline)*.98:
        return initial,{'evaluations':count,'selected':False,'before':baseline,'after':baseline}
    # Match median target active level across training sources only.
    lev=np.median([temporal_profile(b.render(r),b.rate)['level'] for b in bases])
    r=replace(r,gain_db=float(np.clip(r.gain_db+target['level']-lev,-36,36)))
    score,final=assess(r)
    if not np.isfinite(score) or score>objective(baseline)*.98:
        return initial,{'evaluations':count,'selected':False,'before':baseline,'after':baseline}
    return r,{'evaluations':count,'selected':True,'before':baseline,'after':final}
