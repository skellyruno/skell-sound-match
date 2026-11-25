import numpy as np
import pytest
from skell_sound_match.diffuse_room import room_basis,mix_room
@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_room(rate):
    x=np.zeros((rate//4,2));x[0]=.5
    a=room_basis(x,rate,.3,6500,.015)
    assert np.isfinite(a).all() and np.max(abs(a[:round(.015*rate)]))<1e-12
    assert np.array_equal(a,room_basis(x,rate,.3,6500,.015))
    assert np.array_equal(mix_room(x,a,0,1),x)
    mono=mix_room(x,a,.2,0);assert np.array_equal(mono[:,0],mono[:,1])
    assert np.max(abs(a[:,0]-a[:,1]))>1e-4
    assert np.allclose(a[:len(x)//2],room_basis(x[:len(x)//2],rate,.3,6500,.015),atol=1e-12)
def test_invalid():
    x=np.zeros((100,2))
    with pytest.raises(ValueError):room_basis(x,44100,0,6500,0)
    with pytest.raises(ValueError):room_basis(x,44100,.3,float('nan'),0)
    with pytest.raises(ValueError):mix_room(x,x,2,1)
