import numpy as np
import pytest
from skell_sound_match.wav_only.stage_parity import compare
SR=32000
@pytest.fixture
def x():
    z=np.zeros((2*SR,2));z[200:-200]=np.random.default_rng(9).normal(0,.05,(len(z)-400,2));return z

def test_exact(x):
    r=compare(x,x,SR);assert r['bit_identical'] and r['near_null_gate'] and r['within_two_pcm24_lsb']
def test_gain_not_hidden(x):
    r=compare(x,x*.8,SR);assert not r['near_null_gate'] and r['gain_corrected_null_db']<-100 and r['aligned_null_db']>-20
def test_declared_latency(x):
    y=np.roll(x,64,axis=0);r=compare(x,y,SR,64);assert r['near_null_gate'] and not r['bit_identical'] and r['raw_null_db']>-5
    assert not compare(x,y,SR)['near_null_gate']
def test_tail_not_hidden(x):
    y=np.roll(x,64,axis=0);y[:64]=.1;assert not compare(x,y,SR,64)['near_null_gate']
def test_channel_flip(x):
    assert not compare(x,x[:,::-1],SR)['near_null_gate']
@pytest.mark.parametrize('kind',['length','silent','nan','lag','channels'])
def test_invalid(x,kind):
    with pytest.raises(ValueError):
        if kind=='length':compare(x,x[:-1],SR)
        elif kind=='silent':compare(x*0,x,SR)
        elif kind=='nan':compare(x,x*np.nan,SR)
        elif kind=='lag':compare(x,x,SR,20000)
        else:compare(x[:,0],x[:,0],SR)
