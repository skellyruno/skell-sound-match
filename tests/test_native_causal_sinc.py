import numpy as np
import pytest
from skell_sound_match.wav_only.native_causal_sinc import map_causal_sinc

@pytest.mark.parametrize('rate', [32000, 48000, 96000, 192000])
def test_dc_and_shape(rate):
    h = np.random.default_rng(7).normal(0, .02, (500, 2, 2)).astype('f')
    y = map_causal_sinc(h, 44100, rate, 20)
    np.testing.assert_allclose(y.sum(0), h.sum(0), atol=5e-6)
    assert y.shape[1:] == (2, 2)

@pytest.mark.parametrize('radius', [2, 8, 20, 32])
def test_zero_time_impulse(radius):
    h = np.zeros((64, 2), 'f'); h[0] = [1, -1]
    y = map_causal_sinc(h, 44100, 48000, radius)
    np.testing.assert_allclose(y[0], h[0], atol=1e-7)
    assert np.max(np.abs(y[1:])) < 1e-7

def test_identity_returns_copy():
    x = np.arange(8, dtype='f'); y = map_causal_sinc(x, 44100, 44100)
    np.testing.assert_array_equal(x, y); assert not np.shares_memory(x, y)

@pytest.mark.parametrize('h,sr,tr,r', [([],44100,48000,8), ([float('nan')],44100,48000,8), ([1],True,48000,8), ([1],44100,48000.5,8), ([1],44100,48000,1), ([1],44100,48000,True)])
def test_reject_invalid(h,sr,tr,r):
    with pytest.raises(ValueError): map_causal_sinc(h,sr,tr,r)
