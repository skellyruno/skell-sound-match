import json
from dataclasses import asdict, replace
import numpy as np
import pytest
from skell_sound_match.reference_transfer import Recipe,profile,distance,render,fit


def sound(seed=1):
    rng=np.random.default_rng(seed); t=np.arange(32768)/44100
    return (.1*(np.sin(2*np.pi*240*t)+.3*rng.normal(size=len(t))))[:,None].astype('float32')


def test_unity_and_mono():
    x=sound(); y=render(x,44100,Recipe()); assert np.array_equal(y,np.repeat(x,2,axis=1))


def test_profile_no_alignment():
    x=sound(); f=x.reshape(-1,2048,1); y=f[::-1].reshape(x.shape)
    assert distance(profile(x,44100),profile(y,44100))['score']<1e-6


def test_serialized_recipe_transfer():
    x=sound(); r=Recipe(presence=-6,stereo=.35,echo=.2,room=.1,compression=.5)
    y=render(x,44100,r); q=Recipe(**json.loads(json.dumps(asdict(r))))
    assert np.array_equal(y,render(x,44100,q)) and np.isfinite(y).all()
    assert not np.array_equal(y,render(sound(2),44100,q))


@pytest.mark.parametrize('r',[replace(Recipe(),echo=1.1),replace(Recipe(),air=float('nan')),replace(Recipe(),schema='invalid')])
def test_bad_recipe(r):
    with pytest.raises(ValueError): render(sound(),44100,r)


def test_silent_nonfinite():
    with pytest.raises(ValueError): profile(np.zeros((32768,2)),44100)
    x=sound(); x[0]=np.nan
    with pytest.raises(ValueError): profile(x,44100)


def test_fit_different_performance():
    x=sound(); ref=render(sound(2),44100,Recipe(air=-12,presence=-6,stereo=.35))
    r,info=fit(x,44100,ref,44100); assert info['fit']['score']<info['baseline']['score']
    y=render(sound(3),44100,r); assert np.isfinite(y).all()


@pytest.mark.parametrize('rate',[32000,48000,96000,192000])
def test_multirate(rate):
    t=np.arange(rate)//1/rate;x=(.1*np.sin(2*np.pi*320*t))[:,None].astype('float32')
    assert np.array_equal(render(x,rate,Recipe()),np.repeat(x,2,axis=1))
    assert np.isfinite(render(x,rate,Recipe(stereo=.3,room=.15))).all()


def test_two_training_sources():
    a=sound();b=sound(2);ref=render(sound(3),44100,Recipe(air=-12,stereo=.35))
    r,info=fit(a,44100,ref,44100,[(b,44100)])
    assert info['training_sources']==2 and info['fit']['score']<info['baseline']['score']
    assert np.isfinite(render(sound(4),44100,r)).all()
