"""Verify the complete checked-out public research archive without modifying it."""
import json
from pathlib import Path
from scripts.materialize_archive import materialize

def test_actual_checked_out_archive_is_complete():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "archive/manifest.json").read_text(encoding="utf-8"))
    result = materialize(root, manifest)
    assert len(result) >= 64
    names = {r["path"] for r in result}
    for expected in (
        "data/deuce/audio/dry.flac",
        "data/deuce/audio/full_combined.flac",
        "data/deuce/listening_comparisons/D_15s.flac",
        "data/deuce/presets/rec.fst",
        "data/alchemist/audio/main_effects.flac",
        "data/alchemist/presets/MAIN.fst",
    ):
        assert expected in names
