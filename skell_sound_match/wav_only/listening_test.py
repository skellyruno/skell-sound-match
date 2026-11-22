"""Private, level-matched, safety-checked, blinded same-take A/B sessions.

Experimental offline listening helper. Never uploads audio, edits originals,
certifies true peaks or claims independent performance matching. The owner
keeps answer_key.json private until ratings are recorded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import secrets
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

from .skelly_reference_eq_trial import truepeak


def _read(path: Path):
    audio, sample_rate = sf.read(path, always_2d=True, dtype='float64')
    if not (32000 <= sample_rate <= 192000):
        raise ValueError('Only 32–192 kHz audio supported')
    if audio.ndim != 2 or audio.shape[1] not in (1, 2) or len(audio) < sample_rate:
        raise ValueError('Only >=1-second mono or stereo recordings supported')
    if not np.isfinite(audio).all():
        raise ValueError('Nonfinite audio')
    return audio, sample_rate


def _hash(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def prepare_pair(reference_path: Path, candidate_path: Path, output_dir: Path, *,
                 start_seconds: float = 0.0, duration_seconds: float | None = None,
                 target_lufs: float = -18.0, seed: int | None = None) -> dict:
    """Write A/B FLAC and a separate private key. No gain optimization on test audio."""
    reference_path = Path(reference_path).expanduser().resolve()
    candidate_path = Path(candidate_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if reference_path == candidate_path:
        raise ValueError('Reference and candidate must be separate files')
    if not (math.isfinite(target_lufs) and -35 <= target_lufs <= -10):
        raise ValueError('Target loudness must be finite and between -35 and -10 LUFS')
    if not (math.isfinite(start_seconds) and start_seconds >= 0):
        raise ValueError('Start must be a finite nonnegative time')
    if duration_seconds is not None and not (math.isfinite(duration_seconds) and duration_seconds >= 1):
        raise ValueError('Duration must be >=1 second')

    originals = [reference_path, candidate_path]
    filenames = ('A.flac', 'B.flac', 'LISTENING_SESSION.md', 'answer_key.json')
    dest = [output_dir / name for name in filenames]
    if any(o in originals for o in dest):
        raise ValueError('Output file collides with source')
    if any(o.exists() for o in dest):
        raise FileExistsError('Refusing to overwrite an existing listening session')

    ref, rate = _read(reference_path)
    trial, rate2 = _read(candidate_path)
    if rate != rate2 or ref.shape != trial.shape:
        raise ValueError('Different sample rate, channels, length or start offset; align before A/B')
    start = int(round(start_seconds * rate))
    stop = len(ref) if duration_seconds is None else min(len(ref), start + int(round(duration_seconds * rate)))
    if stop - start < rate:
        raise ValueError('Clip interval shorter than one second')
    ref = ref[start:stop]
    trial = trial[start:stop]
    meter = pyln.Meter(rate)
    before = [float(meter.integrated_loudness(v)) for v in (ref, trial)]
    if not all(math.isfinite(x) for x in before):
        raise ValueError('Cannot loudness-match silent or nonfinite input')
    adjusted = [v * 10 ** ((target_lufs - loudness) / 20) for v, loudness in zip((ref, trial), before)]

    # One shared attenuation after matching keeps the A and B levels equivalent.
    measured_tp = [truepeak(v) for v in adjusted]
    common_trim_db = min(0.0, -1.25 - max(measured_tp))
    shared = 10 ** (common_trim_db / 20)
    adjusted = [v * shared for v in adjusted]
    if any(not np.isfinite(v).all() or np.max(np.abs(v)) >= 1 for v in adjusted):
        raise ValueError('Unsafe matched preview')
    final_tp = [truepeak(v) for v in adjusted]
    if max(final_tp) > -1.19:
        raise ValueError('Estimated 4x true-peak guard failed')
    measured_lufs = [float(meter.integrated_loudness(v)) for v in adjusted]
    if abs(measured_lufs[0] - measured_lufs[1]) > 0.08:
        raise ValueError('Loudness matching tolerance exceeded')

    # Seed is optional to allow reproducibility for explicitly repeatable tests.
    swap = bool((secrets.randbits(1) if seed is None else __import__('random').Random(seed).getrandbits(1)))
    a, b = (adjusted[1], adjusted[0]) if swap else (adjusted[0], adjusted[1])
    output_dir.mkdir(parents=True, exist_ok=True)
    # Files are written only after all samples and safety checks have passed.
    sf.write(dest[0], a, rate, subtype='PCM_24')
    sf.write(dest[1], b, rate, subtype='PCM_24')
    # Confirm encoded output is also safe, not just the in-memory samples.
    encoded_tp = [truepeak(sf.read(p, always_2d=True, dtype='float64')[0]) for p in dest[:2]]
    if max(encoded_tp) > -1.19:
        for p in dest[:2]:
            p.unlink(missing_ok=True)
        raise ValueError('Encoded preview exceeded estimated true-peak guard')

    readme = ('# Blind Skelly A/B listening session\n\n'
              'Listen to **A.flac** and **B.flac** at the same device/volume settings. '
              'Record which you prefer and why (tone, consonants, dynamics, sibilance, '
              'stereo image, delay/reverb, artifacts) before opening **answer_key.json**.\n\n'
              'Both files were LUFS-matched and given the SAME safety attenuation. '
              'This is a 4x interpolated-peak estimate, not certified true-peak limiting.\n'
              'Only a different time segment of the SAME performance is tested; '
              'independent-take and native plugin verification remain separate.\n')
    dest[2].write_text(readme, encoding='utf-8')
    key = {'schema': 'skelly.private.blind-ab.v1', 'sample_rate': rate,
           'frames': len(ref), 'start_seconds': start_seconds,
           'duration_seconds': len(ref) / rate, 'target_lufs': target_lufs,
           'measured_lufs_final': measured_lufs,
           'measured_pretrim_truepeak_4x_dbtp': measured_tp,
           'measured_encoded_truepeak_4x_dbtp': encoded_tp,
           'common_safety_trim_db': common_trim_db,
           'source_sha256': {'reference': _hash(reference_path), 'candidate': _hash(candidate_path)},
           'blind_mapping': {'A': 'candidate' if swap else 'reference',
                             'B': 'reference' if swap else 'candidate'},
           'original_file_names': {'reference': reference_path.name, 'candidate': candidate_path.name},
           'provenance': 'same-performance and alignment are user/operator assertions; not independently verified',
           'status': 'BLIND_LISTENING_ONLY_NOT_A_PRESET_APPROVAL'}
    dest[3].write_text(json.dumps(key, indent=2) + '\n', encoding='utf-8')
    return {'status': key['status'], 'sample_rate': rate, 'duration_seconds': len(ref)/rate,
            'output_dir': str(output_dir), 'A': 'A.flac', 'B': 'B.flac',
            'answer_key': 'answer_key.json (PRIVATE; review after ratings)',
            'common_safety_trim_db': common_trim_db,
            'maximum_estimated_encoded_truepeak_dbtp': max(encoded_tp)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('candidate', type=Path)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--start', type=float, default=0.0)
    p.add_argument('--duration', type=float)
    p.add_argument('--target-lufs', type=float, default=-18.0)
    p.add_argument('--seed', type=int, help='For deterministic local regressions, not actual blinded studies')
    args = p.parse_args()
    result = prepare_pair(args.reference, args.candidate, args.output_dir,
                          start_seconds=args.start, duration_seconds=args.duration,
                          target_lufs=args.target_lufs, seed=args.seed)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
