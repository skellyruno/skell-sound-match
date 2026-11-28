"""Separate direct vocal and residual tail diagnostics for paired offline audio.
Does not certify take identity, recover clipped samples or authorize promotion.
Thresholds must be frozen from training. Reference rail exclusions are explicit.
"""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class Thresholds:
    source_power: float
    reference_power: float
    rail: float = .9999


def _audio(x):
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.isfinite(x).all():
        raise ValueError('expected nonempty finite stereo audio')
    return x


def _frames(x,frame):
    if type(frame) is not int or frame<16 or len(x)<frame:raise ValueError('invalid frame length')
    n=len(x)//frame
    return x[:n*frame].reshape(n,frame,2)


def freeze_thresholds(source,reference,frame=2048,source_range_db=24.,reference_range_db=50.,rail=.9999):
    x,y=_audio(source),_audio(reference)
    if x.shape!=y.shape or not all(np.isfinite(z) for z in (source_range_db,reference_range_db,rail)) or not 0<source_range_db<=100 or not 0<reference_range_db<=100 or not 0<rail<=1:raise ValueError('invalid threshold controls')
    xp=np.max(np.mean(_frames(x,frame)**2,axis=(1,2)));yp=np.max(np.mean(_frames(y,frame)**2,axis=(1,2)))
    if xp<1e-12 or yp<1e-12:raise ValueError('silent training')
    return Thresholds(float(max(1e-12,xp*10**(-source_range_db/10))),float(max(1e-12,yp*10**(-reference_range_db/10))),float(rail))


def diagnostics(source,reference,candidate,thresholds,frame=2048):
    x,y,z=map(_audio,(source,reference,candidate))
    if x.shape!=y.shape or x.shape!=z.shape:raise ValueError('unaligned shapes')
    if not isinstance(thresholds,Thresholds) or not all(np.isfinite(a) for a in (thresholds.source_power,thresholds.reference_power,thresholds.rail)) or min(thresholds.source_power,thresholds.reference_power)<=0 or not 0<thresholds.rail<=1:raise ValueError('invalid thresholds')
    a,b,c=(_frames(v,frame) for v in (x,y,z));xp=np.mean(a*a,axis=(1,2));yp=np.mean(b*b,axis=(1,2))
    active=(xp>=thresholds.source_power)&(yp>=thresholds.reference_power);tail=(xp<thresholds.source_power)&(yp>=thresholds.reference_power)
    # Never infer missing waveform beyond the reference rail. Report sample coverage.
    rails=(np.abs(b)>=thresholds.rail).any(axis=2)|(np.abs(a)>=thresholds.rail).any(axis=2)
    valid=active[:,None]&~rails
    q=b[valid];r=c[valid];target_energy=float(np.sum(q*q));render_energy=float(np.sum(r*r));cross=float(np.sum(q*r))
    wave=float(np.sqrt(np.sum((q-r)**2)/target_energy)) if target_energy>1e-12 else None
    corr=float(np.clip(cross/np.sqrt(target_energy*render_energy),-1,1)) if target_energy>1e-12 and render_energy>1e-12 else None
    def level(v):return 10*np.log10(np.maximum(v,1e-12))
    def tail_metrics(mask):
        if not mask.any():return None
        u,v=b[mask],c[mask];er=np.mean(abs(level(np.mean(u*u,axis=(1,2)))-level(np.mean(v*v,axis=(1,2)))))
        def side_mid(w):
            m=w.mean(2);s=(w[:,:,0]-w[:,:,1])*.5
            return level(np.mean(s*s,axis=1))-level(np.mean(m*m,axis=1))
        width=np.mean(abs(side_mid(u)-side_mid(v)))
        return {'envelope_db':float(er),'side_mid_db':float(width)}
    return {'frame_count':len(a),'discarded_end_samples':len(x)%frame,'vocal_frames':int(active.sum()),'tail_frames':int(tail.sum()),'rail_frames':int(rails.any(1).sum()),'rail_samples_in_frames':int(rails.sum()),'vocal_valid_samples':int(valid.sum()),'vocal_total_samples':int(active.sum()*frame),'vocal_waveform_nrmse':wave,'vocal_correlation':corr,'vocal_profile':tail_metrics(active),'tail_profile':tail_metrics(tail)}
