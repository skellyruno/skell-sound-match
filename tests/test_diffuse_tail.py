import numpy as np
import pytest
from skell_sound_match.wav_only.diffuse_tail import render


def test_tail_is_causal_stereo_and_deterministic():
    sr=32000
    x=np.zeros((sr,2));x[100]=1
    y=render(x,sr,.2,.25,side_emphasis=True)
    np.testing.assert_allclose(y[:740],x[:740],atol=1e-12)
    assert np.max(abs(y[740:]))>0
    assert not np.array_equal(y[:,0],y[:,1])
    np.testing.assert_array_equal(render(x,sr,.2,.25,side_emphasis=True),y)
    np.testing.assert_allclose(render(x[:2000],sr,.2,.25,side_emphasis=True),y[:2000],atol=1e-12)
    np.testing.assert_array_equal(render(x,sr,wet_gain=0),x)
    with pytest.raises(ValueError):render(x,sr,decay_s=float('nan'))
