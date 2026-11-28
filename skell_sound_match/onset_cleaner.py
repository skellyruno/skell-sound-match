"""Experimental dry/reference-free pre-echo mask for offline matched vocal renders.

Detects major phrases from the *candidate audio*, delays only their gate opening,
and leaves all active speech samples after each short fade unchanged. This does
not clone the reference recording and does not use reference audio at inference.
Noncausal onset detection; not a ready-to-ship real-time VST3 processor.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class OnsetConfig:
    threshold_dbfs: float = -60.0
    analysis_ms: float = 5.0
    min_phrase_ms: float = 160.0
    merge_gap_ms: float = 90.0
    onset_holdoff_ms: float = 40.0
    pre_lookback_ms: float = 90.0
    fade_ms: float = 2.0
    min_phrase_gap_ms: float = 180.0


def _valid(x: np.ndarray, sample_rate: int, config: OnsetConfig):
    if x.ndim != 2 or x.shape[1] not in (1, 2) or not np.isfinite(x).all():
        raise ValueError("finite mono or stereo candidate required")
    if sample_rate < 16000 or sample_rate > 192000 or len(x) < sample_rate:
        raise ValueError("unsupported sample rate or duration")
    for field in (config.threshold_dbfs, config.analysis_ms, config.min_phrase_ms,
                  config.merge_gap_ms, config.onset_holdoff_ms,
                  config.pre_lookback_ms, config.fade_ms, config.min_phrase_gap_ms):
        if not np.isfinite(field):
            raise ValueError("nonfinite configuration")
    if not (-110 <= config.threshold_dbfs <= -15) or not (1 <= config.analysis_ms <= 30):
        raise ValueError("unsafe threshold/analysis window")
    if not (40 <= config.min_phrase_ms <= 1000 and 0 <= config.merge_gap_ms <= 200
            and 0 <= config.onset_holdoff_ms <= 80 and 0 <= config.pre_lookback_ms <= 150
            and .1 <= config.fade_ms <= 20 and 0 <= config.min_phrase_gap_ms <= 500):
        raise ValueError("unsafe onset parameters")


def major_phrases(candidate: np.ndarray, sr: int, config: OnsetConfig) -> list[tuple[int, int]]:
    _valid(candidate, sr, config)
    w = max(1, round(config.analysis_ms * sr / 1000))
    mono = candidate.mean(axis=1)
    n = len(mono) // w
    rms = np.sqrt(np.maximum(np.mean(mono[:n*w].reshape(n, w) ** 2, axis=1), 1e-18))
    mask = rms > 10 ** (config.threshold_dbfs / 20)
    # Close short interior gaps to avoid retriggering on syllables.
    merge = max(1, round(config.merge_gap_ms / config.analysis_ms))
    mask = ndimage.binary_closing(mask, structure=np.ones(merge + 1), border_value=0)
    labels, total = ndimage.label(mask)
    segments = []
    for i in range(1, total + 1):
        hits = np.where(labels == i)[0]
        if len(hits) * config.analysis_ms < config.min_phrase_ms:
            continue
        segments.append((int(hits[0] * w), int(min(len(candidate), (hits[-1] + 1) * w))))
    return segments


def clean_onsets(candidate: np.ndarray, sr: int, config: OnsetConfig = OnsetConfig()) -> tuple[np.ndarray, dict]:
    """Return *new* audio; never edit input array. Reference not required."""
    parts = major_phrases(candidate, sr, config)
    out = candidate.copy()
    masked = []
    previous_end = -10**9
    for start, stop in parts:
        if start - previous_end < round(sr * config.min_phrase_gap_ms / 1000):
            previous_end = stop
            continue
        begin = max(0, start - round(sr * config.pre_lookback_ms / 1000))
        # Do not erase a preceding phrase's release.
        begin = max(begin, previous_end + 1)
        gate_end = min(len(out), start + round(sr * config.onset_holdoff_ms / 1000))
        if gate_end >= stop:
            previous_end = stop
            continue
        out[begin:gate_end] = 0.0
        f = max(1, round(sr * config.fade_ms / 1000))
        f_end = min(len(out), gate_end + f)
        out[gate_end:f_end] *= np.linspace(0, 1, f_end-gate_end, endpoint=True)[:, None]
        masked.append((begin, gate_end, f_end))
        previous_end = stop
    return out, {"phrase_starts_samples": [s for s, _ in parts],
                 "masked_intervals_samples": masked,
                 "note": "Fixed onset holdoff learned from training-only material; never assumed transferable."}


def cli(argv: list[str] | None = None) -> None:
    """Run locally; require explicit settings because onsets are voice dependent."""
    import argparse
    import hashlib
    import json
    from pathlib import Path
    import soundfile as sf
    from scipy import signal

    parser = argparse.ArgumentParser(description="Offline pre-echo onset correction (experimental)")
    parser.add_argument("source")
    parser.add_argument("--wav", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--threshold-dbfs", type=float, required=True)
    parser.add_argument("--holdoff-ms", type=float, required=True)
    parser.add_argument("--pre-lookback-ms", type=float, default=90.0)
    parser.add_argument("--fade-ms", type=float, default=2.0)
    args = parser.parse_args(argv)
    src = Path(args.source)
    dst, report = Path(args.wav), Path(args.report)
    if src.resolve() in (dst.resolve(), report.resolve()) or dst.resolve() == report.resolve():
        raise ValueError("Source, WAV and report paths must differ")
    if dst.exists() or report.exists():
        raise FileExistsError("WAV or report already exists; refusing to overwrite")
    data, sr = sf.read(str(src), always_2d=True, dtype="float64")
    conf = OnsetConfig(threshold_dbfs=args.threshold_dbfs,
                       onset_holdoff_ms=args.holdoff_ms,
                       pre_lookback_ms=args.pre_lookback_ms,
                       fade_ms=args.fade_ms)
    result, evidence = clean_onsets(data, sr, conf)
    if not np.isfinite(result).all():
        raise ValueError("Invalid resulting waveform")
    before = max(float(np.max(np.abs(signal.resample_poly(data[:,c],4,1)))) for c in range(data.shape[1]))
    after = max(float(np.max(np.abs(signal.resample_poly(result[:,c],4,1)))) for c in range(result.shape[1]))
    if after > before * 10 ** (.15/20) + 1e-8 or after > 1.0:
        raise ValueError("Output created an unsafe intersample peak")
    src_sha = hashlib.sha256(src.read_bytes()).hexdigest()
    dst.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    # We have already checked existence; x-mode protects against accidental reruns.
    with dst.open("xb") as fh:
        sf.write(fh, result, sr, format="WAV", subtype="PCM_24")
    metadata = {
        "status": "experimental_offline_not_release_approved",
        "reference_was_used_during_rendering": False,
        "source_sha256": src_sha,
        "output_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
        "parameters": vars(conf), "events": evidence,
        "estimated_true_peak_before_dbtp": float(20*np.log10(max(before,1e-12))),
        "estimated_true_peak_after_dbtp": float(20*np.log10(max(after,1e-12))),
        "note": "Settings must be calibrated on other source material before reuse. No automatic champion promotion."
    }
    with report.open("x", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
        fh.write("\n")
    print(json.dumps({"output_written": True,
                      "onset_corrections": len(evidence["masked_intervals_samples"]),
                      "status": metadata["status"]}, indent=2))


if __name__ == "__main__":
    cli()