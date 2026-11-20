import numpy as np
import pytest
import soundfile as sf

from skell_sound_match.deuce_presence_repair import render
from skell_sound_match.deuce_transfer_audit import evaluate, run


def source(sr=44100, n=44100, amplitude=0.015):
    rng = np.random.default_rng(8)
    t = np.arange(n) / sr
    mono = (amplitude * np.sin(2 * np.pi * 190 * t)
            + 0.007 * np.sin(2 * np.pi * 6900 * t)
            + 0.002 * rng.standard_normal(n))
    return mono[:, None]


def test_full_audit_uses_same_performance_target_for_scoring_only():
    x = source()
    target = render(x, 44100)
    y, report = evaluate(x, 44100, target)
    assert y.shape == x.shape
    assert report["claim"] == "Same-performance, frozen-parameter matching audit"
    assert report["has_original_rec_main_target"]
    assert report["render_chunk_consistency_max_error"] == 0
    assert report["band_metrics"]["4500_7900_hz"]["v25"]["mean_absolute_db"] < 0.0001
    assert report["band_metrics"]["9000_14000_hz"]["v25"]["mean_absolute_db"] < 0.0001


def test_safety_only_never_reports_reference_accuracy():
    y, report = evaluate(source(), 44100)
    assert report["claim"] == "Safety audit only"
    assert "band_metrics" not in report
    assert report["finite"]
    assert y.shape == source().shape


def test_mismatched_target_shape_is_rejected():
    with pytest.raises(ValueError):
        evaluate(source(), 44100, source(n=45000))


def test_run_refuses_overwrite_and_input_output_collision(tmp_path):
    input_file = tmp_path / "input.wav"
    output_file = tmp_path / "output.wav"
    report_file = tmp_path / "report.json"
    sf.write(input_file, source(), 44100, subtype="PCM_24")
    report = run(input_file, output_file, report_file)
    assert report["has_original_rec_main_target"] is False
    assert output_file.exists() and report_file.exists()
    with pytest.raises(FileExistsError):
        run(input_file, output_file, report_file)
    with pytest.raises(ValueError):
        run(input_file, input_file, tmp_path / "another.json")


def test_target_sample_rate_mismatch_is_rejected(tmp_path):
    candidate = tmp_path / "candidate.wav"
    target = tmp_path / "target.wav"
    sf.write(candidate, source(sr=44100), 44100, subtype="PCM_24")
    sf.write(target, source(sr=48000), 48000, subtype="PCM_24")
    with pytest.raises(ValueError, match="sample rate mismatch"):
        run(candidate, tmp_path / "out.wav", tmp_path / "report.json", target)
