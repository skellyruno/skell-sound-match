import numpy as np
import pytest
pm=pytest.importorskip("parselmouth")
from skell_sound_match.wav_only import pitch_sync93 as p

def tone(n=44100):
    t=np.arange(n)/44100;u=(.1*np.sin(2*np.pi*200*t)+.04*np.sin(2*np.pi*400*t)).astype('f');return np.column_stack([u,u])
def test_pitch_half():
    x=tone();z=p.pitch_transform(x,44100,.5,1.);assert z.shape==x.shape and np.isfinite(z).all();q=pm.Sound(z.mean(1),44100).to_pitch(pitch_floor=60,pitch_ceiling=350).selected_array['frequency'];assert abs(np.median(q[q>0])-100)<5
def test_silence_and_invalid():
    x=np.zeros((4096,2),'f');assert np.array_equal(p.pitch_transform(x,44100,.5,1),x)
    with pytest.raises(ValueError):p.pitch_transform(x,44100,0,1)
    with pytest.raises(ValueError):p.pitch_transform(x[:,0],44100,.5,1)
def test_repeatable_unvoiced():
    x=tone();x[10000:25000]=np.random.default_rng(93).normal(0,.03,(15000,2));a=p.pitch_transform(x,44100,.5,1.);b=p.pitch_transform(x,44100,.5,1.);np.testing.assert_array_equal(a,b)
