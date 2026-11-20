"""Offline, evidence-backed quality report for reference-audio candidates.

No audio leaves the local machine. A report is not listening approval or proof
that a proprietary effect has been reproduced. No candidate is auto-promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal


WINDOWS = {"training": (0.8, 5.7), "validation": (6.1, 10.4), "test": (10.8, 14.4)}
EPS = 1e-12


def _read(path: str | Path) -> tuple[np.ndarray, int]:
    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    if not (16000 <= sr <= 192000) or x.shape[1] not in (1, 2) or len(x) < sr:
        raise ValueError("Unsupported audio: require >=1 s mono/stereo, 16–192 kHz")
    if not np.isfinite(x).all():
        raise ValueError("Input contains nonfinite samples")
    return x, sr


def _sha(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _db(val: float) -> float:
    return float(20 * np.log10(max(val, EPS)))


def _env_db(x: np.ndarray, sr: int, ms: float) -> np.ndarray:
    n = max(1, round(sr * ms / 1000))
    count = len(x) // n
    if count < 3:
        raise ValueError("Window too short for envelope analysis")
    frames = x[:count * n].reshape(count, n, x.shape[1])
    return 20 * np.log10(np.maximum(np.sqrt(np.mean(frames**2, axis=(1, 2))), EPS))


def _spectral(reference: np.ndarray, candidate: np.ndarray, sr: int) -> float:
    values = []
    for nfft in (512, 2048, 8192):
        if len(reference) < nfft * 2:
            continue
        _, _, rr = signal.stft(reference.mean(axis=1), fs=sr, nperseg=nfft, noverlap=nfft // 2,
                               boundary=None)
        _, _, cc = signal.stft(candidate.mean(axis=1), fs=sr, nperseg=nfft, noverlap=nfft // 2,
                               boundary=None)
        magr, magc = abs(rr), abs(cc)
        # Skip both-near-silent bins; do not hide candidate-only sibilance/noise.
        activity = np.maximum(magr, magc) > max(float(magr.max()), float(magc.max())) * 1e-4
        if np.any(activity):
            values.append(float(np.mean(np.abs(20*np.log10(np.maximum(magr[activity], 1e-9))
                                                  - 20*np.log10(np.maximum(magc[activity], 1e-9))))))
    return float(np.mean(values)) if values else 0.0


def _true_peak(x: np.ndarray) -> float:
    # Only an approximate 4x interpolated peak, not a certified BS.1770 meter.
    return _db(max(float(np.max(abs(signal.resample_poly(x[:, ch], 4, 1))))
                   for ch in range(x.shape[1])))


def _lufs(x: np.ndarray, sr: int) -> float | None:
    try:
        import pyloudnorm as pyln
    except ImportError:
        return None
    v = float(pyln.Meter(sr).integrated_loudness(x if x.shape[1] > 1 else x[:, 0]))
    return v if np.isfinite(v) else None


def measure(reference: np.ndarray, candidate: np.ndarray, sr: int) -> dict:
    if reference.shape != candidate.shape or reference.ndim != 2 or reference.shape[1] not in (1, 2):
        raise ValueError("Clips must have matching samples and channel layout")
    if not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise ValueError("Nonfinite input")
    r, c = reference.mean(axis=1), candidate.mean(axis=1)
    corr = float(np.corrcoef(r, c)[0, 1]) if np.std(r) > EPS and np.std(c) > EPS else 0.0
    ref_env20 = _env_db(reference, sr, 20)
    mask = ref_env20 >= max(ref_env20) - 35.0
    errs = {}
    for ms in (5, 20, 200):
        er, ec = _env_db(reference, sr, ms), _env_db(candidate, sr, ms)
        maskms = er >= max(er) - 35.0
        errs[f"envelope_{ms}ms_mae_db"] = float(np.mean(np.abs(er[maskms] - ec[maskms])))
    ref_rms, cand_rms = np.sqrt(np.mean(reference**2)), np.sqrt(np.mean(candidate**2))
    peak_ref, peak_cand = _db(np.max(np.abs(reference))), _db(np.max(np.abs(candidate)))
    return {
        "waveform_correlation_signed": corr,
        "null_residual_db": _db(float(np.sqrt(np.mean((reference-candidate)**2)))/max(ref_rms, EPS)),
        "multires_spectral_mae_db": _spectral(reference, candidate, sr),
        **errs,
        "reference_rms_dbfs": _db(ref_rms), "candidate_rms_dbfs": _db(cand_rms),
        "reference_sample_peak_dbfs": peak_ref,
        "candidate_sample_peak_dbfs": peak_cand,
        "candidate_true_peak_dbtp_4x_estimate": _true_peak(candidate),
        "reference_crest_db": peak_ref - _db(ref_rms),
        "candidate_crest_db": peak_cand - _db(cand_rms),
    }


def evaluate(reference: np.ndarray, champion: np.ndarray, candidate: np.ndarray,
             sr: int, *, windows: dict = WINDOWS, max_loudness_delta: float = 0.2,
             true_peak_ceiling: float = -1.0) -> dict:
    if (reference.shape != champion.shape or reference.shape != candidate.shape
            or reference.ndim != 2 or not np.isfinite(reference).all()
            or not np.isfinite(champion).all() or not np.isfinite(candidate).all()):
        raise ValueError("All clips must be aligned, finite, and have identical shapes")
    if not windows or not set(("training", "validation", "test")).issubset(windows):
        raise ValueError("Training/validation/test windows required")
    ordered = [windows[k] for k in ("training", "validation", "test")]
    if not (all(0 <= a < b <= len(reference)/sr for a, b in ordered)
            and ordered[0][1] + .2 <= ordered[1][0]
            and ordered[1][1] + .2 <= ordered[2][0]):
        raise ValueError("Chronological nonoverlapping windows with >=200 ms gaps required")
    for q in (max_loudness_delta, true_peak_ceiling):
        if not np.isfinite(q):
            raise ValueError("Invalid threshold")
    if max_loudness_delta < 0 or true_peak_ceiling > 0:
        raise ValueError("Unsafe threshold")

    # Full-file sample-level and LUFS checks are independent of any quality ranking.
    reference_lufs, champ_lufs, cand_lufs = (_lufs(v, sr) for v in (reference, champion, candidate))
    peak = _true_peak(candidate)
    if reference_lufs is None or champ_lufs is None or cand_lufs is None:
        diff = abs(_db(np.sqrt(np.mean(candidate**2))) - _db(np.sqrt(np.mean(reference**2))))
        loudness_method = "RMS FALLBACK: pyloudnorm unavailable; LUFS not measured"
    else:
        diff = abs(cand_lufs - reference_lufs)
        loudness_method = "LUFS"
    blocked = []
    if peak > true_peak_ceiling + 1e-5:
        blocked.append("candidate exceeds the configured 4x true-peak ceiling")
    if diff > max_loudness_delta:
        blocked.append("candidate and reference are not loudness-matched for a fair audition")
    outcome = {}
    for name, (a, b) in windows.items():
        s = slice(round(a*sr), round(b*sr))
        outcome[name] = {
            "champion": measure(reference[s], champion[s], sr),
            "candidate": measure(reference[s], candidate[s], sr),
        }
        old, new = outcome[name]["champion"], outcome[name]["candidate"]
        outcome[name]["delta_candidate_minus_champion"] = {
            "null_residual_db": new["null_residual_db"] - old["null_residual_db"],
            "spectral_error_db": new["multires_spectral_mae_db"] - old["multires_spectral_mae_db"],
            "envelope20_error_db": new["envelope_20ms_mae_db"] - old["envelope_20ms_mae_db"],
            "crest_error_db": abs(new["candidate_crest_db"] - new["reference_crest_db"])
                              - abs(old["candidate_crest_db"] - old["reference_crest_db"]),
        }
    holdouts = [outcome[z]["delta_candidate_minus_champion"] for z in ("validation", "test")]
    improvements = [k for k in holdouts[0] if all(t[k] < -0.01 for t in holdouts)]
    regressions = [k for k in holdouts[0] if any(t[k] > 0.25 for t in holdouts)]
    if blocked:
        status = "unsafe_or_unfair_audition"
    elif improvements and regressions:
        status = "audition_candidate_with_tradeoffs_no_auto_promotion"
    elif improvements:
        status = "audition_candidate_no_auto_promotion"
    else:
        status = "mixed_or_insufficient_improvement"
    return {
        "status": status,
        "audition_blockers": blocked,
        "improved_on_both_holdout_sections": improvements,
        "regressed_on_any_holdout_over_0_25db": regressions,
        "audio": {"sr": sr, "samples": len(reference), "channels": reference.shape[1],
                  "reference_lufs": reference_lufs, "champion_lufs": champ_lufs,
                  "candidate_lufs": cand_lufs, "candidate_true_peak_dbtp_4x_estimate": peak,
                  "reference_vs_candidate_loudness_diff_db": diff, "loudness_method": loudness_method},
        "windows": outcome,
        "limitations": ["Chronological holdout sections of the SAME take, not a new performance.",
                        "Holdouts reused during iterative development are not truly blind.",
                        "A numeric pass is never automatic listening approval or release approval.",
                        "A 4x true-peak estimate is not a certified true-peak measurement."],
    }


def cli(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Skell Sound Match champion-vs-candidate quality gate")
    parser.add_argument("reference")
    parser.add_argument("champion")
    parser.add_argument("candidate")
    parser.add_argument("--out", required=True, help="JSON report path; will not overwrite")
    parser.add_argument("--true-peak-ceiling", type=float, default=-1.0)
    parser.add_argument("--training", nargs=2, type=float, default=list(WINDOWS["training"]))
    parser.add_argument("--validation", nargs=2, type=float, default=list(WINDOWS["validation"]))
    parser.add_argument("--test", nargs=2, type=float, default=list(WINDOWS["test"]))
    args = parser.parse_args(argv)
    paths = (args.reference, args.champion, args.candidate)
    audios = [_read(path) for path in paths]
    rates = [sr for _, sr in audios]
    if len(set(rates)) != 1:
        raise ValueError("Sample rates differ; align/resample explicitly")
    report = evaluate(*(a for a, _ in audios), sr=rates[0],
                      windows={"training": tuple(args.training),
                               "validation": tuple(args.validation),
                               "test": tuple(args.test)},
                      true_peak_ceiling=args.true_peak_ceiling)
    report["input_sha256"] = {role: _sha(path) for role, path in zip(("reference", "champion", "candidate"), paths)}
    report["paths_recorded"] = False  # avoid exposing private file names in reports
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "report": str(dest),
                      "audition_blockers": report["audition_blockers"]}, indent=2))


if __name__ == "__main__":
    cli()