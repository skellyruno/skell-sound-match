"""Evidence-aware MAIN-chain dynamics diagnostic (not compressor emulation).

Fruity Compressor's visible threshold / attack / release / ratio can be used as
an *envelope-detector hypothesis*.  This code deliberately does not claim that
its GR curve equals FL Studio's proprietary plugin response.  Results and
source audio remain local: only synthetic regression tests enter Git history.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class CompressorAnchor:
    threshold_db: float = -24.0
    ratio: float = 4.0
    attack_ms: float = 10.0
    release_ms: float = 100.0
    makeup_gain_db: float = 0.0
    frame_ms: float = 5.0

    def validate(self) -> None:
        numbers = list(asdict(self).values())
        if not all(np.isfinite(numbers)):
            raise ValueError('Compressor settings must be finite')
        if not (-100 <= self.threshold_db <= 12 and 1 <= self.ratio <= 100
                and .05 <= self.attack_ms <= 3000 and .05 <= self.release_ms <= 10000
                and -48 <= self.makeup_gain_db <= 48 and .5 <= self.frame_ms <= 100):
            raise ValueError('Invalid compressor settings')


def mono_wav(path: str | Path) -> tuple[np.ndarray, int]:
    x, sr = sf.read(path, always_2d=True, dtype='float64')
    if x.shape[1] not in (1, 2) or sr < 8000 or not np.isfinite(x).all():
        raise ValueError('Invalid audio; only mono/dual-mono PCM supported')
    mid = x.mean(axis=1)
    if x.shape[1] == 2 and np.sqrt(np.mean(np.square(x[:, 0] - x[:, 1]))) > .06 * max(np.sqrt(np.mean(mid * mid)), 1e-9):
        raise ValueError('Meaningful stereo differences require stereo-aware analysis')
    if len(mid) < int(sr * .2):
        raise ValueError('Audio too short')
    return mid, int(sr)


def rms_db_frames(signal: np.ndarray, sample_rate: int, frame_ms: float = 5.0) -> np.ndarray:
    if np.ndim(signal) != 1 or not np.isfinite(signal).all():
        raise ValueError('Invalid signal')
    width = max(1, int(round(sample_rate * frame_ms / 1000)))
    n = len(signal) // width
    if n == 0:
        raise ValueError('Insufficient frames')
    frames = signal[:n * width].reshape(n, width)
    return 20 * np.log10(np.maximum(1e-10, np.sqrt(np.mean(frames * frames, axis=1))))


def envelope_hypothesis(x: np.ndarray, sr: int, config: CompressorAnchor = CompressorAnchor()) -> dict[str, np.ndarray]:
    """Frame-rate attack/release approximation to gauge GR *trend*, not the actual FL plugin."""
    config.validate()
    levels = rms_db_frames(x, sr, config.frame_ms)
    attack = float(np.exp(-config.frame_ms / config.attack_ms))
    release = float(np.exp(-config.frame_ms / config.release_ms))
    detector = np.empty_like(levels)
    detector[0] = levels[0]
    for i in range(1, len(levels)):
        a = attack if levels[i] > detector[i - 1] else release
        detector[i] = a * detector[i - 1] + (1 - a) * levels[i]
    gain_reduction = -np.maximum(0, detector - config.threshold_db) * (1 - 1 / config.ratio)
    return {'level_db': levels, 'detector_db': detector, 'hypothetical_gr_db': gain_reduction,
            'hypothetical_output_gain_db': gain_reduction + config.makeup_gain_db}


def stage_report(input_path: str | Path, output_path: str | Path,
                 config: CompressorAnchor = CompressorAnchor()) -> dict:
    """Reports whole-chain observed gain; never attributes it solely to one plugin."""
    inp, sr = mono_wav(input_path)
    out, s2 = mono_wav(output_path)
    if sr != s2 or len(inp) != len(out):
        raise ValueError('Inputs require the same sample rate, samples and take')
    hyp = envelope_hypothesis(inp, sr, config)
    received = rms_db_frames(out, sr, config.frame_ms)
    measured = received - hyp['level_db']
    mask = (hyp['level_db'] > -55) & (received > -55)
    if not np.any(mask):
        raise ValueError('No active frames to compare')
    return {
        'sample_rate': sr, 'frames': len(inp),
        'anchor': asdict(config),
        'status': 'diagnostic_only_not_vendor_dsp_reproduction',
        'active_frames': int(mask.sum()),
        'main_chain_gain_db_p10_p50_p90': [round(float(v), 4) for v in np.percentile(measured[mask], [10, 50, 90])],
        'hypothetical_compressor_gr_db_p10_p50_p90': [round(float(v), 4) for v in np.percentile(hyp['hypothetical_gr_db'][mask], [10, 50, 90])],
        'note': 'Observed gain includes every plugin, EQ and routing; cannot identify compressor gain reduction by itself.',
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input_wav'); ap.add_argument('processed_wav')
    ap.add_argument('--out', help='New JSON report (refuses overwrite)')
    ap.add_argument('--threshold-db', type=float, default=-24)
    ap.add_argument('--ratio', type=float, default=4)
    ap.add_argument('--attack-ms', type=float, default=10)
    ap.add_argument('--release-ms', type=float, default=100)
    ap.add_argument('--makeup-gain-db', type=float, default=0)
    args = ap.parse_args()
    config = CompressorAnchor(args.threshold_db, args.ratio, args.attack_ms,
                              args.release_ms, args.makeup_gain_db)
    r = stage_report(args.input_wav, args.processed_wav, config)

    if args.out:
        dest = Path(args.out)
        if dest.exists():
            raise FileExistsError(dest)
        dest.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(r, indent=2))


if __name__ == '__main__':
    main()
