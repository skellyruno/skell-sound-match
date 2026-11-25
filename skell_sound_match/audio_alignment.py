"""Spectrotemporal *diagnostic* alignment, not proof of recording identity.

Use trusted DAW session metadata and audio-manifest hashes to verify identity.
Audio may exhibit strong similarity after copying, pitch-shifting or other edits;
weak similarity may also result from aggressive DSP applied to a true same take.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
import numpy as np
from scipy.signal import stft


@dataclass(frozen=True)
class AlignmentDiagnostic:
    best_similarity: float
    offset_seconds: float
    overlap_seconds: float
    hop_seconds: float
    # Always false: a score is *never* sufficient to establish take provenance.
    identity_verified: bool = False


def _bands(x: np.ndarray, sample_rate: int, hop: int) -> np.ndarray:
    # A time-dependent spectral signature, insensitive to signal polarity and
    # mostly insensitive to overall loudness / equalization. Not a fingerprint.
    mono = np.mean(x, axis=1)
    freq, _, spectrum = stft(mono, fs=sample_rate, nperseg=2048,
                             noverlap=2048-hop, boundary=None, padded=False)
    power = np.abs(spectrum) ** 2
    out = []
    for low, high in ((80, 250), (250, 600), (600, 1300),
                      (1300, 2800), (2800, 6000), (6000, 12000)):
        use = (freq >= low) & (freq < high)
        energy = np.sum(power[use], axis=0)
        # A per-recording relative floor preserves invariance to overall gain.
        floor = max(float(np.max(energy)) * 1e-8, np.finfo(float).tiny)
        level = np.log(np.maximum(energy, floor))
        sigma = float(np.std(level))
        out.append(np.clip((level - np.mean(level)) / max(sigma, 0.1), -4, 4))
    return np.stack(out, axis=1)


def alignment_diagnostic(source: np.ndarray, candidate: np.ndarray,
                         sample_rate: int, *, maximum_offset_seconds: float = 1.0,
                         minimum_overlap_seconds: float = 1.0) -> AlignmentDiagnostic:
    """Compare *similarity*, not same-take provenance.

    Positive offsets mean candidate content occurs later on its timebase.
    No audio material is written or cached by this function.
    """
    if type(sample_rate) is not int or not 32000 <= sample_rate <= 192000:
        raise ValueError('invalid sample rate')
    if not (isfinite(maximum_offset_seconds) and 0 <= maximum_offset_seconds <= 10
            and isfinite(minimum_overlap_seconds) and 0.5 <= minimum_overlap_seconds <= 60):
        raise ValueError('invalid alignment range')
    inputs = []
    for x in (source, candidate):
        y = np.asarray(x)
        if y.ndim != 2 or y.shape[1] not in (1, 2) or len(y) < sample_rate * minimum_overlap_seconds or not np.isfinite(y).all():
            raise ValueError('invalid or insufficient source/candidate audio')
        if np.max(np.abs(y)) < 1e-8:
            raise ValueError('silent input cannot establish alignment')
        inputs.append(y.astype(np.float64, copy=False))
    hop = max(1, round(sample_rate * .010))
    a, b = (_bands(x, sample_rate, hop) for x in inputs)
    min_frames = int(np.ceil(minimum_overlap_seconds * sample_rate / hop))
    best = None
    for offset in range(-round(maximum_offset_seconds * sample_rate / hop),
                        round(maximum_offset_seconds * sample_rate / hop)+1):
        ia = max(0, -offset)
        ib = max(0, offset)
        length = min(len(a)-ia, len(b)-ib)
        if length < min_frames:
            continue
        x, y = a[ia:ia+length], b[ib:ib+length]
        norm = np.sqrt(np.sum(x*x)*np.sum(y*y))
        sim = float(np.sum(x*y) / norm) if norm > 1e-14 else 0.0
        if best is None or sim > best[0]:
            best = (sim, offset * hop / sample_rate, length * hop / sample_rate)
    if best is None:
        raise ValueError('no valid overlap')
    return AlignmentDiagnostic(float(np.clip(best[0], -1., 1.)), best[1], best[2], hop / sample_rate)
