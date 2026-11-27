import numpy as np
import pytest
from skell_sound_match.wav_only.native_causal_rate import map_causal_kernel


def test_identity_rate_copy():
    h = np.array([1, 2, 3], dtype=np.float32)
    y = map_causal_kernel(h, 44100, 44100)
    np.testing.assert_array_equal(h, y)
    assert not np.shares_memory(h, y)


def test_zero_delay_stereo_identity():
    h = np.array([[[1, 1], [1, -1]]], dtype=np.float32)
    y = map_causal_kernel(h, 44100, 48000)
    np.testing.assert_array_equal(y[0], h[0])
    assert not np.any(y[1:])


@pytest.mark.parametrize('target_rate', [32000, 48000, 96000, 192000])
def test_dc_preserved(target_rate):
    h = np.random.default_rng(8).normal(0, .1, (819, 2, 2)).astype(np.float32)
    y = map_causal_kernel(h, 44100, target_rate)
    np.testing.assert_allclose(y.sum(0), h.sum(0), atol=1e-5)


def test_impulse_time_and_causality():
    h = np.zeros(100, np.float32); h[55] = 1
    y = map_causal_kernel(h, 44100, 48000)
    assert not np.any(y[:59])
    np.testing.assert_allclose(np.dot(np.arange(len(y)), y), 55*48000/44100, atol=1e-5)


@pytest.mark.parametrize('h,sr,tr', [([],44100,48000),([float('nan')],44100,48000),([1],0,48000),([1],44100,48000.5),([1],True,48000)])
def test_invalid_input(h,sr,tr):
    with pytest.raises(ValueError): map_causal_kernel(h,sr,tr)
