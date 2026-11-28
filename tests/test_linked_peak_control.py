import numpy as np
import pytest
from skell_sound_match.wav_only.linked_peak_control import render


def test_linked_peak_control_preserves_channel_ratio_and_causality():
    x = np.array([[.01, -.02], [1., -.5], [.2, .1]])
    y = render(x)
    np.testing.assert_array_equal(y[0], x[0])
    assert y[1, 0] < x[1, 0]
    np.testing.assert_allclose(y[:, 0] * x[:, 1], y[:, 1] * x[:, 0])
    np.testing.assert_array_equal(render(x[:2]), y[:2])
    np.testing.assert_array_equal(render(x, ratio=1), x)
    with pytest.raises(ValueError):
        render(x, ratio=float('nan'))
