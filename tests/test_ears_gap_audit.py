import copy
import json
import pytest
from skell_sound_match.wav_only.ears_gap_audit import (
    PairingError, compare_manifest, compare_reports,
)


def fake_report(*, bright=2000, width=0.3, duration=10, channel=2):
    return {
        "tool": {"name": "fif-ears"},
        "layers": {
            "signal": {
                "status": "ok", "duration_s": duration, "sample_rate": 44100,
                "channels": channel, "peak_dbfs": -2, "rms_dbfs": -18,
                "spectral_centroid_hz": {"mean": bright}, "stereo_width": width,
            },
            "expression": {
                "status": "ok",
                "timbre": {"overall": {"brightness_hz": bright,
                                      "warmth": .3, "roughness": .2}},
                "dynamics": {
                    "dynamic_range_db": 12, "contour": [
                        {"t": 0, "db": -30}, {"t": .1, "db": -25},
                        {"t": .2, "db": -26}, {"t": .3, "db": -29},
                    ],
                },
            },
        },
    }


def compare(ref, cand, **kwargs):
    return compare_reports(ref, cand, reference_take="same", candidate_take="same",
                           reference_stage="full_effects",
                           candidate_stage="full_effects", **kwargs)


def test_identity_has_zero_feature_gap():
    a = fake_report()
    d = compare(a, copy.deepcopy(a))["candidate_minus_original"]
    assert all(value == 0 for value in d.values() if value is not None)


def test_differences_in_brightness_width_dynamics():
    a, b = fake_report(), fake_report(bright=1600, width=.6)
    b["layers"]["expression"]["dynamics"]["dynamic_range_db"] = 14
    d = compare(a, b)["candidate_minus_original"]
    assert d["brightness_pct"] == -20
    assert d["stereo_width_db"] == pytest.approx(6.021, abs=.001)
    assert d["dynamic_range_db"] == 2


def test_contour_ignores_constant_level_offset():
    a, b = fake_report(), fake_report()
    for row in b["layers"]["expression"]["dynamics"]["contour"]:
        row["db"] += 4
    assert compare(a, b)["candidate_minus_original"]["rms_contour_mae_db"] == 0


def test_refuse_mismatched_take_stage_or_unverified_original():
    a = fake_report()
    with pytest.raises(PairingError, match="Same-take"):
        compare_reports(a, a, reference_take="one", candidate_take="two",
                        reference_stage="main", candidate_stage="main")
    with pytest.raises(PairingError, match="same output stage"):
        compare_reports(a, a, reference_take="one", candidate_take="one",
                        reference_stage="main", candidate_stage="full")
    with pytest.raises(PairingError, match="verified processed"):
        compare(a, a, original_is_processed=False)


def test_refuse_bad_audio_or_incomplete_reports():
    a, b = fake_report(), fake_report(duration=9.5)
    with pytest.raises(PairingError):
        compare(a, b)
    b = fake_report()
    b["layers"]["expression"]["status"] = "not_installed"
    with pytest.raises(PairingError):
        compare(a, b)
    b = fake_report()
    b["layers"]["signal"]["peak_dbfs"] = float("nan")
    with pytest.raises(PairingError):
        compare(a, b)


def test_zero_stereo_ratios_are_not_infinite():
    a = fake_report(width=0)
    assert compare(a, fake_report(width=0))["candidate_minus_original"]["stereo_width_db"] == 0
    assert compare(a, fake_report(width=.5))["candidate_minus_original"]["stereo_width_db"] is None


def test_private_manifest_is_provenance_gated(tmp_path):
    folder = tmp_path / "reports"
    folder.mkdir()
    (folder / "original.json").write_text(json.dumps(fake_report()))
    (folder / "candidate.json").write_text(json.dumps(fake_report()))
    base = {
        "group_id": "vocal", "candidate_id": "trial",
        "original_report": "reports/original.json",
        "candidate_report": "reports/candidate.json",
        "reference_take": "take1", "candidate_take": "take1",
        "reference_stage": "full_effects",
        "candidate_stage": "full_effects",
        "reference_verified": True,
    }
    manifest = tmp_path / "private.json"
    manifest.write_text(json.dumps({"schema": "skelly.fif-ears-pair-audit.v1",
                                    "pairs": [base]}))
    assert compare_manifest(manifest)["pairs"][0]["candidate_id"] == "trial"
    assert "Tempo/key" in compare_manifest(manifest)["notice"]
    base["candidate_take"] = "unrelated"
    manifest.write_text(json.dumps({"schema": "skelly.fif-ears-pair-audit.v1",
                                    "pairs": [base]}))
    with pytest.raises(PairingError):
        compare_manifest(manifest)
