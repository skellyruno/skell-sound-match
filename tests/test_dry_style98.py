import numpy as np
import pytest
from skell_sound_match.wav_only import cross_take_features98 as c, dry_style98 as d

def audio():
    t=np.arange(44100*2)/44100
    v=(.1*np.sin(2*np.pi*160*t)+.04*np.sin(2*np.pi*480*t))*(.6+.35*np.sin(2*np.pi*2*t))
    return np.column_stack([v,v]).astype('f')
def test_stft_roundtrip():
    x=audio();np.testing.assert_allclose(c.synth(c.spec(x),len(x)),x,atol=1e-6)
def test_identity_direct_fit():
    p=c.power(c.spec(audio()));m=d.fit_direct(p,p)
    np.testing.assert_allclose(m['ride'],0,atol=1e-7);np.testing.assert_allclose(m['eq'],0,atol=1e-7)
def test_spatial_determinism():
    x=audio();a,b=d.space(x,1);u,v=d.space(x,1)
    np.testing.assert_array_equal(a,u);np.testing.assert_array_equal(b,v);assert np.std(a[:,0]-a[:,1])>0
def test_zero_mix():
    x=audio();np.testing.assert_array_equal(d.mix(x,0,0,0),x)
def test_recipe_replay_and_stress():
    x=audio();p=c.power(c.spec(x));m=d.fit_direct(p,p);m.update(tone=1.,dyn=1.,lufs=-16.,preset=1,early=.15,tail=.2,g=np.zeros(8),amount=0.)
    a=d.replay(x,m);b=d.replay(x,m);np.testing.assert_array_equal(a,b);assert a.shape==x.shape
    assert d.peak(a)<=-1.24 and d.peak(d.replay(x*10**.3,m))<=-1.24
def test_invalid_input():
    with pytest.raises(ValueError):d.replay(np.zeros((20,2),'f'),{})
    with pytest.raises(ValueError):d.normalize(np.zeros((44100,2),'f'),-16)
