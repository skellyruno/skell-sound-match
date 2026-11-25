"""Local-only audio intake for source/reference/candidate recording lineage.

Never infer take IDs or verified stages from filenames or similarity scores.
The caller must supply a trusted export manifest before pair_provenance passes.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

import soundfile as sf
from .audio_alignment import alignment_diagnostic
from .chain_evidence import PairProvenance, check_pair_provenance
from .reference_guard import split_activity


def _inspect(path: Path) -> tuple[dict[str, Any], Any, int]:
    if not path.is_file():
        raise FileNotFoundError(path)
    data, rate = sf.read(path, always_2d=True, dtype="float64")
    return ({"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "rate": rate, "channels": data.shape[1], "frames": len(data),
             "seconds": len(data) / rate}, data, rate)


def audit_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(source, dict) or not isinstance(source.get("pairs"), list):
        raise ValueError("manifest needs a 'pairs' array")
    out = []
    for i, entry in enumerate(source["pairs"]):
        if not isinstance(entry, dict) or not all(k in entry for k in ("source", "reference")):
            raise ValueError(f"pair {i} missing source or reference")
        tracks: dict[str, dict[str, Any]] = {}
        signals = {}
        for key in ("source", "reference", "candidate"):
            if entry.get(key) is None:
                continue
            path = (manifest_path.parent / entry[key]).resolve()
            tracks[key], signals[key], _ = _inspect(path)
        rates = {v["rate"] for v in tracks.values()}
        channels = {v["channels"] for v in tracks.values()}
        compatible = len(rates) == 1 and len(channels) == 1 and next(iter(channels)) in (1, 2)
        warnings: list[str] = []
        if not compatible:
            warnings.append("sample rate or channel count mismatch")
        for key, v in tracks.items():
            expected = entry.get(f"{key}_expected_sha256")
            if expected is None or expected != v["sha256"]:
                warnings.append(f"{key} export checksum missing or mismatched")
        aligns: dict[str, Any] = {}
        if compatible:
            for key in ("reference", "candidate"):
                if key in signals:
                    try:
                        aligns[f"source_vs_{key}"] = asdict(alignment_diagnostic(
                            signals["source"], signals[key], next(iter(rates))))
                    except ValueError as exc:
                        warnings.append(f"{key} acoustic diagnostic unavailable: {exc}")
        activity: dict[str, Any] = {}
        for key, value in signals.items():
            try:
                activity[key] = split_activity(value, tracks[key]["rate"], int(len(value)*.6))
            except ValueError as exc:
                activity[key] = {"eligible": False, "reason": str(exc)}
        pair = None
        if compatible and "candidate" in tracks:
            pair = PairProvenance(
                source_take_id=entry.get("source_take_id", ""),
                reference_take_id=entry.get("reference_take_id", ""),
                candidate_take_id=entry.get("candidate_take_id", ""),
                source_sha256=tracks["source"]["sha256"],
                reference_sha256=tracks["reference"]["sha256"],
                candidate_sha256=tracks["candidate"]["sha256"],
                source_rate=tracks["source"]["rate"],
                reference_rate=tracks["reference"]["rate"],
                candidate_rate=tracks["candidate"]["rate"],
                reference_stage=entry.get("reference_stage", ""),
                candidate_stage=entry.get("candidate_stage", ""),
                source_offset_samples=entry.get("source_offset_samples", -1),
                reference_offset_samples=entry.get("reference_offset_samples", -1),
                candidate_offset_samples=entry.get("candidate_offset_samples", -1),
                offsets_verified=entry.get("offsets_verified", False),
                evidence_origin=entry.get("evidence_origin", "unverified"),
            )
        blockers=list(check_pair_provenance(pair))
        if entry.get("source_take_id") and entry.get("reference_take_id") and entry["source_take_id"] != entry["reference_take_id"]:
            blockers.append("source/reference are different documented performances")
        blockers.extend(warnings)
        if any(not value.get("eligible", False) for value in activity.values()):
            blockers.append("inactive audio partition")
        out.append({"target": entry.get("target", f"pair_{i}"), "tracks": tracks,
                    "alignment_diagnostic_only": aligns, "activity": activity,
                    "pair_provenance_gate_passed": len(blockers) == 0,
                    "eligible_for_preset_promotion": False,  # Requires independent holdout, peak and owner approval.
                    "blockers": list(dict.fromkeys(blockers))})
    return {"version": 1, "semantics": "acoustic similarity never establishes take identity; intake cannot approve a preset",
            "pairs": out}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit local source/reference/candidate lineage")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_manifest(args.manifest)
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
