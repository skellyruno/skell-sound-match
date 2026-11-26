"""Offline pitch-conditioned spectral-envelope diagnostics (not a vocoder).

Inspired by the source/filter decomposition used in STAND/WORLD. This is an
independent cepstral method, not STAR, DIO or PLATINUM. F0 comes from an
explicit caller-supplied track or optional local Praat; never alters tuning.
"""
from dataclasses import dataclass
import numpy as np
from scipy import fft, signal

BANDS = np.array([180.,320.,560.,1000.,1800.,3200.,5600.,8000.])

@dataclass(frozen=True)
class Envelope:
    times: np.ndarray
    f0: np.ndarray
    shape_db: np.ndarray
    harmonic_fraction: np.ndarray
    active: np.ndarray


def analyse(audio, rate, *, f0=None):
    """40 ms frames, 10 ms hop, stereo power not mono cancellation.

    f0, if supplied, must be a (time_seconds, hz) tuple with strictly ascending
    times. Otherwise optional praat-parselmouth must be installed locally.
    No voiced frames are invented for unvoiced or missing F0 measurements.
    """
    x=np.asarray(audio,dtype=np.float64)
    if x.ndim==1: x=x[:,None]
    if (x.ndim!=2 or x.shape[1] not in (1,2) or not np.isfinite(x).all()
        or not np.isfinite(rate) or rate!=int(rate) or not 22050<=rate<=192000
        or not rate<=len(x)<=60*rate):
        raise ValueError('expected finite 1–60 s mono/stereo at 22.05–192 kHz')
    rate=int(rate); n=round(.040*rate); hop=round(.010*rate)
    if np.max(np.abs(x))>16:
        raise ValueError("audio outside supported amplitude range")
    frames=np.lib.stride_tricks.sliding_window_view(x,n,axis=0)[::hop]
    times=(np.arange(len(frames))*hop+(n-1)/2)/rate
    power=np.empty(len(frames))
    for start in range(0,len(frames),128):
        part=frames[start:start+128]
        power[start:start+len(part)]=np.mean(part**2,axis=(1,2))
    active=power>max(power.max()*1e-4,1e-12)
    if f0 is None:
        try: import parselmouth
        except ImportError as exc: raise RuntimeError('install optional praat-parselmouth or supply F0') from exc
        # Avoid stereo cancellation; choose a fixed higher-energy lane, not
        # a per-frame channel switch that could create false pitch transitions.
        lane=x[:,int(np.argmax(np.mean(x*x,axis=0)))]
        p=parselmouth.Sound(lane,sampling_frequency=rate).to_pitch_ac(time_step=.01,pitch_floor=65.,pitch_ceiling=600.)
        pt,ph=p.xs(),p.selected_array['frequency']
    else:
        pt,ph=map(lambda q:np.asarray(q,dtype=float),f0)
    if (pt.ndim!=1 or pt.shape!=ph.shape or len(pt)<2 or not np.isfinite(pt).all()
        or not np.isfinite(ph).all() or np.any(np.diff(pt)<=0) or np.any(ph<0)):
        raise ValueError('invalid F0 track')
    idx=np.searchsorted(pt,times); right=np.clip(idx,0,len(pt)-1); left=np.clip(idx-1,0,len(pt)-1)
    near=np.where(abs(pt[right]-times)<abs(pt[left]-times),right,left)
    hz=ph[near].copy(); hz[(abs(pt[near]-times)>.015)|(hz<65)|(hz>600)|~active]=0
    shape=np.full((len(times),len(BANDS)-1),np.nan); harmonic=np.full(len(times),np.nan)
    ids=np.flatnonzero(hz>0)
    if len(ids):
        size=fft.next_fast_len(n*2); freq=fft.rfftfreq(size,1/rate)
        # Process in bounded batches for long/high-rate audio.
        for start in range(0,len(ids),128):
            j=ids[start:start+128]; pwr=np.mean(abs(fft.rfft(frames[j]*np.hanning(n),n=size,axis=-1))**2,axis=1)
            logp=np.log(np.maximum(pwr,np.max(pwr,axis=1,keepdims=True)*1e-8+1e-30))
            cep=fft.irfft(logp,n=size,axis=-1); q=np.minimum(np.arange(size),size-np.arange(size))/rate
            # Retain slow spectral-envelope variation; suppress periodic harmonic comb.
            lifter=np.exp(-.5*(q[None,:]*hz[j,None]/.48)**4)
            smooth=fft.rfft(cep*lifter,axis=-1).real*(10/np.log(10))
            v=np.stack([smooth[:,(freq>=a)&(freq<b)].mean(axis=1) for a,b in zip(BANDS[:-1],BANDS[1:])],axis=1)
            shape[j]=v-v.mean(axis=1,keepdims=True)
            # Simple energy-around-harmonics proxy, not WORLD aperiodicity.
            hdist=np.abs(freq[None,:]/hz[j,None]-np.rint(freq[None,:]/hz[j,None]))*hz[j,None]
            band=(freq>=180)&(freq<8000); nearh=hdist<=np.minimum(1.4/.04,.25*hz[j,None])
            harmonic[j]=np.sum(pwr[:,band]*nearh[:,band],axis=1)/np.maximum(np.sum(pwr[:,band],axis=1),1e-30)
    return Envelope(times,hz,shape,harmonic,active)


def compare(candidate, reference, *, min_frames=20):
    """Same-time diagnostic only. Reject inadequate voiced overlap.

    Pitch mismatch is reported, not auto-corrected. This does not prove source
    identity or time alignment, and cannot approve an effect chain.
    """
    if not isinstance(min_frames,int) or min_frames<1: raise ValueError("min_frames must be a positive integer")
    if candidate.times.shape!=reference.times.shape or not np.allclose(candidate.times,reference.times,atol=1e-6,rtol=0):
        raise ValueError('different frame geometry')
    cv=candidate.f0>0; rv=reference.f0>0; both=cv&rv
    if both.sum()<min_frames: raise ValueError('insufficient common voiced frames')
    cents=1200*np.log2(candidate.f0[both]/reference.f0[both]); matched=np.abs(cents)<=100
    idx=np.flatnonzero(both)[matched]
    if len(idx)<min_frames: raise ValueError('insufficient pitch-matched voiced frames')
    delta=reference.shape_db[idx]-candidate.shape_db[idx]
    return {'common_voiced_frames':int(both.sum()),'matched_frames':len(idx),
            'voicing_disagreement':float(np.sum(cv!=rv)/max(1,np.sum(cv|rv))),
            'median_abs_pitch_cents':float(np.median(abs(cents))),
            'envelope_mae_db':float(np.mean(abs(delta))),
            'band_delta_db':np.median(delta,axis=0),
            'harmonic_fraction_error':float(np.mean(abs(candidate.harmonic_fraction[idx]-reference.harmonic_fraction[idx])))}
