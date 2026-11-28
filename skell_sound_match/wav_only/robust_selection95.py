"""Balanced multi-phrase regret for pre-audit selection, with fail-closed boundaries."""
import numpy as np

def validate_windows(windows,fit_stop,audit_start,guard=0):
    if not 0<=fit_stop<audit_start or guard<0 or not windows:raise ValueError('invalid limits')
    last=fit_stop
    for w in windows:
        if not isinstance(w,slice) or w.step not in (None,1) or w.start is None or w.stop is None or not last+guard<=w.start<w.stop<=audit_start-guard:
            raise ValueError('overlapping or out-of-range selection window')
        last=w.stop
    return tuple(windows)

def regret(scores,anchor_scores,local_weight=.5):
    a=np.asarray(scores,dtype=float);b=np.asarray(anchor_scores,dtype=float)
    if a.ndim!=1 or a.shape!=b.shape or len(a)<2 or not np.isfinite(a).all() or not np.isfinite(b).all() or (a<0).any() or (b<0).any() or not 0<=local_weight<=1:raise ValueError('invalid scores')
    ratio=(a+1e-8)/(b+1e-8)
    return float((1-local_weight)*ratio[:-1].mean()+local_weight*ratio[-1])
