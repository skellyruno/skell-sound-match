import numpy as np
import pytest
from skell_sound_match.broad_dsp import Basis,Recipe
@pytest.mark.parametrize('sr',[44100,48000,96000,192000])
def test_causal(sr):
 x=np.random.default_rng(22).normal(0,.08,(8192,2)).astype(np.float32)
 assert np.array_equal(Basis(x,sr).render(Recipe()),x)
 for r in [Recipe(low=3,mid=-2,high=4,compression=.4),Recipe(echo=.4,delay_ms=20,motion=.25,side=-3,drive=2,gain=1)]:
  y=Basis(x,sr).render(r);z=Basis(x[:4096],sr).render(r);assert np.array_equal(y[:4096],z);assert np.isfinite(y).all()
  assert not Basis(x*0,sr).render(r).any()
 mono=np.column_stack((x[:,0],x[:,0]));z=Basis(mono,sr).render(Recipe(low=4,compression=.4,side=12));assert np.array_equal(z[:,0],z[:,1])
@pytest.mark.parametrize('r',[Recipe(low=10),Recipe(compression=-1),Recipe(echo=1),Recipe(delay_ms=0),Recipe(gain=float('nan')),Recipe(motion_hz=0)])
def test_invalid(r):
 with pytest.raises(ValueError):Basis(np.ones((100,2)),44100).render(r)
def test_echo():
 x=np.zeros((8192,2),np.float32);x[0,0]=1;y=Basis(x,44100).render(Recipe(echo=.4,delay_ms=20));assert y[882,1]==np.float32(.4);assert np.count_nonzero(y)==4
