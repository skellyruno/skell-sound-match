import numpy as np
import pytest
from skell_sound_match.wav_only.tail_identification import measure_tail_lags

@pytest.mark.parametrize('sr',[44100,48000])
def test_detects_delayed_return(sr):
    rng=np.random.default_rng(41)
    x=np.zeros((sr*3,2))
    for k in [0.1,.42,.89,1.5,1.88]:
        p=int(k*sr); n=int(.04*sr)
        x[p:p+n]=rng.normal(0,.08,n)[:,None]
    d=int(sr*.27); t=x.copy();t[d:]+=.6*x[:-d]
    lags=measure_tail_lags(x,t,sr)
    assert any(abs(l-.27)<.015 for l,_,_ in lags),lags
    assert all(.045<=l<=1.81 and np.isfinite(c) for l,c,_ in lags)

def test_silence_and_invalid():
    x=np.zeros((44100,2))
    assert measure_tail_lags(x,x)==[]
    with pytest.raises(ValueError):measure_tail_lags(x,x[:-1])
    x[0,0]=np.nan
    with pytest.raises(ValueError):measure_tail_lags(x,x)
