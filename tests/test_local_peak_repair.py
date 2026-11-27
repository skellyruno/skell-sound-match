import numpy as np
import pytest
from skell_sound_match.wav_only.local_peak_repair import repair_peak, estimated_peak

def test_safe_unchanged():
    x=np.random.default_rng(1).normal(0,.03,(1000,2)).astype('f')
    y=repair_peak(x);np.testing.assert_array_equal(y,x);assert not np.shares_memory(y,x)

def test_localized_linked_peak():
    x=np.full((4096,2),.05,'f');x[2048]=[1.4,.7]
    y=repair_peak(x);assert estimated_peak(y)<=10**(-1.2/20)+1e-6
    np.testing.assert_array_equal(y[:1800],x[:1800]);np.testing.assert_array_equal(y[2300:],x[2300:]);assert np.isclose(y[2048,0],2*y[2048,1])

def test_interpolated_overshoot():
    i=np.arange(4000);v=(.98*np.sin(2*np.pi*.39*i+.4)).astype('f');x=np.column_stack((v,v*.5));y=repair_peak(x);assert estimated_peak(y)<=10**(-1.2/20)+1e-6

@pytest.mark.parametrize('x,cap,passes',[(np.zeros((1,1)),-1.2,3),(np.full((2,2),np.nan),-1.2,3),(np.zeros((2,2)),1,3),(np.zeros((2,2)),-1.2,0)])
def test_invalid(x,cap,passes):
    with pytest.raises(ValueError):repair_peak(x,cap,passes)
