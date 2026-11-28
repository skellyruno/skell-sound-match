import numpy as np
import pytest
from skell_sound_match.wav_only.vocal_retrieval import descriptor,rank,distances

@pytest.fixture
def tone():
    t=np.arange(64000)/32000
    x=.1*np.sin(2*np.pi*220*t)*(.6+.4*np.sin(2*np.pi*3*t))
    return np.column_stack([x,x])

def test_gain_invariance(tone):
    a,b=descriptor(tone,32000),descriptor(tone*.2,32000)
    assert distances(a,[b])[0]<1e-7

def test_antiphase_and_mono(tone):
    a=descriptor(tone,32000); b=descriptor(tone*np.array([1,-1]),32000)
    assert np.isfinite(b[3]).all() and np.min(b[3][:3])>0 and np.max(b[3][3:])<-.99

def test_rank_and_stage(tone):
    a=descriptor(tone,32000);b=descriptor(tone*np.array([1,-1]),32000)
    assert rank(a,[('a',a),('b',b)])[0].key=='a'
    assert rank(a,[('a',a),('b',b)],allowed_keys={'b'})[0].key=='b'
    assert rank(a,[('a',a)],allowed_keys=set())==[]
    with pytest.raises(ValueError):rank(a,[('a',a),('a',b)])

@pytest.mark.parametrize('x,sr',[(np.zeros((32000,2)),32000),(np.ones((100,2)),32000),(np.ones((32000,3)),32000),(np.ones(32000),16000),(np.full(32000,np.nan),32000)])
def test_invalid(x,sr):
    with pytest.raises(ValueError):descriptor(x,sr)

def test_invalid_weights(tone):
    a=descriptor(tone,32000)
    with pytest.raises(ValueError):distances(a,[a],[-1,0,1,0])

from skell_sound_match.wav_only.vocal_retrieval import prototypes,rank_prototypes

def test_multi(tone):
    a=descriptor(tone,32000); b=descriptor(tone*np.array([1,-1]),32000)
    assert len(prototypes(tone,32000))==3
    assert rank_prototypes(a,[('a',[b,a]),('b',[b])])[0].key=='a'
    assert rank_prototypes(a,[('a',[a])],allowed_keys=[])==[]
    with pytest.raises(ValueError):rank_prototypes(a,[('a',[])])

def test_short_half(tone):
    assert len(prototypes(tone[:48000],32000))==1

def test_resampling(tone):
    from scipy.signal import resample_poly
    a=descriptor(tone,32000);b=descriptor(resample_poly(tone,3,2,axis=0),48000)
    assert distances(a,[b])[0]<.05
