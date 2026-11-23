"""Private, repeatable batch intake for verified source/reference audio pairs.

The manifest and results contain private paths, hashes and source-derived knobs;
NEVER commit them to public Git. Duplicate runs are content-addressed and skipped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .vocal_knob_search import Window, run_files

SCHEMA = "skelly.vocal-knob-batch.v1"
ENGINE_REVISION = "knob-optimizer-v3-shared-envelope-floor"


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while data := f.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()


def process_batch(manifest_path: Path, private_output: Path) -> dict:
    manifest_path = Path(manifest_path).resolve()
    private_output = Path(private_output).resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA or not isinstance(payload.get("pairs"), list):
        raise ValueError("Expected skelly.vocal-knob-batch.v1 pairs")
    pairs = payload["pairs"]
    if len(pairs) < 1 or len(pairs) > 250:
        raise ValueError("Batch must contain 1–250 pairs")
    # The output must not overlap sources and must never be a public repo.
    if any(part in {".git", "skell-sound-match", "skell_sound_match"}
           for part in private_output.parts):
        raise ValueError("Choose a private output folder outside the source repository")
    private_output.mkdir(parents=True, exist_ok=True)
    seen = set()
    result = {"schema": "skelly.vocal-knob-batch-results.v1",
              "engine_revision": ENGINE_REVISION, "processed": [], "cached": [], "blocked": []}
    for item in pairs:
        name = item.get("id")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", name):
            raise ValueError("Pair IDs must be safe, short identifiers")
        if name in seen:
            raise ValueError("Duplicate pair ID")
        seen.add(name)
        try:
            s = (manifest_path.parent / item["source"]).resolve()
            t = (manifest_path.parent / item["reference"]).resolve()
            if s == t:
                raise ValueError("Source and reference are identical")
            if not s.is_file() or not t.is_file():
                raise FileNotFoundError("Source/reference not found")
            pairing = {"same_take": item.get("same_take"),
                       "take_id": item["take_id"], "source_stage": item["source_stage"],
                       "target_stage": item["target_stage"]}
            train = Window(*item["train"])
            holdout = Window(*item["holdout"])
            opts = {"effects": bool(item.get("effects", False)),
                    "fif_signal": bool(item.get("fif_signal", False)),
                    "budget": int(item.get("budget", 55)), "seed": int(item.get("seed", 17))}
            inputs = {"source_sha256": _file_hash(s), "reference_sha256": _file_hash(t),
                      "pairing": pairing, "train": vars(train), "holdout": vars(holdout),
                      "options": opts, "engine_revision": ENGINE_REVISION}
            digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
            out = private_output / f"{name}__{digest}"
            report = out / "trial_report.json"
            if report.is_file():
                prior = json.loads(report.read_text(encoding="utf-8"))
                render_name = prior.get("render_name", "")
                if not render_name or Path(render_name).name != render_name:
                    raise ValueError("Invalid cached render name")
                render_path = out / render_name
                if prior.get("source_sha256") == inputs["source_sha256"] and \
                        prior.get("reference_sha256") == inputs["reference_sha256"] and \
                        render_path.is_file() and \
                        prior.get("render_sha256") == _file_hash(render_path):
                    result["cached"].append({"id": name, "path": str(report),
                                             "status": prior.get("status")})
                    continue
                raise ValueError("Stale or incomplete cached result; refusing overwrite")
            if out.exists() and any(out.iterdir()):
                raise ValueError("Output folder exists without complete report")
            trial = run_files(s, t, out, pairing=pairing, train=train, holdout=holdout,
                              **opts)
            result["processed"].append({"id": name, "path": str(report),
                                         "status": trial["status"],
                                         "listening_eligible": trial["listening_eligible"]})
        except (ValueError, OSError, KeyError, TypeError, ImportError, RuntimeError) as exc:
            result["blocked"].append({"id": name, "error": f"{type(exc).__name__}: {exc}"})
    # A batch index is private because it contains file paths and evaluation IDs.
    (private_output / "latest_batch_index.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="Run verified offline Sound Match knob batches")
    p.add_argument("manifest", type=Path)
    p.add_argument("private_output", type=Path)
    args = p.parse_args()
    result = process_batch(args.manifest, args.private_output)
    print(json.dumps({k: len(v) if isinstance(v,list) else v
                      for k,v in result.items()}, indent=2))


if __name__ == "__main__":
    main()
