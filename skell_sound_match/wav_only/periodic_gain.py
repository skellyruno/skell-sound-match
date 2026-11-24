"""Offline rhythmic gain identification from a fixed training prefix.

Fits periodic basis coefficients, never records or replays the reference envelope.
Absolute time is relative to the paired recording; phase transfer is unverified.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class PeriodicGain:
    rate_hz: float
    coefficients: np.ndarray
    validation_mae_db: float


def _basis(t, frequency):
    return np.column_stack([np.ones(len(t))]+[v for j in range(1,5) for v in
                          (np.sin(2*np.pi*frequency*j*t), np.cos(2*np.pi*frequency*j*t))])


def fit_periodic_candidates(time_s, residual_db, active, split_s, *, rates=None, limit=5):
    """Validate rates on a later part of the supplied training prefix; refit winners."""
    t=np.asarray(time_s,float); y=np.asarray(residual_db,float); active=np.asarray(active,bool)
    if t.ndim!=1 or t.shape!=y.shape or t.shape!=active.shape or not np.isfinite(t).all() or not np.isfinite(y).all() or np.any(np.diff(t)<=0) or not 1<=limit<=20:
        raise ValueError('Invalid periodic training data')
    tr=active&(t<split_s); va=active&~tr
    if tr.sum()<20 or va.sum()<10:
        raise ValueError('Insufficient active train and validation frames')
    rates=np.arange(.35,12.01,.025) if rates is None else np.asarray(rates,float)
    if rates.ndim!=1 or not len(rates) or not np.isfinite(rates).all() or np.any((rates<=0)|(rates>20)):
        raise ValueError('Invalid search rates')
    y=np.clip(y,-28,18); penalty=np.diag([.001,2,2,4,4,8,8,16,16]); ranked=[]
    for f in rates:
        B=_basis(t,f); A=B[tr]; c=np.linalg.solve(A.T@A+penalty,A.T@y[tr]); err=float(np.mean(abs(y[va]-B[va]@c)))
        ranked.append((err,float(f)))
    out=[]
    for err,f in sorted(ranked):
        if any(abs(f-m.rate_hz)<.2 for m in out):continue
        A=_basis(t,f)[active]; c=np.linalg.solve(A.T@A+penalty,A.T@y[active]);c.setflags(write=False)
        out.append(PeriodicGain(f,c,err))
        if len(out)>=limit:break
    return out


def render_gain(time_s, model, strength=1.):
    """Deterministic bounded gain for replay, no target required."""
    t=np.asarray(time_s,float)
    if t.ndim!=1 or not np.isfinite(t).all() or not 0<=strength<=1.5:
        raise ValueError('Invalid time or strength')
    return 10**(np.clip(_basis(t,model.rate_hz)@model.coefficients,-28,12)*strength/20)
