"""Reusable offline spectral/stereo trial DSP and held-out diagnostics.

No recording-derived presets or private trial coefficients are defined here.
This is not real-time-safe native JUCE processing and is not a VST3 release.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy import signal

DEFAULT_BANDS = ((80, 160), (160, 350), (350, 700), (700, 1600),
                 (1600, 4000), (4000, 8000), (8000, 14000))


def _stereo(audio: np.ndarray) -> np.ndarray:
    x = np.asarray(audio, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 2 or not np.all(np.isfinite(x)):
        raise ValueError("Expected finite, two-channel [frames, 2] audio")
    return x


def _rate(sample_rate: int) -> None:
    if not 32000 <= sample_rate <= 192000:
        raise ValueError("Sample rate outside 32–192 kHz")


def peaking_sos(sample_rate: int, hz: float, db: float, q: float = 0.8) -> np.ndarray:
    """RBJ-style peaking biquad, independently normalized, offline analysis."""
    _rate(sample_rate)
    if not (40 <= hz < sample_rate / 2 and 0.1 <= q <= 12 and -24 <= db <= 24):
        raise ValueError("Invalid peaking EQ settings")
    a = 10 ** (db / 40)
    w = 2 * math.pi * hz / sample_rate
    cos = math.cos(w)
    alpha = math.sin(w) / (2 * q)
    norm = 1 + alpha / a
    return np.array([(1 + alpha * a) / norm, -2 * cos / norm,
                     (1 - alpha * a) / norm, 1.0, -2 * cos / norm,
                     (1 - alpha / a) / norm])


def high_shelf_sos(sample_rate: int, hz: float, db: float, slope: float = 0.8) -> np.ndarray:
    """RBJ high-shelf biquad, normalized to a0=1."""
    _rate(sample_rate)
    if not (40 <= hz < sample_rate / 2 and 0.1 <= slope <= 1 and -24 <= db <= 24):
        raise ValueError("Invalid high-shelf EQ settings")
    a = 10 ** (db / 40)
    w = 2 * math.pi * hz / sample_rate
    cos = math.cos(w)
    alpha = math.sin(w) / 2 * math.sqrt((a + 1 / a) * (1 / slope - 1) + 2)
    v = 2 * math.sqrt(a) * alpha
    b0 = a * ((a + 1) + (a - 1) * cos + v)
    b1 = -2 * a * ((a - 1) + (a + 1) * cos)
    b2 = a * ((a + 1) + (a - 1) * cos - v)
    a0 = (a + 1) - (a - 1) * cos + v
    a1 = 2 * ((a - 1) - (a + 1) * cos)
    a2 = (a + 1) - (a - 1) * cos - v
    return np.array([b0 / a0, b1 / a0, b2 / a0, 1., a1 / a0, a2 / a0])


def finish_stereo(audio: np.ndarray, sample_rate: int,
                  *, presence_db: float = 0., presence_hz: float = 1250.,
                  upper_presence_db: float = 0., upper_presence_hz: float = 3800.,
                  air_db: float = 0., air_hz: float = 7500.,
                  gain_db: float = 0., side_gain: float = 1.) -> np.ndarray:
    """Apply EQ to a pre-rendered source-only chain and adjust existing side audio.

    Crucially, this does not synthesize missing stereo material. Passing zero-side
    mono input with side_gain>1 remains mono; do not describe it as an FX match.
    """
    x = _stereo(audio)
    _rate(sample_rate)
    if not (0 <= side_gain <= 4 and -24 <= gain_db <= 12):
        raise ValueError("Invalid gain/side adjustment")
    sos = np.stack((peaking_sos(sample_rate, presence_hz, presence_db),
                    peaking_sos(sample_rate, upper_presence_hz, upper_presence_db),
                    high_shelf_sos(sample_rate, air_hz, air_db)))
    filtered = signal.sosfilt(sos, x, axis=0) * 10 ** (gain_db / 20)
    mid = (filtered[:, 0] + filtered[:, 1]) * 0.5
    side = (filtered[:, 0] - filtered[:, 1]) * 0.5 * side_gain
    return np.column_stack((mid + side, mid - side))


def estimate_true_peak_db(audio: np.ndarray, oversample: int = 4) -> float:
    """Conservative 4x oversampled peak estimate, not a certified BS.1770 meter."""
    x = _stereo(audio)
    if oversample not in (2, 4, 8):
        raise ValueError("Oversampling factor must be 2, 4, or 8")
    a = signal.resample_poly(x, oversample, 1, axis=0)
    return 20 * math.log10(max(float(np.max(np.abs(a))), 1e-12))


def trim_true_peak(audio: np.ndarray, ceiling_db: float = -1.5) -> tuple[np.ndarray, float]:
    x = _stereo(audio)
    if not -12 <= ceiling_db <= -0.1:
        raise ValueError("Invalid peak ceiling")
    db = min(0., ceiling_db - estimate_true_peak_db(x))
    return x * (10 ** (db / 20)), db


def heldout_band_mae(reference: np.ndarray, candidate: np.ndarray, sample_rate: int,
                     start_s: float, end_s: float,
                     bands: Sequence[tuple[float, float]] = DEFAULT_BANDS) -> dict:
    """RMS loudness-matched band error on a caller-selected unseen time segment.

    Does NOT prove independent-performance transfer or automatic audio alignment.
    Caller must provide a same-take, sample-aligned pair and freeze the recipe.
    """
    _rate(sample_rate)
    ref = _stereo(reference)
    cand = _stereo(candidate)
    if ref.shape != cand.shape or not (0 <= start_s < end_s <= len(ref) / sample_rate):
        raise ValueError("Unaligned lengths or invalid evaluation interval")
    left, right = round(start_s * sample_rate), round(end_s * sample_rate)
    x = cand[left:right]
    y = ref[left:right]
    if len(x) < sample_rate // 4:
        raise ValueError("Evaluation window under 250 ms")
    gain = math.sqrt((np.mean(y * y) + 1e-18) / (np.mean(x * x) + 1e-18))
    errors = []
    for lo, hi in bands:
        if not 20 < lo < hi < sample_rate / 2:
            raise ValueError("Invalid band")
        sos = signal.butter(3, [lo, hi], btype="bandpass", fs=sample_rate, output="sos")
        a = signal.sosfilt(sos, x, axis=0)
        b = signal.sosfilt(sos, y, axis=0)
        errors.append(20 * math.log10(max(math.sqrt(np.mean(a * a)) * gain, 1e-10) /
                                    max(math.sqrt(np.mean(b * b)), 1e-10)))
    return {"band_errors_db": errors, "mae_db": float(np.mean(np.abs(errors))),
            "matching_gain_db": 20 * math.log10(gain)}


def side_mid_db(audio: np.ndarray) -> float:
    x = _stereo(audio)
    mid = (x[:, 0] + x[:, 1]) * 0.5
    side = (x[:, 0] - x[:, 1]) * 0.5
    return 20 * math.log10(max(math.sqrt(float(np.mean(side * side))), 1e-10) /
                         max(math.sqrt(float(np.mean(mid * mid))), 1e-10))
