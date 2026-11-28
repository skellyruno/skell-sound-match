import numpy as np
import pytest
from skell_sound_match.wav_only.phase_diagnostic import fit_allpass,apply_allpass

@pytest.mark.parametrize('sr',[44100,48000])
def test_causal_phase_fit(sr):
    x=np.random.default_rng(58).normal(0,.04,(sr*2,2));target=apply_allpass(x,{'frequency':[950.],'q':[.8],'polarity':-1},sr)
    p=fit_allpass(x[:sr],target[:sr],sr,sections=1);y=apply_allpass(x,p,sr)
    assert np.linalg.norm(y[sr:]-target[sr:])<.2*np.linalg.norm(x[sr:]-target[sr:])
    assert p['polarity']==-1
    assert abs(np.sqrt(np.mean(y[sr:]**2))/np.sqrt(np.mean(x[sr:]**2))-1)<.015

def test_invalid():
    x=np.zeros((8192,2))
    with pytest.raises(ValueError):fit_allpass(x,x)
    with pytest.raises(ValueError):fit_allpass(x,x[:-1])
