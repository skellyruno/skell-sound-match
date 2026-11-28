import numpy as np
import pytest
from skell_sound_match.conditioned_main import labels,conditional,compare,fit
from skell_sound_match.reference_transfer import profile,Recipe


def audio(sr=44100):
    t=np.arange(2*sr)/sr
    x=.1*np.sin(2*np.pi*170*t);x[sr:]=np.random.default_rng(3).normal(0,.04,sr)
    return np.column_stack([x,x]).astype('float32')


def test_groups():
    x=audio();m=labels(x,44100);assert (m[:18]==1).mean()>.9 and (m[-18:]==0).mean()>.9
    g,c=conditional(x,44100,m);assert set(g)=={0,1}
    assert compare(x,44100,profile(x,44100),g,m)['main_score']==0


def test_gain_invariance_rates():
    for sr in (32000,44100,48000,96000,192000):
        x=audio(sr);m=labels(x,sr);g,_=conditional(x,sr,m);assert np.array_equal(m,labels(.5*x,sr));assert compare(.5*x,sr,profile(x,sr),g,m)['main_score']<1e-4


def test_invalid():
    x=audio()
    with pytest.raises(ValueError):conditional(x,44100,np.zeros(2))
    with pytest.raises(ValueError):fit([(x,44100)],x,44100)


def test_unity():
    x=audio();r,info=fit([(x,44100),(x*.7,44100)],x,44100)
    assert r.echo==r.room==r.stereo==0
    assert info['reference_groups']==2
    assert all(v['main_score']<1e-4 for v in info['after'])
