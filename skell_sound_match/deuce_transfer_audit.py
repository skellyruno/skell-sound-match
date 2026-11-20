"""Unseen-performance validation for the frozen Deuce v2.5 presence stage.

Input MUST be the already-rendered v2.3 candidate for another vocal take.
This applies the frozen finishing stage only; it does not fit parameters or
recreate the original REC->MAIN chain. A same-performance REC->MAIN target is
used only for scoring and is never passed into the render path.

Offline research only. This is not native VST3 or real-time DSP.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from .deuce_presence_repair import CENTER_HZ, Q, GAIN_DB, OUTPUT_GAIN_DB, render


def _read(path: Path):
    audio, rate = sf.read(path, always_2d=True, dtype="float64")
    if not 32000 <= rate <= 192000 or audio.shape[1] not in (1, 2):
        raise ValueError("Only 32–192 kHz mono/stereo references are supported")
    if audio.shape[0] < rate or not np.isfinite(audio).all():
        raise ValueError("Need at least one second of finite audio")
    return audio, rate


def _db(amplitude: float) -> float:
    return 20.0 * math.log10(max(amplitude, 1e-14))


def _true_peak_4x(audio: np.ndarray) -> float:
    reconstructed = signal.resample_poly(audio, 4, 1, axis=0)
    return _db(float(np.max(np.abs(reconstructed))))


def _levels(audio: np.ndarray, rate: int) -> dict:
    meter = pyln.Meter(rate)
    return {
        "lufs": float(meter.integrated_loudness(audio)),
        "sample_peak_dbfs": _db(float(np.max(np.abs(audio)))),
        "estimated_true_peak_dbtp_4x": _true_peak_4x(audio),
    }


def _level_match_for_analysis(audio: np.ndarray, target_lufs: float, rate: int):
    level = _levels(audio, rate)["lufs"]
    if not (math.isfinite(level) and math.isfinite(target_lufs)):
        raise ValueError("Cannot level-match silent/nonfinite audio")
    return audio * (10.0 ** ((target_lufs - level) / 20.0))


def _band_error(reference, candidate, rate, low_hz, high_hz):
    if high_hz >= rate / 2:
        raise ValueError("Analysis band exceeds Nyquist")
    ref = reference.mean(axis=1)
    cand = candidate.mean(axis=1)
    frequencies, _, ref_stft = signal.stft(
        ref, fs=rate, nperseg=2048, noverlap=1536,
        boundary=None, padded=False,
    )
    _, _, cand_stft = signal.stft(
        cand, fs=rate, nperseg=2048, noverlap=1536,
        boundary=None, padded=False,
    )
    selected = (frequencies >= low_hz) & (frequencies <= high_hz)
    if not np.any(selected):
        raise ValueError("Analysis band is empty at this sample rate")
    ref_level = np.sqrt(np.mean(np.abs(ref_stft[selected]) ** 2, axis=0) + 1e-18)
    cand_level = np.sqrt(np.mean(np.abs(cand_stft[selected]) ** 2, axis=0) + 1e-18)
    active = ref_level > max(float(ref_level.max()) * 0.025, 1e-9)
    count = int(np.count_nonzero(active))
    if count < 10:
        return {"mean_absolute_db": None, "active_frames": count}
    error_db = 20.0 * np.log10(
        (cand_level[active] + 1e-10) / (ref_level[active] + 1e-10)
    )
    return {"mean_absolute_db": float(np.mean(np.abs(error_db))), "active_frames": count}


def evaluate(v23_candidate: np.ndarray, rate: int, target: np.ndarray | None = None):
    """Render from candidate only; optional same-take target is evaluation-only."""
    output = render(v23_candidate, rate, block_size=512)
    report = {
        "schema": "skell.deuce-v25.unseen-transfer-audit",
        "version": 1,
        "algorithm_frozen": True,
        "causal_candidate_only": True,
        "native_vst3_verified": False,
        "source_role": "v2.3 candidate audio, not original dry recording",
        "presence": {
            "frequency_hz": CENTER_HZ,
            "q": Q,
            "gain_db": GAIN_DB,
            "output_trim_db": OUTPUT_GAIN_DB,
        },
        "duration_s": len(v23_candidate) / rate,
        "sample_rate": rate,
        "channels": v23_candidate.shape[1],
        "candidate_input": _levels(v23_candidate, rate),
        "trial": _levels(output, rate),
        "finite": bool(np.isfinite(output).all()),
        "stereo_shape_preserved": bool(output.shape == v23_candidate.shape),
        "render_chunk_consistency_max_error": float(
            np.max(np.abs(output - render(v23_candidate, rate)))
        ),
        "has_original_rec_main_target": target is not None,
        "claim": "Safety audit only" if target is None else
                 "Same-performance, frozen-parameter matching audit",
        "no_automatic_promotion": True,
    }
    if target is not None:
        if target.shape != v23_candidate.shape or not np.isfinite(target).all():
            raise ValueError("Target must match candidate sample count, channels and start offset")
        target_lufs = _levels(target, rate)["lufs"]
        base_matched = _level_match_for_analysis(v23_candidate, target_lufs, rate)
        trial_matched = _level_match_for_analysis(output, target_lufs, rate)
        metrics = {}
        for low_hz, high_hz in ((4500, 7900), (9000, 14000)):
            key = f"{low_hz}_{high_hz}_hz"
            baseline = _band_error(target, base_matched, rate, low_hz, high_hz)
            repaired = _band_error(target, trial_matched, rate, low_hz, high_hz)
            metrics[key] = {
                "baseline": baseline,
                "v25": repaired,
                "delta_mae_db": (
                    None if baseline["mean_absolute_db"] is None
                    or repaired["mean_absolute_db"] is None
                    else repaired["mean_absolute_db"] - baseline["mean_absolute_db"]
                ),
            }
        report["target"] = _levels(target, rate)
        report["analysis_only_loudness_matched_to_target"] = True
        report["band_metrics"] = metrics
    return output, report


def run(candidate_path: Path, output_path: Path, report_path: Path,
        target_path: Path | None = None):
    paths = [candidate_path.resolve(), output_path.resolve(), report_path.resolve()]
    if target_path is not None:
        paths.append(target_path.resolve())
    if len(set(paths)) != len(paths):
        raise ValueError("Input/output path collision")
    if output_path.exists() or report_path.exists():
        raise FileExistsError("Refusing to overwrite an existing output")
    candidate, rate = _read(candidate_path)
    target = None
    if target_path is not None:
        target, target_rate = _read(target_path)
        if target_rate != rate:
            raise ValueError("Target sample rate mismatch")
    output, report = evaluate(candidate, rate, target)
    if not report["finite"] or float(np.max(np.abs(output))) > 1.0:
        raise ValueError("Unsafe output: nonfinite or sample-clipped")
    if report["trial"]["estimated_true_peak_dbtp_4x"] > -1.0:
        raise ValueError("Unsafe output: estimated 4x true peak exceeds -1 dBTP")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, output, rate, subtype="PCM_24")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("v23_candidate", type=Path,
                        help="already-rendered v2.3 candidate from the new performance")
    parser.add_argument("--target", type=Path,
                        help="same-performance original FL Studio REC->MAIN processed target")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.v23_candidate, args.output, args.report, args.target), indent=2))


if __name__ == "__main__":
    main()
