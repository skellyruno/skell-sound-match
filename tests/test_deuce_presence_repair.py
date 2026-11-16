import numpy as np
import pytest
from skell_sound_match.deuce_presence_repair import coefficients, render

@pytest.mark.parametrize('sr', [44100, 48000, 96000])
@pytest.mark.parametrize('block', [1, 17, 64, 257, 512])
def test_block_reproducibility(sr, block):
    rng = np.random.default_rng(120)
    x = rng.normal(0, 0.06, (2047, 2))
    ref = render(x, sr)
    y = render(x, sr, block_size=block)
    np.testing.assert_allclose(y, ref, atol=3e-14, rtol=0)

@pytest.mark.parametrize('sr', [44100, 48000, 96000])
def test_finite_and_silence(sr):
    assert np.isfinite(coefficients(sr)).all()
    z=render(np.zeros((1024,2)),sr,block_size=64)
    assert np.array_equal(z,np.zeros_like(z))
    impulse=np.zeros((1024,2));impulse[0]=0.1
    y=render(impulse,sr,block_size=64)
    assert np.isfinite(y).all()
    assert np.max(abs(y)) < 1
    assert np.any(y[:4]) # no sample latency

def test_fails_bad_inputs():
    with pytest.raises(ValueError):render(np.array([[float('nan'),0]]),44100)
    with pytest.raises(ValueError):render(np.zeros((10,3)),44100)
    with pytest.raises(ValueError):render(np.zeros((10,2)),8000)
    with pytest.raises(ValueError):render(np.zeros((10,2)),44100,block_size=0)


def test_presence_filter_response_is_stable_and_correctly_centered():
    from scipy.signal import sosfreqz
    from skell_sound_match.deuce_presence_repair import CENTER_HZ, GAIN_DB
    sr = 48000
    w, h = sosfreqz(coefficients(sr), worN=np.array([0.0, CENTER_HZ, sr / 2]), fs=sr)
    response_db = 20 * np.log10(abs(h))
    np.testing.assert_allclose(response_db, [0.0, GAIN_DB, 0.0], atol=1e-9)
    poles = np.roots(coefficients(sr)[0, 3:])
    assert np.max(abs(poles)) < 1.0


def test_mono_and_empty_stream_are_safe():
    silence = np.zeros((0, 1), dtype=np.float64)
    assert render(silence, 48000, block_size=128).shape == (0, 1)
    mono = np.ones((256, 1), dtype=np.float64) * 0.01
    output = render(mono, 48000, block_size=17)
    assert output.shape == mono.shape
    assert np.isfinite(output).all()
