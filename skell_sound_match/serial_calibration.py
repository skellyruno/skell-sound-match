"""Offline two-stage reference calibration from four *aligned* renders.

Inputs: dry, recording-only, main-only, and full (REC->MAIN) reference.
Fits REC from dry->REC, and a *shared* MAIN model using both dry->MAIN
and REC->full.  Requires the actual sample-aligned take; never infers FL
Studio routing from observed audio. No private audio is embedded in models.

This is an experimental FIR/level-dependent model, NOT a recreation of
proprietary plugins or a zero-latency/real-time-safe processor.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence
import numpy as np
from scipy import signal, ndimage

from .core import Audio, _truepeak_db


@dataclass(frozen=True)
class SerialModel:
    sample_rate: int
    rec: dict
    main: dict
    train_window: tuple[float, float]
    offline_only: bool = True


def _mono(a: Audio) -> np.ndarray:
    if a.samples.ndim != 2 or a.samples.shape[1] not in (1, 2):
        raise ValueError('Only mono or near-dual-mono material is supported')
    if not np.isfinite(a.samples).all():
        raise ValueError('Non-finite audio')
    x = a.samples.mean(axis=1)
    if a.samples.shape[1] == 2:
        s = (a.samples[:, 0] - a.samples[:, 1]) * 0.5
        if np.sqrt(np.mean(s*s)) > .02 * max(np.sqrt(np.mean(x*x)), 1e-10):
            raise ValueError('Meaningful stereo content: use a dedicated stereo model')
    return x


def _validate_four(clips: Sequence[Audio], window: tuple[float, float]):
    if len(clips) != 4:
        raise ValueError('Four renders required')
    sr = clips[0].rate
    if not 16000 <= sr <= 96000:
        raise ValueError('Unsupported sample rate')
    samples = len(clips[0].samples)
    if samples < sr * 4 or not (0 <= window[0] < window[1] <= samples/sr):
        raise ValueError('Invalid duration or training window')
    for c in clips:
        if c.rate != sr or len(c.samples) != samples:
            raise ValueError('Four WAVs must have matching rates and sample counts')
        _mono(c)
    return sr


def _fir_fit(pairs: Sequence[tuple[np.ndarray, np.ndarray]], sr: int,
             window: tuple[float, float], taps: int = 513,
             reg: float = .02) -> np.ndarray:
    if taps < 3 or taps % 2 == 0 or taps > 2049:
        raise ValueError('FIR length must be odd and <= 2049')
    nfft = max(4096, 2**int(math.ceil(math.log2(4*taps))))
    lo, hi = [round(v*sr) for v in window]
    wins = np.hanning(nfft)
    num = np.zeros(nfft//2+1, complex)
    den = np.zeros(nfft//2+1)
    total = 0
    for x, y in pairs:
        for pos in range(lo, hi-nfft+1, nfft//4):
            xx = np.fft.rfft(x[pos:pos+nfft]*wins)
            yy = np.fft.rfft(y[pos:pos+nfft]*wins)
            num += np.conj(xx)*yy
            den += np.abs(xx)**2
            total += 1
    if total < 4 or den.max() <= 1e-12:
        raise ValueError('Training region too short or silent for FIR')
    h = np.fft.irfft(num/(den + reg*np.mean(den)))
    half = taps//2
    h = np.r_[h[-half:], h[:half+1]].real
    if not np.isfinite(h).all() or np.max(np.abs(h)) > 10:
        raise ValueError('Unstable FIR fit')
    return h


def _apply_fir(x: np.ndarray, taps: np.ndarray) -> np.ndarray:
    n = len(taps)//2
    return signal.fftconvolve(x, taps, mode='full')[n:n+len(x)]


def _features(inp: np.ndarray, z: np.ndarray, sr: int):
    width = max(1, round(sr*.005)); k = min(len(inp),len(z))//width
    if k < 20:
        raise ValueError('Insufficient frames')
    def db(q):
        return 20*np.log10(np.maximum(np.sqrt(np.mean(q[:k*width].reshape(k,width)**2,axis=1)),1e-9))
    a,b=db(inp),db(z)
    slow=ndimage.gaussian_filter1d(b, 12)
    diff=b-ndimage.gaussian_filter1d(b, 3)
    grad=np.gradient(ndimage.gaussian_filter1d(a,2))
    # Features remain available at inference with no reference vocal.
    X=np.column_stack([np.ones(k),np.clip((a+25)/20,-3,3),np.clip((b+25)/20,-3,3),
                       np.clip((slow+25)/20,-3,3),np.clip(diff/8,-2,2),np.clip(grad/5,-2,2)])
    return X,b,width,k


def _gain_fit(pairs, h, sr, window):
    features=[];targets=[]
    for inp,target in pairs:
        z=_apply_fir(inp,h)
        F,dbz,w,k=_features(inp,z,sr)
        n=k*w
        dby=20*np.log10(np.maximum(np.sqrt(np.mean(target[:n].reshape(k,w)**2,axis=1)),1e-9))
        t=(np.arange(k)+.5)*w/sr
        good=(t>=window[0])&(t<window[1])&(dbz>-45)&(dby>-45)
        if int(good.sum())<40:
            raise ValueError('Insufficient active frames for gain fit')
        features.append(F[good]);targets.append(np.clip(dby[good]-dbz[good],-7,7))
    X=np.concatenate(features);y=np.concatenate(targets)
    ridge=np.diag([0, 10,10,10,20,20])*len(y)/1000
    coeff=np.linalg.solve(X.T@X+ridge+1e-6*np.eye(X.shape[1]), X.T@y)
    coeff=np.clip(coeff,-20,20)
    return coeff


def fit_stage(pairs: Sequence[tuple[np.ndarray,np.ndarray]], sr: int,
              window: tuple[float,float], taps: int=513) -> dict:
    h=_fir_fit(pairs,sr,window,taps=taps)
    c=_gain_fit(pairs,h,sr,window)
    return {'fir':h.tolist(),'gain_coeff':c.tolist(),'max_gain_change_db':6.0,
            'lookahead_samples':taps//2,'sample_rate':sr}


def apply_stage(inp: np.ndarray, sr: int, model: dict) -> np.ndarray:
    h=np.asarray(model['fir'],dtype=float)
    coeff=np.asarray(model['gain_coeff'],dtype=float)
    cap=float(model['max_gain_change_db'])
    if model['sample_rate']!=sr or h.ndim!=1 or len(h)%2!=1 or len(h)>2049 or len(h)<3 or len(coeff)!=6:
        raise ValueError('Incompatible model')
    if not np.isfinite(h).all() or not np.isfinite(coeff).all() or np.max(abs(h))>10 or not (0 <= cap <= 12):
        raise ValueError('Invalid/unsafe model')
    if not np.isfinite(inp).all():
        raise ValueError('Non-finite input')
    z=_apply_fir(inp,h)
    F,_,width,k=_features(inp,z,sr)
    gain=np.clip(F@coeff,-cap,cap)
    gain=ndimage.gaussian_filter1d(gain,3)
    positions=(np.arange(k)+.5)*width
    interpolated=np.interp(np.arange(len(z)),positions,gain,left=gain[0],right=gain[-1])
    return z*10**(interpolated/20)


def fit_serial(dry:Audio,rec:Audio,main_only:Audio,combined:Audio,
               train_window:tuple[float,float]=(0.94,6.84)) -> SerialModel:
    sr=_validate_four((dry,rec,main_only,combined),train_window)
    d,r,m,f=[_mono(c) for c in (dry,rec,main_only,combined)]
    # Ensure the same performance is present; strong EQ can invert polarity.
    for x,y in ((d,r),(d,m),(r,f)):
        width=round(sr*.01);k=len(x)//width
        xx=np.sqrt(np.mean(x[:k*width].reshape(k,width)**2,axis=1))
        yy=np.sqrt(np.mean(y[:k*width].reshape(k,width)**2,axis=1))
        if np.corrcoef(xx,yy)[0,1]<.35:
            raise ValueError('Different or misaligned takes; refuse to fit')
    recording=fit_stage(((d,r),),sr,train_window)
    main=fit_stage(((d,m),(r,f)),sr,train_window)
    return SerialModel(sr,recording,main,train_window)


def render_serial(dry:Audio, model:SerialModel) -> Audio:
    if dry.rate != model.sample_rate:
        raise ValueError('Different sample rate')
    d=_mono(dry)
    r=apply_stage(d,dry.rate,model.rec)
    f=apply_stage(r,dry.rate,model.main)
    if not np.isfinite(f).all():
        raise ValueError('Non-finite output')
    # No automatic gain or limiting: caller decides how to audition safely.
    return Audio(f[:,None],dry.rate)


def training_gain(a:np.ndarray, target:np.ndarray, sr:int,
                  window:tuple[float,float]) -> float:
    lo,hi=[round(v*sr) for v in window]
    src=a[lo:hi]; ref=target[lo:hi]
    if np.mean(src*src)<1e-14:
        raise ValueError('Silent training input')
    return float(np.sum(src*ref)/np.sum(src*src))


def evaluate_sections(reference:Audio, candidate:Audio,
                      sections:dict[str,tuple[float,float]],
                      train_window:tuple[float,float]) -> dict:
    if candidate.rate!=reference.rate or len(candidate.samples)!=len(reference.samples):
        raise ValueError('Mismatched clips')
    sr=reference.rate
    ref, cand=_mono(reference), _mono(candidate)
    g=training_gain(cand,ref,sr,train_window)
    if not np.isfinite(g) or abs(g)<1e-10:
        raise ValueError('Invalid gain alignment')
    result={'train_gain_db':float(20*np.log10(abs(g))),'sections':{}}
    for key,(lo,hi) in sections.items():
        if not 0<=lo<hi<=len(ref)/sr:
            raise ValueError('Invalid evaluation window')
        a=ref[round(lo*sr):round(hi*sr)]
        b=(cand*g)[round(lo*sr):round(hi*sr)]
        if len(a)<sr//4: raise ValueError('Evaluation section too short')
        corr=float(np.corrcoef(a,b)[0,1])
        w=round(sr*.02);k=len(a)//w
        rms=lambda x:np.sqrt(np.mean(x[:w*k].reshape(k,w)**2,axis=1))+1e-10
        ar,br=rms(a),rms(b)
        mask=ar>max(ar)*10**(-35/20)
        env=float(np.mean(abs(20*np.log10(ar[mask]/br[mask]))))
        result['sections'][key]={'waveform_corr':corr,'envelope20_mae_db':env}
    return result


def safe_for_preview(audio:Audio, ceiling_dbtp=-1.0) -> bool:
    return bool(np.isfinite(audio.samples).all() and _truepeak_db(audio.samples) <= ceiling_dbtp)


def probe_direct_path(dry: Audio, candidate: Audio, reference: Audio,
                      train_window: tuple[float,float],
                      sections: dict[str,tuple[float,float]]) -> dict:
    """Probe an additive dry path; this cannot establish DAW routing topology.

    Coefficients are fitted only within the opening training window. The
    improvement on later passages is reported, never asserted as proof of
    a parallel signal route.
    """
    if dry.rate != candidate.rate or dry.rate != reference.rate or not            (len(dry.samples) == len(candidate.samples) == len(reference.samples)):
        raise ValueError('Mismatched clips')
    d, c, f = (_mono(q) for q in (dry,candidate,reference))
    lo,hi=[round(v*dry.rate) for v in train_window]
    X=np.stack((c[lo:hi],d[lo:hi]),axis=1)
    Y=f[lo:hi]
    normal=X.T@X
    # Penalize the dry path to avoid claiming spurious double-routing.
    ridge=np.diag([.01,.1])*max(float(np.trace(normal)),1e-9)
    coeff=np.linalg.solve(normal+ridge+1e-12*np.eye(2),X.T@Y)
    with_dry=Audio((coeff[0]*c+coeff[1]*d)[:,None],dry.rate)
    before=evaluate_sections(reference,candidate,sections,train_window)
    after=evaluate_sections(reference,with_dry,sections,train_window)
    deltas={k:{'corr_delta':after['sections'][k]['waveform_corr']-before['sections'][k]['waveform_corr'],
               'envelope20_error_delta_db':after['sections'][k]['envelope20_mae_db']-before['sections'][k]['envelope20_mae_db']}
            for k in sections}
    return {'fitted_serial_coeff':float(coeff[0]),'fitted_dry_coeff':float(coeff[1]),
            'sections':deltas,
            'warning':'Non-unique signal-fit diagnostic; cannot prove or disprove DAW parallel routing.'}