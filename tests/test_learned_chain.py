import numpy as np
import pytest
from skell_sound_match.wav_only.learned_chain import features,fit_kernel,render


def sample():return np.random.default_rng(3).normal(0,.1,(24000,2)).astype('f')


def test_identity():
    x=sample();assert np.array_equal(x,render(x,kind='identity',scale=.1,lead=0,kernel=None))


def test_exact_fixed_kernel():
    x=sample();k=np.zeros((129,2,2),'f');k[128,0]=[1,1];k[128,1]=[1,-1];y=render(x,kind='linear',scale=.1,lead=128,kernel=k);assert np.max(abs(x-y))<2e-7


def test_known_gain_fit():
    x=sample();t=x*.6;k,s=fit_kernel(x,t,kind='linear',nfft=2048,lead=128,taps=512,regularization=.003);y=render(x,kind='linear',scale=s,lead=128,kernel=k);assert np.sqrt(np.mean((y-t)**2))<.001


def test_dynamic_replay():
    x=sample();t=np.tanh(x*2)*.4;k,s=fit_kernel(x,t,kind='dynamic',nfft=2048,lead=128,taps=512,regularization=.025);y=render(x,kind='dynamic',scale=s,lead=128,kernel=k);assert np.array_equal(y,render(x,kind='dynamic',scale=s,lead=128,kernel=k))


def test_echo_causal():
    x=np.zeros((1000,2),'f');x[10]=.2;y=render(x,kind='identity',scale=.1,lead=0,kernel=None,spatial_features=[('echo',100,2300)],spatial_weights=[[.4,-.4]]);assert np.all(y[:10]==0) and np.allclose(y[10],x[10]) and np.max(abs(y[110:]))>0


@pytest.mark.parametrize('x',[np.zeros((5,1)),np.zeros((0,2)),np.full((2,2),np.nan)])
def test_bad_input(x):
    with pytest.raises(ValueError):features(x,.1,'linear')


@pytest.mark.parametrize('kw',[dict(kind='unknown'),dict(scale=0),dict(lead=-1),dict(kernel=np.zeros((10,3,2))),dict(spatial_features=[('echo',-1,2300)],spatial_weights=[[.4,.4]]),dict(spatial_features=[('room',1,0)],spatial_weights=[[2,2]])])
def test_bad_recipe(kw):
    a=dict(kind='linear',scale=.1,lead=0,kernel=np.zeros((10,2,2),'f'));a.update(kw)
    with pytest.raises(ValueError):render(sample(),**a)
