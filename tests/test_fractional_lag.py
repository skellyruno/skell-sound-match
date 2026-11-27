import numpy as np
import pytest
from skell_sound_match.wav_only.fractional_lag import estimate_lag


@pytest.mark.parametrize('lag', [-8, -3, 0, 3, 8])
def test_signed_integer_delay(lag):
    x = np.random.default_rng(72).normal(size=1048).astype('f')
    t = x[12-lag:12-lag+1024]
    measured, corr = estimate_lag(x, t, 12)
    assert abs(measured-lag) < .03
    assert corr > .999


def test_fractional_delay():
    k = np.arange(1048, dtype=float)
    f = lambda v: np.sin(.13*v) + .6*np.sin(.27*v+.2) + .2*np.sin(.43*v)
    x = f(k).astype('f')
    t = f(np.arange(1024)+12-2.4).astype('f')
    lag, corr = estimate_lag(x,t,12)
    assert abs(lag-2.4) < .08 and corr > .99


def test_silence():
    assert estimate_lag(np.zeros(20),np.zeros(12),4) == (0.0,0.0)


@pytest.mark.parametrize('x,t,r', [(np.zeros(20),np.zeros(12),True),
    (np.zeros(20),np.zeros(12),0), (np.zeros(20),np.zeros(11),4),
    (np.full(20,np.nan),np.zeros(12),4), (np.zeros((20,1)),np.zeros(12),4)])
def test_invalid(x,t,r):
    with pytest.raises(ValueError):
        estimate_lag(x,t,r)
