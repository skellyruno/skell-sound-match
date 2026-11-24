import numpy as np
import pytest
from skell_sound_match.wav_only.wet_routing import filtered_echo, diffuse_reverb


def test_echo_causal_cross_and_offset():
    sr = 8000
    x = np.zeros((8000, 2)); x[0, 0] = 1
    y = filtered_echo(x, sr, 100, .5, True, 3000, 10)
    assert np.count_nonzero(y[:880]) == 0
    assert np.max(abs(y[880:1600, 1])) > .01
    assert np.max(abs(y[1600:2400, 0])) > .01
    assert np.isfinite(y).all()


def test_diffuse_reverb_deterministic_predelay_and_silence():
    x = np.zeros((8000, 2)); x[0] = 1
    y = diffuse_reverb(x, 8000, .6, .04, 3000)
    assert np.max(abs(y[:320])) < 1e-12
    assert np.max(abs(y[320:])) > .01
    np.testing.assert_array_equal(y, diffuse_reverb(x, 8000, .6, .04, 3000))
    np.testing.assert_array_equal(diffuse_reverb(x*0, 8000, .6, .04, 3000), x*0)


def test_invalid_input():
    x = np.zeros((800, 2))
    with pytest.raises(ValueError): filtered_echo(x, 8000, 100, 1, False, 3000)
    with pytest.raises(ValueError): diffuse_reverb(x, 8000, .6, .4, 3000)
    with pytest.raises(ValueError): filtered_echo(x[:, 0], 8000, 100, .5, False, 3000)
