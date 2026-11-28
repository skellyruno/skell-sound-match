import numpy as np
import pytest
from skell_sound_match.reference_guard import split_activity, training_trim, linked_guard,peak_db

@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_activity_and_guard(rate):
    t=np.arange(rate)/rate
    x=np.stack((.3*np.sin(2*np.pi*173*t),.2*np.cos(2*np.pi*173*t)),1)
    assert split_activity(x,rate,len(x)//2)['eligible']
    z=x.copy();z[len(z)//2:]*=1e-5
    assert not split_activity(z,rate,len(z)//2)['eligible']
    z=x*8;y,d=linked_guard(z,rate)
    assert np.isfinite(y).all() and np.max(abs(y))<=10**(-2.5/20)+1e-12
    assert np.allclose(y[:,0]*z[:,1],y[:,1]*z[:,0],atol=1e-12)
    assert np.array_equal(linked_guard(x,rate)[0],x)
    assert np.array_equal(linked_guard(z[:8192],rate)[0],y[:8192])
    assert d.max()>0
    assert peak_db(y,rate)<0


def test_training_and_invalid():
    assert training_trim([-9,-4])==0
    assert training_trim([1,2])==-4.5
    with pytest.raises(ValueError):training_trim([np.nan])
    with pytest.raises(ValueError):linked_guard(np.zeros((8,2)),44100,1)
    with pytest.raises(ValueError):split_activity(np.zeros((8,2)),44100,4)
