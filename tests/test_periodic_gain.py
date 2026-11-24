import numpy as np
import pytest
from skell_sound_match.wav_only.periodic_gain import fit_periodic_candidates, render_gain


def test_rate_recovered_and_replay_not_reference_dependent():
    t=np.arange(594)*.01+.005
    y=-8+10*np.sin(2*np.pi*8.675*t)+3*np.cos(2*np.pi*17.35*t)
    m=fit_periodic_candidates(t,y,np.ones(len(t),bool),4.2,limit=1)[0]
    assert abs(m.rate_hz-8.675)<.026
    assert m.validation_mae_db<1
    r=render_gain(t,m)
    assert np.min(r)>=10**(-28/20) and np.max(r)<=10**(12/20)
    np.testing.assert_array_equal(r,render_gain(t,m))


def test_insufficient_active_or_invalid_rates():
    t=np.arange(100)*.01
    with pytest.raises(ValueError):fit_periodic_candidates(t,t,np.zeros(len(t),bool),.5)
    with pytest.raises(ValueError):fit_periodic_candidates(t,t,np.ones(len(t),bool),.5,rates=[0])
