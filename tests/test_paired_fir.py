import numpy as np
import pytest
from skell_sound_match.paired_fir import compress_source, fit_kernel, render_kernel

@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_identity_causality(rate):
    x=np.random.default_rng(0).normal(0,.07,8192)
    v=np.column_stack([x,x]); assert np.array_equal(compress_source(v,rate),x)
    z=compress_source(v,rate,.5);assert np.max(abs(z))<=np.max(abs(x))
    assert np.array_equal(z[:4096],compress_source(v[:4096],rate,.5))
    h=np.zeros((16,2));h[4]=[.7,.3];h[7]=[.2,-.1]
    y=render_kernel(z,h);f=fit_kernel(z,y,16,.0001)
    assert np.max(abs(f-h))<.002
    assert np.allclose(y[:4096],render_kernel(z[:4096],h),atol=1e-12)
    assert np.max(abs(render_kernel(np.zeros(100),f)))==0

def test_invalid():
    x=np.ones(8192);y=np.column_stack([x,x]);
    with pytest.raises(ValueError):fit_kernel(x,y,4097,.1)
    with pytest.raises(ValueError):fit_kernel(x*0,y,16,.1)
    with pytest.raises(ValueError):fit_kernel(x,y,16,float('nan'))
    with pytest.raises(ValueError):compress_source(np.column_stack([x,-x]),44100)
    with pytest.raises(ValueError):render_kernel(x,np.ones((128,2)))
