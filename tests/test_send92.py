import numpy as np
import pytest
from skell_sound_match.wav_only.send92 import activity,make_terms

def test_activity_bounded_and_prefix():
    x=np.random.default_rng(92).normal(0,.1,(8192,2)).astype('f');a=activity(x,.2,65.)
    assert a.shape==(len(x),) and np.isfinite(a).all() and np.all((a>=0)&(a<=1))
    np.testing.assert_array_equal(a[:4096],activity(x[:4096],.2,65.))

def test_silence_and_decay():
    x=np.zeros((44100,2),'f');assert not activity(x,.1,65.).any();x[:4410]=.2
    a=activity(x,.1,65.);assert a[4409]>.9 and a[-1]<.01

def test_partition():
    x=np.random.default_rng(3).normal(0,.1,(4096,2)).astype('f');y=x*.8;d=x*.5
    u=make_terms(x,y,d,.1,65.,0);np.testing.assert_allclose(u[1]+u[2],y,atol=1e-7)
    a=make_terms(x,y,d,.1,65.,1);b=make_terms(x,y,d,.1,65.,2)
    np.testing.assert_allclose(a[1],y-d,atol=1e-7);np.testing.assert_allclose(a[2]+b[2],a[1],atol=1e-7);np.testing.assert_allclose(a[3]+b[3],d,atol=1e-7)

def test_bad_params():
    x=np.zeros((16,2),'f')
    for scale,release in [(0,1),(.1,0),(np.nan,1)]:
        with pytest.raises(ValueError):activity(x,scale,release)
    with pytest.raises(ValueError):make_terms(x,x,x,.1,65.,4)
