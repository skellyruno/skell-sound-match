"""Deterministic, channel-aware matching diagnostics. Never edits source files."""
from __future__ import annotations

import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
import soundfile as sf
from scipy import signal, optimize

EPS = 1e-10

class Audio(NamedTuple):
    samples: np.ndarray  # always (samples, channels), float64
    rate: int


def load_wav(path: str | Path) -> Audio:
    x, sr = sf.read(str(path), always_2d=True, dtype="float64")
    if sr < 16000 or sr > 192000 or x.shape[0] < int(sr * .15):
        raise ValueError("Unsupported sample rate or audio shorter than 150 ms")
    if x.shape[1] not in (1, 2) or not np.isfinite(x).all():
        raise ValueError("Only finite mono/stereo WAV audio is supported")
    return Audio(x, sr)


def split_audio(audio: Audio, training=(0.05, 0.45), validation=(0.55, 0.78), test=(0.80, 0.99)) -> dict[str, Audio]:
    """Nonoverlapping chronological windows; fraction of full clip length."""
    limits = [training, validation, test]
    if not all(0 <= a < b <= 1 for a, b in limits):
        raise ValueError("Invalid split bounds")
    if not (training[1] <= validation[0] and validation[1] <= test[0]):
        raise ValueError("Overlapping windows would leak validation data")
    out = {}
    for name, (a, b) in zip(("training", "validation", "test"), limits):
        x = audio.samples[round(a * len(audio.samples)):round(b * len(audio.samples))]
        if len(x) < audio.rate // 10:
            raise ValueError("A split is too short")
        out[name] = Audio(x, audio.rate)
    return out


def _mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1)


def _envelope(x: np.ndarray, sr: int, ms: float) -> np.ndarray:
    mono = _mono(x)
    width = max(1, round(sr * ms / 1000))
    full = len(mono) // width
    if full < 2:
        raise ValueError("Insufficient audio for envelope")
    frames = mono[:full * width].reshape(full, width)
    return np.sqrt(np.mean(frames ** 2, axis=1) + EPS ** 2)


def _db(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.maximum(x, EPS))


def _peak_db(x: np.ndarray) -> float:
    return float(_db(np.array([np.max(np.abs(x))]))[0])


def _truepeak_db(x: np.ndarray, factor: int = 4) -> float:
    # Approximate oversampled true peak; not a certified ITU BS.1770 meter.
    peaks = [np.max(np.abs(signal.resample_poly(x[:, ch], factor, 1))) for ch in range(x.shape[1])]
    return float(_db(np.array([max(peaks)]))[0])


def _stft_distance(a: np.ndarray, b: np.ndarray, sr: int) -> float:
    """Mean log-magnitude error (dB), averaged over multiple FFT resolutions."""
    diffs = []
    for n in (512, 2048, 8192):
        n = min(n, len(a), len(b))
        if n < 128:
            continue
        _, _, A = signal.stft(_mono(a), fs=sr, nperseg=n, noverlap=n // 2, boundary=None)
        _, _, B = signal.stft(_mono(b), fs=sr, nperseg=n, noverlap=n // 2, boundary=None)
        # Ignore near-silent bins; report a comparable active-band metric.
        mag_a = np.abs(A)
        mag_b = np.abs(B)
        active = (mag_a > max(float(np.max(mag_a)) * 1e-4, 1e-8)) | (mag_b > max(float(np.max(mag_b)) * 1e-4, 1e-8))
        diffs.append(float(np.mean(np.abs(_db(mag_a[active]) - _db(mag_b[active])))) if np.any(active) else 0.0)
    return float(np.mean(diffs))


def compare(reference: Audio, candidate: Audio, *, allow_shorter: bool = False) -> dict:
    """No automatic gain, polarity flip or time alignment (which could hide errors)."""
    if reference.rate != candidate.rate:
        raise ValueError("Sample rates differ: resample deliberately before comparing")
    if reference.samples.shape[1] != candidate.samples.shape[1]:
        raise ValueError("Channel counts differ: downmixing silently would conceal stereo errors")
    a, b = reference.samples, candidate.samples
    if not allow_shorter and len(a) != len(b):
        raise ValueError("Sample counts differ: align the same take first")
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if not np.isfinite(b).all():
        raise ValueError("Non-finite candidate")
    # Correlation remains signed so polarity differences are visible.
    am, bm = _mono(a), _mono(b)
    corr = float(np.corrcoef(am, bm)[0, 1]) if np.std(am) > EPS and np.std(bm) > EPS else 0.0
    env = {}
    for ms in (5, 20, 200):
        ea, eb = _envelope(a, reference.rate, ms), _envelope(b, reference.rate, ms)
        mask = ea > np.max(ea) * 10 ** (-35 / 20)
        env[f"{ms}ms_active_error_db"] = float(np.mean(np.abs(_db(ea[mask]) - _db(eb[mask])))) if np.any(mask) else float("nan")
    residual = b - a
    return {
        "sample_rate": reference.rate,
        "samples": n,
        "channels": a.shape[1],
        "waveform_correlation_signed": corr,
        "null_residual_rms_db_relative_to_reference": float(_db(np.array([np.sqrt(np.mean(residual ** 2)) / max(np.sqrt(np.mean(a ** 2)), EPS)]))[0]),
        "reference_sample_peak_dbfs": _peak_db(a),
        "candidate_sample_peak_dbfs": _peak_db(b),
        "candidate_true_peak_dbfs_4x_estimate": _truepeak_db(b),
        "candidate_rms_dbfs": float(_db(np.array([np.sqrt(np.mean(b ** 2))]))[0]),
        "multires_log_spectral_error_db": _stft_distance(a, b, reference.rate),
        **env,
    }


def gain_audio(audio: Audio, gain_db: float) -> Audio:
    if not np.isfinite(gain_db) or abs(gain_db) > 48:
        raise ValueError("Invalid or excessive gain")
    return Audio(audio.samples * (10 ** (gain_db / 20)), audio.rate)


def optimize_gain(dry: Audio, target: Audio, *, ceiling_dbtp: float = -1.0) -> float:
    """Fit ONE gain parameter on the supplied *training split only*."""
    if dry.rate != target.rate or dry.samples.shape != target.samples.shape:
        raise ValueError("Dry and target must be sample aligned and have matching channels")
    if not np.isfinite(ceiling_dbtp) or ceiling_dbtp > 0:
        raise ValueError("Unsafe ceiling")
    # Stop excessive gain before the optimizer; never silently attenuate its output.
    max_gain = min(24.0, ceiling_dbtp - _truepeak_db(dry.samples))
    if max_gain < -24.0:
        raise ValueError("Input exceeds safe ceiling by more than 24 dB")
    ref = _envelope(target.samples, target.rate, 20)
    source = _envelope(dry.samples, dry.rate, 20)
    active = ref > max(ref) * 10 ** (-35 / 20)
    if not active.any():
        raise ValueError("No active reference frames")
    def objective(g: float) -> float:
        return float(np.mean(np.abs((_db(source[active]) + g) - _db(ref[active]))))
    result = optimize.minimize_scalar(objective, bounds=(-24, max_gain), method="bounded", options={"xatol": 0.001})
    if not result.success:
        raise RuntimeError("Gain optimization failed")
    return float(result.x)
