import numpy as np
import pytest
from skell_sound_match.brightness import brightness_shelf

@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_shelf(rate):
    t=np.arange(rate//4)/rate
    x=np.stack([.1*np.sin(2*np.pi*100*t),.1*np.sin(2*np.pi*10000*t)],1).astype(np.float32)
    assert np.array_equal(brightness_shelf(x,rate,4500,0),x)
    y=brightness_shelf(x,rate,4500,6)
    assert np.array_equal(y[:8192],brightness_shelf(x[:8192],rate,4500,6))
    assert np.isfinite(y).all()
    gain=20*np.log10(np.sqrt(np.mean(y[2048:]**2,axis=0)/np.mean(x[2048:]**2,axis=0)))
    assert abs(gain[0])<.1 and gain[1]>2
    z=np.ones((4096,2),np.float32)*.1
    assert np.allclose(brightness_shelf(z,rate,4500,6)[-1],.1,atol=1e-7)
    assert np.array_equal(brightness_shelf(z,rate,4500,6)[:,0],brightness_shelf(z,rate,4500,6)[:,1])
    assert not brightness_shelf(z*0,rate,4500,6).any()

@pytest.mark.parametrize('rate,hz,db',[(0,4500,6),(44100,0,6),(44100,20000,6),(44100,4500,float('nan')),(44100,4500,30)])
def test_invalid(rate,hz,db):
    with pytest.raises(ValueError):brightness_shelf(np.ones((100,2)),rate,hz,db)
