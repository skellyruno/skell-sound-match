import numpy as np
import pytest
from skell_sound_match.wav_only.ms_band_repair import fit_ms_gain, replay_ms_gain


def fixture():
    rng = np.random.default_rng(66)
    m = rng.normal(0, .05, 32768).astype('f')
    s = rng.normal(0, .01, 32768).astype('f')
    x = np.column_stack([m+s, m-s])
    t = np.column_stack([1.2*m+.7*s, 1.2*m-.7*s])
    return x, t


@pytest.mark.parametrize('separate', [True, False])
def test_improves_known_gain(separate):
    x, t = fixture()
    g = fit_ms_gain(x[:16384], t[:16384], separate_side=separate)
    y = replay_ms_gain(x[16384:], g)
    assert np.linalg.norm(y-t[16384:]) < .2*np.linalg.norm(x[16384:]-t[16384:])


def test_zero_amount():
    x, t = fixture()
    np.testing.assert_allclose(replay_ms_gain(x, fit_ms_gain(x, t), 0), x, atol=1e-6)


def test_impulse_center_and_channel_shape():
    x = np.zeros((4096, 2), 'f'); x[2048] = [1, 1]
    y = replay_ms_gain(x, np.full((8, 2), 2, 'f'))
    assert y.shape == x.shape and np.argmax(abs(y[:, 0])) == 2048
    np.testing.assert_allclose(y[:, 0], y[:, 1], atol=1e-7)


@pytest.mark.parametrize('bad', [np.zeros((8, 1)), np.full((8, 2), np.nan), np.full((8, 2), 17)])
def test_invalid_gains(bad):
    x, _ = fixture()
    with pytest.raises(ValueError): replay_ms_gain(x, bad)


def test_invalid_training_and_amount():
    x, t = fixture()
    with pytest.raises(ValueError): fit_ms_gain(x, t[:-1])
    with pytest.raises(ValueError): fit_ms_gain(x[:10], t[:10])
    with pytest.raises(ValueError): replay_ms_gain(x, np.zeros((8, 2)), 2)
