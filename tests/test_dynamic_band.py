import numpy as np
import pytest
from skell_sound_match.wav_only.dynamic_band import fit,replay

def x():return np.random.default_rng(9).normal(0,.1,(16000,2)).astype('f')

def recipe():return fit(x(),x()*.6,edges=[250,1600,6000],regularization=.08)

def test_gain_and_identity():
    z=x();r=recipe();assert np.array_equal(replay(z,r,0),z);y=replay(z,r,1);assert np.mean((y[4410:]-z[4410:]*.6)**2)<np.mean((z[4410:]*.4)**2)*.15

def test_prefix():
    z=x();r=recipe();a=replay(z,r,.75);b=replay(z[:8000],r,.75);assert np.array_equal(a[:8000],b)

@pytest.mark.parametrize('edges',[[0,100],[200,100],[100,100],[19000]])
def test_bad_edges(edges):
    with pytest.raises(ValueError):fit(x(),x(),edges=edges,regularization=.08)

def test_bad_recipe():
    r=recipe();r['weights'][0][0]=float('nan')
    with pytest.raises(ValueError):replay(x(),r,1)

def test_wrong_input():
    with pytest.raises(ValueError):replay(x()[:,0],recipe(),1)
