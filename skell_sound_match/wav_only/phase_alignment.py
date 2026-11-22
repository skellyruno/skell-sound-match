"""Offline phase-only correction with explicit causal latency and train-only fit.

Recording-derived impulses must remain private. This is not native plugin DSP.
"""
from __future__ import annotations
import numpy as np
from scipy import signal
from .wav_only_effect_match import learn_reverb,check_mono_compatible


def fit(source,target,sr,train_end,fft_size=4096):
    if fft_size<2048 or fft_size>16384 or fft_size%2:raise ValueError('Invalid phase kernel size')
    if source.shape!=target.shape or not np.isfinite(target).all():raise ValueError('Expected aligned finite audio')
    response,meta=learn_reverb(source,target-source,sr,(0,train_end),tail_seconds=.05,ridge_relative=.005)
    response[0]+=1.
    spectrum=np.fft.rfft(response,n=fft_size,axis=0)
    # Unit magnitude preserves the prior trial's tonal balance. A known delay
    # makes the centered kernel causal and is retained in model/render metadata.
    unit=np.exp(1j*np.angle(spectrum));latency=fft_size//2
    kernel=np.roll(np.fft.irfft(unit,n=fft_size,axis=0),latency,axis=0)
    return {'impulse':kernel,'sample_rate':sr,'latency_samples':latency,
            'fit_metadata':meta,'scope':'offline_phase_hypothesis_not_native'}


def render(source,sr,model):
    if sr!=model['sample_rate']:raise ValueError('Sample rate mismatch')
    mono=check_mono_compatible(source);h=np.asarray(model['impulse'])
    if h.ndim!=2 or h.shape[1]!=source.shape[1] or not np.isfinite(h).all():raise ValueError('Invalid phase model')
    latency=model['latency_samples']
    if not isinstance(latency,int) or not 0<=latency<len(h):raise ValueError('Invalid latency')
    return np.column_stack([signal.fftconvolve(mono,h[:,c])[:len(source)+latency] for c in range(source.shape[1])])
