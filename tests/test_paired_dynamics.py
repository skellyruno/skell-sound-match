import numpy as np
import pytest
from skell_sound_match.paired_dynamics import Dynamics,render,fit_gate


def test_unity_and_validation():
    x=np.random.default_rng(2).normal(0,.1,(10000,2)).astype('float32')
    assert np.array_equal(render(x,44100,Dynamics()),x)
    with pytest.raises(ValueError):render(x,44100,Dynamics(attack_ms=99))
    with pytest.raises(ValueError):fit_gate(x,x[:-1],44100)


def test_causal_and_stereo_linked():
    x=np.zeros((10000,2),dtype='float32');x[1000:2000]=[.1,.05];x[5000:]=[.01,.005]
    r=Dynamics(expansion=3,threshold_db=-30)
    y=render(x,44100,r);z=x.copy();z[8000:]=.2
    assert np.array_equal(y[:8000],render(z,44100,r)[:8000])
    assert np.allclose(y[:,0],2*y[:,1]);assert np.max(abs(y[6000:]))<.01


def test_rates():
    for sr in (32000,44100,48000,96000,192000):
        x=np.ones((sr//10,1),dtype='float32')*.03
        y=render(x,sr,Dynamics(expansion=2))
        assert y.shape==(len(x),2) and np.isfinite(y).all()
