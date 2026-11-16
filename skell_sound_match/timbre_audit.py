"""Level-aware, pitch-independent timbre diagnostics for same-take recordings.

Separates harmonic-like and noise-like frames by the candidate's spectral
flatness, to avoid using target audio to control a candidate processor.
Flatness is only a *proxy* for vocal excitation, not a voiced/unvoiced oracle.
"""
from __future__ import annotations
import numpy as np
from scipy import signal
from .core import Audio

DEFAULT_BANDS = [(80,250),(250,500),(500,1100),(1100,2600),(2600,5500),(5500,9000),(9000,14000)]


def analyze_timbre(reference: Audio, candidate: Audio, *, bands=DEFAULT_BANDS,
                   flatness_split=0.28, active_floor_db=-40.0, fft_size=2048, hop=441):
    if reference.rate != candidate.rate or reference.samples.shape != candidate.samples.shape:
        raise ValueError('Same-length, same-channel, same-rate recordings are required')
    if not (reference.rate >= 16000 and 0 < flatness_split < 1.0 and -120 < active_floor_db < 0):
        raise ValueError('Invalid sample rate or mask configuration')
    if not (128 <= fft_size <= 8192 and 0 < hop <= fft_size):
        raise ValueError('Invalid STFT parameters')
    if not (np.isfinite(reference.samples).all() and np.isfinite(candidate.samples).all()):
        raise ValueError('Non-finite audio is not supported')
    # Honest, explicitly mono-only proxy: stereo separation must be audited separately.
    if reference.samples.shape[1] not in (1,2):
        raise ValueError('Unsupported channel count')
    x=reference.samples.mean(axis=1);y=candidate.samples.mean(axis=1)
    f,tm,X=signal.stft(x,fs=reference.rate,nperseg=fft_size,noverlap=fft_size-hop,
                       boundary=None,padded=False)
    _,_,Y=signal.stft(y,fs=reference.rate,nperseg=fft_size,noverlap=fft_size-hop,
                      boundary=None,padded=False)
    a=np.abs(X);b=np.abs(Y)
    energy=np.sqrt(np.mean(b*b,axis=0)+1e-20)
    peak=float(np.max(energy))
    if peak < 1e-9:raise ValueError('Candidate has no analyzable audio')
    active=energy>peak*(10.0**(active_floor_db/20.0))
    floor=1e-10
    flat=np.exp(np.mean(np.log(b+floor),axis=0))/np.mean(b+floor,axis=0)
    harmonic=active&(flat<flatness_split)
    noise=active&~harmonic
    out={'sample_rate':reference.rate,'samples':len(x),'channels':reference.samples.shape[1],
         'fft_size':fft_size,'hop':hop,'classification':'candidate spectral-flatness proxy, not actual vowel recognition',
         'active_frames':int(active.sum()),'harmonic_like_frames':int(harmonic.sum()),
         'noise_like_frames':int(noise.sum()),'bands':[]}
    for lo,hi in bands:
        if not (0 <= lo < hi <= reference.rate/2):continue
        sel=(f>=lo)&(f<hi)
        if not np.any(sel):continue
        ra=np.sqrt(np.mean(a[sel]**2,axis=0)+1e-18)
        ca=np.sqrt(np.mean(b[sel]**2,axis=0)+1e-18)
        signed=20*np.log10((ca+floor)/(ra+floor))
        record={'frequency_low_hz':lo,'frequency_high_hz':hi}
        for name,mask in [('all',active),('harmonic_like',harmonic),('noise_like',noise)]:
            record[name+'_frames']=int(mask.sum())
            record[name+'_median_signed_db']=float(np.median(signed[mask])) if np.any(mask) else None
            record[name+'_mean_abs_error_db']=float(np.mean(np.abs(signed[mask]))) if np.any(mask) else None
        out['bands'].append(record)
    return out
