import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.core import Audio, compare, gain_audio, load_wav, optimize_gain, split_audio


def sample(sr=16000, seconds=3):
    t = np.arange(sr * seconds, dtype=float) / sr
    # Synthetic harmonic vocal-like signal with time-varying amplitude.
    x = .08 * (1 + .5 * np.sin(2 * np.pi * .7 * t)) * (np.sin(2 * np.pi * 180 * t) + .3 * np.sin(2 * np.pi * 540 * t))
    return Audio(x[:, None], sr)


def test_identity_metrics():
    x = sample()
    m = compare(x, x)
    assert m['waveform_correlation_signed'] > .999999
    assert m['20ms_active_error_db'] < 1e-8
    assert m['multires_log_spectral_error_db'] == 0
    assert m['candidate_true_peak_dbfs_4x_estimate'] <= 0


def test_gainfit_heldout_improves():
    dry = sample()
    target = gain_audio(dry, 4)
    a, b = split_audio(dry), split_audio(target)
    g = optimize_gain(a['training'], b['training'])
    before = compare(b['test'], a['test'])
    after = compare(b['test'], gain_audio(a['test'], g))
    assert abs(g - 4) < .04
    assert after['20ms_active_error_db'] < before['20ms_active_error_db'] / 20


def test_mismatch_rejected():
    a = sample()
    with pytest.raises(ValueError, match='Sample rates'):
        compare(a, Audio(a.samples, 22050))
    with pytest.raises(ValueError, match='Channel counts'):
        compare(a, Audio(np.column_stack([a.samples, a.samples]), a.rate))
    with pytest.raises(ValueError, match='Sample counts'):
        compare(a, Audio(a.samples[:-10], a.rate))


def test_no_leakage_and_invalid_parameters():
    a = sample()
    w = split_audio(a)
    assert all(len(v.samples) > 0 for v in w.values())
    with pytest.raises(ValueError, match='Overlapping'):
        split_audio(a, training=(0,.7))
    with pytest.raises(ValueError):
        gain_audio(a, np.nan)
    with pytest.raises(ValueError, match='Unsafe ceiling'):
        optimize_gain(a, a, ceiling_dbtp=2)


def test_file_roundtrip(tmp_path):
    a = sample()
    path = tmp_path / 'synthetic.wav'
    sf.write(path, a.samples, a.rate, subtype='PCM_24')
    b = load_wav(path)
    assert b.rate == a.rate and b.samples.shape == a.samples.shape
    assert np.max(np.abs(b.samples - a.samples)) < 2e-7


def test_signed_polarity_matters():
    a = sample()
    reverse = Audio(-a.samples, a.rate)
    assert compare(a, reverse)['waveform_correlation_signed'] < -.999


def test_nonfinite_rejected(tmp_path):
    a = sample()
    bad = np.copy(a.samples)
    bad[0,0] = np.nan
    with pytest.raises(ValueError):
        compare(a, Audio(bad, a.rate))
