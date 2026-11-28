"""Offline source-only wet paths, with independent delay and reverb controls."""
import numpy as np
from scipy import signal


def _input(audio, sr, lowpass):
    x = np.asarray(audio, dtype=float)
    if (x.ndim != 2 or x.shape[1] != 2 or not len(x) or
            not np.isfinite(x).all() or not 8000 <= sr <= 192000 or
            not 200 < lowpass < sr / 2):
        raise ValueError('Invalid stereo wet input or cutoff')
    return x


def filtered_echo(audio, sr, delay_ms, feedback, cross, lowpass, right_offset_ms=0):
    """Finite causal echo branch; no direct signal or reference samples."""
    x = _input(audio, sr, lowpass)
    if not 10 <= delay_ms <= 2000 or not 0 <= feedback <= .9 or not 0 <= right_offset_ms <= 100:
        raise ValueError('Invalid echo parameters')
    wet = signal.sosfilt(signal.butter(2, lowpass, fs=sr, btype='lowpass', output='sos'), x, axis=0)
    wet = signal.sosfilt(signal.butter(2, 200, fs=sr, btype='highpass', output='sos'), wet, axis=0)
    out = np.zeros_like(x)
    offset = round(right_offset_ms * sr / 1000)
    for j in range(1, 6):
        d = round(sr * delay_ms * j / 1000)
        if d >= len(x):
            break
        tap = wet[:, ::-1] if cross and j % 2 else wet
        out[d:, 0] += tap[:len(x)-d, 0] * feedback**(j-1)
        if d + offset < len(x):
            out[d+offset:, 1] += tap[:len(x)-d-offset, 1] * feedback**(j-1)
    return out


def diffuse_reverb(audio, sr, rt60, predelay, lowpass, seed=18):
    """Deterministic causal diffuse tail from input, not a proprietary IR model."""
    x = _input(audio, sr, lowpass)
    if not .1 <= rt60 <= 4 or not 0 <= predelay < min(.2, rt60):
        raise ValueError('Invalid reverb parameters')
    rng = np.random.default_rng(seed)
    t = np.arange(round(sr * min(3, rt60 * 1.5))) / sr
    h = rng.normal(size=len(t)) * np.exp(-6.9078 * t / rt60)
    h[:round(predelay * sr)] = 0
    h = signal.sosfilt(signal.butter(2, [180, lowpass], fs=sr, btype='bandpass', output='sos'), h)
    h /= max(np.linalg.norm(h), 1e-12)
    return np.column_stack([signal.fftconvolve(x[:, i], h)[:len(x)] for i in range(2)])
