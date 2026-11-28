import numpy as np
import pytest
from skell_sound_match.wav_only.stage_prefix import supervised_prefix


def test_exact_prefix_and_owned_target():
    x = np.arange(40).reshape(20, 2)
    t = x * 2
    y = supervised_prefix(x[:15], x, t, 10, 12)
    np.testing.assert_array_equal(y, t[:10])
    y[:] = 0
    assert t[1, 0] == 4


@pytest.mark.parametrize('stop,evaluation', [(13, 12), (0, 12), (True, 12), (8, 21)])
def test_boundaries(stop, evaluation):
    x = np.ones((20, 2))
    with pytest.raises(ValueError):
        supervised_prefix(x, x, x, stop, evaluation)


def test_source_mismatch():
    x = np.ones((20, 2)); y = x.copy(); y[3, 0] = 2
    with pytest.raises(ValueError):
        supervised_prefix(x, y, x, 10, 12)


def test_nonfinite_prefix():
    x = np.ones((20, 2)); y = x.copy(); y[3, 0] = np.nan
    with pytest.raises(ValueError):
        supervised_prefix(x, x, y, 10, 12)


def test_short_stage():
    x = np.ones((20, 2))
    with pytest.raises(ValueError):
        supervised_prefix(x, x[:8], x[:8], 10, 12)
