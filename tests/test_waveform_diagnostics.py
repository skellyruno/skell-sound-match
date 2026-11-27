import numpy as np
import pytest
from skell_sound_match.wav_only.waveform_diagnostics import compare_waveforms


def test_polarity_is_not_magnitude_error():
    x = np.random.default_rng(61).normal(0, .03, (8192, 2))
    d = compare_waveforms(-x, x)
    assert d['signed_waveform_correlation'] == pytest.approx(-1)
    assert d['least_squares_gain'] == pytest.approx(-1)
    assert d['gain_fit_relative_residual'] < 1e-12
    assert max(d['active_stft_magnitude_error_db'].values()) < 1e-12


def test_output_gain_preserves_shape_but_not_level():
    x = np.random.default_rng(62).normal(0, .04, (8192, 2))
    gain = 10**(-1.6/20)
    d = compare_waveforms(x*gain, x)
    assert d['signed_waveform_correlation'] == pytest.approx(1)
    assert d['least_squares_gain'] == pytest.approx(gain)
    assert d['gain_fit_relative_residual'] < 1e-12
    assert all(1.4 < v < 1.6 for v in d['active_stft_magnitude_error_db'].values())


def test_invalid():
    x = np.zeros((4096, 2))
    with pytest.raises(ValueError): compare_waveforms(x, x)
    with pytest.raises(ValueError): compare_waveforms(x, x[:-1])
