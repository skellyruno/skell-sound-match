"""Offline feature-gap comparisons from optional, separately installed fif-ears reports.

No fif-ears code is vendored. Only signal/expression fields are consumed.
Tempo/key benchmarking against Skell Key is DEFERRED per owner direction.
Audio, private reports, learned filters and reference WAVs do not belong in Git.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


class PairingError(ValueError):
    """The supplied reference/candidate pairing is not valid for comparison."""


def _numeric(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PairingError(f"Missing or nonnumeric {label}")
    out = float(value)
    if not math.isfinite(out):
        raise PairingError(f"Nonfinite {label}")
    return out


def _measurements(report: dict) -> dict:
    if report.get("tool", {}).get("name") != "fif-ears":
        raise PairingError("Expected a fif-ears report")
    layers = report.get("layers", {})
    sig = layers.get("signal", {})
    expr = layers.get("expression", {})
    if sig.get("status") != "ok" or expr.get("status") != "ok":
        raise PairingError("Required signal/expression layer unavailable")
    timbre = expr.get("timbre", {}).get("overall", {})
    dyn = expr.get("dynamics", {})
    result = {
        "duration_s": _numeric(sig.get("duration_s"), "duration_s"),
        "sample_rate": _numeric(sig.get("sample_rate"), "sample_rate"),
        "channels": _numeric(sig.get("channels"), "channels"),
        "peak_dbfs": _numeric(sig.get("peak_dbfs"), "peak_dbfs"),
        "rms_dbfs": _numeric(sig.get("rms_dbfs"), "rms_dbfs"),
        "spectral_centroid_hz": _numeric(sig.get("spectral_centroid_hz", {}).get("mean"), "centroid"),
        "stereo_width": _numeric(sig.get("stereo_width"), "stereo_width"),
        "brightness_hz": _numeric(timbre.get("brightness_hz"), "brightness_hz"),
        "warmth": _numeric(timbre.get("warmth"), "warmth"),
        "roughness": _numeric(timbre.get("roughness"), "roughness"),
        "dynamic_range_db": _numeric(dyn.get("dynamic_range_db"), "dynamic_range_db"),
    }
    if result["duration_s"] <= 0 or result["sample_rate"] < 8000 or result["channels"] not in (1, 2):
        raise PairingError("Invalid physical audio description")
    return result


def _width_delta_db(reference: float, candidate: float) -> float | None:
    if reference <= 1e-8 and candidate <= 1e-8:
        return 0.0
    if reference <= 1e-8 or candidate <= 1e-8:
        return None
    return round(20 * math.log10(candidate / reference), 3)


def _contour_error(reference: dict, candidate: dict) -> float | None:
    """Median-level-normalized audible contour MAE; not transient verification."""
    def rows(report):
        contour = report["layers"]["expression"]["dynamics"].get("contour", [])
        return {
            round(_numeric(row["t"], "contour t"), 2):
                _numeric(row["db"], "contour db")
            for row in contour
        }

    ref, cand = rows(reference), rows(candidate)
    audible = sorted(t for t in ref.keys() & cand.keys() if ref[t] > -60)
    if len(audible) < 3:
        return None
    diffs = sorted(cand[t] - ref[t] for t in audible)
    offset = diffs[len(diffs) // 2]
    return round(
        sum(abs(cand[t] - ref[t] - offset) for t in audible) / len(audible), 3
    )


def compare_reports(reference: dict, candidate: dict, *,
                    reference_take: str, candidate_take: str,
                    reference_stage: str, candidate_stage: str,
                    original_is_processed: bool = True) -> dict:
    """Use only caller-verified same take and processed target stage.

    The reports alone cannot verify the evidence or sample accuracy.
    They never determine winning sounds or automatically promote versions.
    """
    if not reference_take or not candidate_take or reference_take != candidate_take:
        raise PairingError("Same-take identity must be explicitly verified")
    if not reference_stage or reference_stage != candidate_stage:
        raise PairingError("Original and candidate must target the same output stage")
    if not original_is_processed:
        raise PairingError("No verified processed original for this target stage")
    r, c = _measurements(reference), _measurements(candidate)
    if (r["sample_rate"] != c["sample_rate"] or r["channels"] != c["channels"] or
            abs(r["duration_s"] - c["duration_s"]) > 0.025):
        raise PairingError("Reports differ in sample rate, channels or duration")
    brightness = c["brightness_hz"] - r["brightness_hz"]
    return {
        "pairing": "verified_by_explicit_intake_metadata_not_automatic_audio_fingerprint",
        "take": reference_take, "stage": reference_stage,
        "candidate_minus_original": {
            "centroid_hz": round(c["spectral_centroid_hz"] - r["spectral_centroid_hz"], 1),
            "brightness_hz": round(brightness, 1),
            "brightness_pct": round(100 * brightness / max(r["brightness_hz"], 1), 2),
            "warmth_share": round(c["warmth"] - r["warmth"], 3),
            "roughness_proxy": round(c["roughness"] - r["roughness"], 3),
            "stereo_width_db": _width_delta_db(r["stereo_width"], c["stereo_width"]),
            "dynamic_range_db": round(c["dynamic_range_db"] - r["dynamic_range_db"], 2),
            "rms_level_db": round(c["rms_dbfs"] - r["rms_dbfs"], 2),
            "peak_dbfs": round(c["peak_dbfs"] - r["peak_dbfs"], 2),
            "rms_contour_mae_db": _contour_error(reference, candidate),
        },
        "limitations": [
            "Global features cannot measure unique delay/chorus modulation or preference",
            "Report summaries cannot validate sample alignment or independent-take transfer",
            "Never automatically eliminate or promote battle candidates from these scores",
        ],
    }


def compare_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "skelly.fif-ears-pair-audit.v1":
        raise PairingError("Unexpected private pairing manifest schema")
    results = []
    for item in data.get("pairs", []):
        def read(key):
            raw = Path(item[key])
            file = raw if raw.is_absolute() else path.parent / raw
            return json.loads(file.read_text(encoding="utf-8"))
        row = compare_reports(
            read("original_report"), read("candidate_report"),
            reference_take=item["reference_take"],
            candidate_take=item["candidate_take"],
            reference_stage=item["reference_stage"],
            candidate_stage=item["candidate_stage"],
            original_is_processed=item.get("reference_verified", False),
        )
        row["group_id"] = item["group_id"]
        row["candidate_id"] = item["candidate_id"]
        results.append(row)
    if not results:
        raise PairingError("No pairings supplied")
    return {
        "schema": "skelly.fif-ears-pair-audit-result.v1",
        "pairs": results,
        "notice": "Private results; public code only. Tempo/key deliberately excluded.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Output exists; refusing overwrite: {args.output}")
    result = compare_manifest(args.manifest)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Verified-report pairings: {len(result['pairs'])}; wrote {args.output}")


if __name__ == "__main__":
    main()
