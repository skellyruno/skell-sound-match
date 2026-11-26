import numpy as np
import pytest
from skell_sound_match.wav_only.stage_replay import replay_echo
from skell_sound_match.wav_only.declared_latency import render_compensated

def test_flush_tail():
    x=np.zeros((50,2),'f');x[4]=.25;x[-1]=.8
    def delayed(z):return np.pad(z,((7,0),(0,0)))[:len(z)]
    assert np.array_equal(render_compensated(x,delayed,7),x)

def test_delay_zero():
    x=np.ones((10,2),'f')*.1;assert np.array_equal(render_compensated(x,lambda z:z,0),x)

def test_stereo_echo():
    x=np.zeros((100,2),'f');x[2]=.4;w=np.zeros((1,6,2),'f');w[0,0]=[.5,-.5];y=replay_echo(x,delays=[10],weights=w,direct_gain=1)
    assert np.array_equal(y[:12],x[:12]);assert np.allclose(y[12],[.2,-.2]);assert not np.any(y[13:])

@pytest.mark.parametrize('delays', [[-1],[132301],[2,1],[1,1],[]])
def test_reject_delay(delays):
    with pytest.raises(ValueError):replay_echo(np.zeros((100,2),'f'),delays=delays,weights=np.zeros((len(delays),6,2)),direct_gain=1)

def test_invalid_latency():
    with pytest.raises(ValueError):render_compensated(np.zeros((20,2)),lambda x:x, -1)
    with pytest.raises(ValueError):render_compensated(np.zeros((20,2)),lambda x:x[:-1], 5)
