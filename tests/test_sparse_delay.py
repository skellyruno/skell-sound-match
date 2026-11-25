import numpy as np
import pytest
from skell_sound_match.sparse_delay import fit,shifted,SparseDelay


def test_audio_only_echo_transfer():
    rng=np.random.default_rng(3);x=(.06*rng.normal(size=(50000,2))).astype('float32');k=6000
    y=.8*x+.35*shifted(x[:,::-1],k)
    r=fit(x[:30000],y[:30000],44100,max_taps=2)
    assert k in r.lags
    out=r.render(x,44100);assert np.sqrt(np.mean((out[30000:]-y[30000:])**2))<1e-5
    z=(.06*rng.normal(size=(50000,2))).astype('float32');assert np.max(abs(r.render(z,44100)-(.8*z+.35*shifted(z[:,::-1],k))))<1e-5


def test_bad_pair():
    x=np.zeros((4096,2),np.float32)
    with pytest.raises(ValueError):fit(x,x,44100)
    with pytest.raises(ValueError):fit(x,x[:-1],44100)
    with pytest.raises(ValueError):SparseDelay(44100,(0,1),((1.,1.),)).render(x,44100)
