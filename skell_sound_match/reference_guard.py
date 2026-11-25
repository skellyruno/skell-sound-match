"""Offline split eligibility and conservative linked headroom diagnostics."""
import numpy as np
from scipy import signal


def _check(x, rate):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] not in (1, 2) or not len(x) or not np.isfinite(x).all() or not np.isfinite(rate) or int(rate) != rate or not 32000 <= rate <= 192000:
        raise ValueError('expected finite mono/stereo audio at 32–192 kHz')
    return x


def split_activity(x, rate, split, min_frames=8, relative_db=-40., absolute_db=-80.):
    """Anchor both partitions to the training level; no quiet-holdout renormalization."""
    x = _check(x, rate)
    if not isinstance(split, (int, np.integer)) or not 0 < split < len(x) or not isinstance(min_frames, int) or min_frames < 1 or not np.isfinite(relative_db) or relative_db > 0 or not np.isfinite(absolute_db) or absolute_db > 0:
        raise ValueError('invalid split or activity limits')
    n = int(round(rate*.04))
    def levels(y):
        return 10*np.log10(np.maximum(np.mean(y[:len(y)//n*n].reshape(-1,n,x.shape[1])**2,axis=(1,2)),1e-30))
    a,b=levels(x[:split]),levels(x[split:])
    if not len(a) or not len(b): raise ValueError('partition too short')
    threshold=max(float(np.max(a))+relative_db,absolute_db)
    ta,tb=a>threshold,b>threshold
    return dict(eligible=bool(ta.sum()>=min_frames and tb.sum()>=min_frames),threshold_db=threshold,train_active=int(ta.sum()),later_active=int(tb.sum()),train_frames=len(a),later_frames=len(b),train_peak_db=float(max(a)),later_peak_db=float(max(b)))


def peak_db(x,rate):
    x=_check(x,rate)
    return float(20*np.log10(max(1e-15,np.max(abs(signal.resample_poly(x,4,1,axis=0))))))


def training_trim(peaks, ceiling_db=-1.5, margin_db=1.):
    """Training-only attenuation; does not guarantee unseen peak safety."""
    p=np.asarray(peaks,dtype=float)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or not np.isfinite(ceiling_db) or ceiling_db>0 or not np.isfinite(margin_db) or margin_db<0:
        raise ValueError('invalid training peak calibration')
    return min(0.,float(ceiling_db-margin_db-p.max()))


def linked_guard(x,rate,ceiling_db=-2.5,release_db_per_second=120.):
    """Causal sample-peak guard; immediate reduction, linear-dB release.

    No lookahead, no amplification. Not a true-peak limiter; separately measure
    oversampled output before acceptance.
    """
    x=_check(x,rate)
    if not np.isfinite(ceiling_db) or ceiling_db>0 or ceiling_db< -60 or not np.isfinite(release_db_per_second) or not 0<release_db_per_second<=1000:
        raise ValueError('invalid peak guard parameters')
    peak=20*np.log10(np.maximum(np.max(abs(x),axis=1),1e-30))
    need=np.maximum(peak-ceiling_db,0.)
    t=np.arange(len(x),dtype=float)*(release_db_per_second/rate)
    reduction=np.maximum(np.maximum.accumulate(need+t)-t,0.)
    return x*10**(-reduction[:,None]/20), reduction
