"""Deuce v2.5 - listener-preferred offline research; not yet a native VST3 preset.

Fixed 7-kHz presence compensation for the earlier v2.3
Sustained Air candidate (not for direct use on dry vocals). Parameters chosen
using only the first 4.8 seconds of the original reference on a 44.1-kHz take.
Evaluation sections are separate, but from the same performance.

All processing is driven only by the input, with no future samples, source
reference waveforms, phrase boundaries, or per-phrase decisions at render time.
DSP primitive: single causal RBJ peaking EQ, processing per channel.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from scipy import signal
import soundfile as sf

CENTER_HZ = 7000.0
Q = 0.75
GAIN_DB = 0.75
# Calibrated only on the first 0-4.8 s vs protected D/Max, not the reference.
OUTPUT_GAIN_DB = -0.1467149783536854


def coefficients(sample_rate: int) -> np.ndarray:
    if not 2 * CENTER_HZ < sample_rate <= 384000:
        raise ValueError("Sample rate does not support the 7 kHz band")
    a = 10 ** (GAIN_DB / 40)
    omega = 2 * np.pi * CENTER_HZ / sample_rate
    alpha = np.sin(omega) / (2 * Q)
    c = -2 * np.cos(omega)
    a0 = 1 + alpha / a
    return np.array([[
        (1 + alpha * a) / a0, c / a0, (1 - alpha * a) / a0,
        1., c / a0, (1 - alpha / a) / a0,
    ]], dtype=np.float64)


def render(input_audio: np.ndarray, sample_rate: int, block_size: int | None = None) -> np.ndarray:
    """Causal render; block_size simulates streaming without hidden lookahead."""
    x = np.asarray(input_audio, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] not in (1, 2):
        raise ValueError("Expected [frames, 1 or 2 channels]")
    if not np.isfinite(x).all():
        raise ValueError("Input contains NaN or infinity")
    sos = coefficients(sample_rate)
    g = 10 ** (OUTPUT_GAIN_DB / 20)
    if block_size is None:
        return signal.sosfilt(sos, x, axis=0) * g
    if block_size < 1:
        raise ValueError("block_size must be positive")
    zi = np.zeros((len(sos), 2, x.shape[1]), dtype=np.float64)
    chunks = []
    for start in range(0, len(x), block_size):
        y, zi = signal.sosfilt(sos, x[start:start+block_size], axis=0, zi=zi)
        chunks.append(y * g)
    return np.vstack(chunks) if chunks else x.copy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="existing v2.3 processed lossless audio")
    parser.add_argument("output", type=Path, help="new file; refuses overwrite")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite: {args.output}")
    x, sr = sf.read(args.input, dtype="float64", always_2d=True)
    out = render(x, sr, block_size=512)
    if not np.isfinite(out).all() or np.max(np.abs(out), initial=0.0) > 1.0:
        raise ValueError("Unsafe render: nonfinite or clipping")
    sf.write(args.output, out, sr, subtype="PCM_24")
    print(f"Wrote {args.output}: {sr} Hz, {len(out)} frames, {out.shape[1]}ch")


if __name__ == "__main__":
    main()
