import numpy as np
import pytest
from skell_sound_match.paired_tone import ToneBasis,ToneRecipe

@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_identity_mono_and_causal(rate):
    t=np.arange(rate//8)/rate;x=(.1*np.sin(2*np.pi*440*t)).astype(np.float32);x=np.stack((x,x),1)
    b=ToneBasis(x,rate)
    assert np.array_equal(b.render(ToneRecipe()),x)
    assert np.array_equal(b.render(ToneRecipe(side_db=12)),x)
    r=ToneRecipe(bands_db=(3,-2,4,-5,1,0),compression=.4,expansion=.5,gain_db=3,drive=2)
    y=b.render(r)
    assert np.isfinite(y).all() and np.array_equal(y[:,0],y[:,1])
    assert np.array_equal(y[:len(x)//2],ToneBasis(x[:len(x)//2],rate).render(r))
    assert np.max(abs(y))<=.5

def test_silence_and_stereo():
    x=np.zeros((4096,2),np.float32);r=ToneRecipe(bands_db=(3,3,3,3,3,3),compression=.9,expansion=2,side_db=18,drive=6)
    assert not ToneBasis(x,44100).render(r).any()
    x[:,0]=.1;x[:,1]=-.1;y=ToneBasis(x,44100).render(ToneRecipe(side_db=6))
    assert np.allclose(y,x*10**(.3))
    assert np.all(y.mean(1)==0)

@pytest.mark.parametrize('r',[ToneRecipe(bands_db=(0,)),ToneRecipe(gain_db=float('nan')),ToneRecipe(drive=-1),ToneRecipe(compression=1)])
def test_bad_recipe(r):
    with pytest.raises(ValueError):ToneBasis(np.zeros((4096,2)),44100).render(r)
