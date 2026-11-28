import numpy as np
import pytest
from skell_sound_match.wav_only.declared_latency import render_compensated


def test_known_latency_preserves_last_sample_and_stereo():
    x=np.arange(200,dtype=np.float32).reshape(-1,2)/200
    y=render_compensated(x,lambda z:np.pad(z,((44,0),(0,0)))[:len(z)],44)
    assert np.array_equal(x,y)
    assert not np.shares_memory(x,y)


def test_zero_latency():
    x=np.ones((4,2),np.float32)
    assert np.array_equal(render_compensated(x,lambda z:z*2,0),x*2)


@pytest.mark.parametrize('lag',[-1,192001,0.5,True])
def test_invalid_delay(lag):
    with pytest.raises(ValueError):render_compensated(np.zeros((2,2)),lambda x:x,lag)


@pytest.mark.parametrize('x',[np.zeros((4,1)),np.zeros((0,2)),np.full((4,2),np.nan)])
def test_invalid_audio(x):
    with pytest.raises(ValueError):render_compensated(x,lambda z:z,0)


def test_invalid_output():
    with pytest.raises(ValueError):render_compensated(np.zeros((4,2)),lambda z:z[:-1],44)
