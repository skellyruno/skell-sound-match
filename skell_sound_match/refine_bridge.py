"""Conservative local bridge to a user-provided VocalMatch refinement script.

Never bundles recordings, calls network services, overwrites an approved source
or automatically promotes a candidate. Offline use only, not real-time DSP.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy import signal


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_pair(previous: Path, reference: Path):
    a, sr = sf.read(previous, always_2d=True, dtype="float64")
    b, br = sf.read(reference, always_2d=True, dtype="float64")
    if (sr != br or a.shape != b.shape or a.shape[1] not in (1, 2)
            or len(a) < sr * 9 or not np.isfinite(a).all() or not np.isfinite(b).all()):
        raise ValueError("Expected aligned, finite, same-length mono/dual-mono recordings >=9 seconds")
    for x in (a, b):
        if x.shape[1] == 2:
            mid = x.mean(axis=1)
            if np.sqrt(np.mean(np.square(x[:, 0] - x[:, 1]))) > .06 * max(np.sqrt(np.mean(mid * mid)), 1e-10):
                raise ValueError("Stereo ambience present; this research backend handles mono/dual-mono only")
    return sr, a.shape


def evaluate_report(report: dict) -> bool:
    metrics = report["metrics"]
    before, after = metrics["previous"], metrics["refined_out_of_fold"]
    for key in ("validation", "late"):
        if after[key]["spectral_error_9band_db"] > before[key]["spectral_error_9band_db"] + 0.05:
            return False
        for window in ("20ms", "200ms"):
            if after[key]["envelope_error_db"][window] > before[key]["envelope_error_db"][window] + 0.05:
                return False
    return report.get("gate", {}).get("passed") is True


def check_candidate(path: Path, sr: int, shape: tuple) -> float:
    x, candidate_sr = sf.read(path, always_2d=True, dtype="float64")
    if candidate_sr != sr or x.shape != shape or not np.isfinite(x).all():
        raise ValueError("Experimental render has invalid sample rate, shape, or samples")
    tp = float(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0))))
    dbtp = 20 * np.log10(max(tp, 1e-12))
    if dbtp > -0.99:
        raise ValueError(f"Experimental render exceeds -1 dBTP safety bound: {dbtp:.3f} dBTP")
    return float(dbtp)


def run(script: Path, previous: Path, reference: Path, out_dir: Path, profile="safe") -> dict:
    if profile not in ("safe", "max"):
        raise ValueError("profile must be safe or max")
    script, previous, reference, out_dir = [Path(x).resolve() for x in (script, previous, reference, out_dir)]
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite {out_dir}")
    if not script.is_file() or not previous.is_file() or not reference.is_file():
        raise FileNotFoundError("Trusted script and both audio inputs must exist locally")
    sr, shape = validate_pair(previous, reference)
    checksums = {str(p): digest(p) for p in (previous, reference)}
    cmd = [sys.executable, str(script), "cv", "--previous", str(previous),
           "--reference", str(reference), "--out-dir", str(out_dir), "--profile", profile]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=360, check=False)
    if result.returncode:
        raise RuntimeError(f"Refinement failed with exit {result.returncode}: {result.stderr[-500:]}")
    for path, expected in checksums.items():
        if digest(Path(path)) != expected:
            raise RuntimeError("An original recording was modified by the external script")
    report_file = out_dir / f"cv_{profile}.json"
    audio_file = out_dir / f"refined_{profile}_out_of_fold.wav"
    report = json.loads(report_file.read_text(encoding="utf-8"))
    tp = check_candidate(audio_file, sr, shape)
    passed = evaluate_report(report)
    summary = {
        "profile": profile, "out_of_fold": True,
        "research_gate_passed": passed,
        "candidate_true_peak_dbtp_estimate": round(tp, 3),
        "original_sha256": checksums,
        "audio_file": str(audio_file), "report_file": str(report_file),
        "approval_status": "AUDITION ONLY - never auto-promote",
    }
    (out_dir / "bridge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description="Verify a locally supplied VocalMatch refinement against an approved candidate")
    p.add_argument("--script", type=Path, required=True, help="Trusted local vocalmatch_refine.py")
    p.add_argument("--previous", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--profile", choices=("safe", "max"), default="safe")
    a = p.parse_args(argv)
    print(json.dumps(run(a.script, a.previous, a.reference, a.out_dir, a.profile), indent=2))


if __name__ == "__main__":
    main()
