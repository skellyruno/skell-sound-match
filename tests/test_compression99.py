import numpy as np
import pytest
from skell_sound_match.wav_only import cross_take_features98 as c
from skell_sound_match.wav_only import compression99 as s

def fixture():
    t=np.arange(4*c.SR)/c.SR
    v=(.06*np.sin(2*np.pi*180*t)+.035*np.sin(2*np.pi*540*t))*(.5+.48*np.sin(2*np.pi*1.7*t))
    return np.column_stack([v,v]).astype('f')

def test_envelope_ballistics():
    u=np.r_[np.zeros(20),np.ones(20),np.zeros(20)]
    a=s.smooth_env(u,3,150);b=s.smooth_env(u,35,45)
    assert a[20]>b[20] and a[45]>b[45]
    assert np.all((a>=0)&(a<=1))

def test_active_split_excludes_silence():
    x=fixture();p=c.power(c.spec(np.pad(x,((0,len(x)),(0,0)))))
    sl=s.split(p)
    assert sl[1].stop<len(p)*.5 and sl[0].stop<sl[1].start<sl[2].start
    with pytest.raises(ValueError):s.split(np.zeros((500,2,8)))

def test_identity_gain():
    p=c.power(c.spec(fixture()))
    m=dict(attack=3,release=80,threshold=-35,ratio=1,parallel=1,ride_amt=0,knots=[-50,-10],ride=[0,0])
    np.testing.assert_array_equal(s.comp_gain(p,m),np.zeros(len(p)))

def test_compressor_limits():
    p=c.power(c.spec(fixture()))
    m=dict(attack=3,release=65,ratio=4,parallel=.8,ride_amt=0,threshold=-35,knots=[-80,0],ride=[0,0])
    g=s.comp_gain(p,m)
    assert g.min()<0 and g.max()<=1e-6 and g.min()>=-18
