import numpy as np
import pytest
from skell_sound_match.wav_only.structural_echo import stereo_echo_recurrence, diagnostic_spectrum


def test_pingpong_lags_and_sign():
    rng=np.random.default_rng(76); x=rng.normal(size=12000);y=np.zeros((len(x),2));y[1234:,1]=.3*x[:-1234];y[2468:,0]=-.2*x[:-2468]
    a,b=stereo_echo_recurrence(x,y,200,3000)
    assert a[0]==2468 and a[1]<-.8 and b[0]==1234 and b[1]>.9


def test_silent():
    assert stereo_echo_recurrence(np.zeros(100),np.zeros((100,2)),1,50)==[None,None]


@pytest.mark.parametrize('bounds',[(0,20),(20,10),(1,100),(True,10)])
def test_invalid_bounds(bounds):
    with pytest.raises(ValueError):stereo_echo_recurrence(np.ones(100),np.ones((100,2)),*bounds)


def test_diagnostic_polarity_invariance_and_gain():
    rng=np.random.default_rng(76);x=rng.normal(size=(8192,2))*.1
    assert max(diagnostic_spectrum(x,x,44100).values())==0
    assert max(diagnostic_spectrum(-x,x,44100).values())==0
    r=diagnostic_spectrum(x*.5,x,44100)
    assert 5.7<r['active_envelope_error_db']<6.1
    assert r['weighted_logmag_1024_db']>4


def test_bad_diagnostic_shape():
    with pytest.raises(ValueError):diagnostic_spectrum(np.ones((2048,1)),np.ones((2048,1)),44100)
