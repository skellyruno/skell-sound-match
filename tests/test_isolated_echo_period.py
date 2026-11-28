import numpy as np
import pytest
from skell_sound_match.wav_only.isolated_echo_period import estimate_period

@pytest.mark.parametrize('sr',[44100,48000])
def test_repeated_delay_identification(sr):
    rng=np.random.default_rng(19)
    x=rng.normal(0,.04,(sr*2,1)).repeat(2,axis=1);d=round(.224*sr)
    t=.3*x
    for k in range(1,7):
        t[k*d:]+=.75*.76**(k-1)*x[:-k*d]
    result=estimate_period(x,t,sr)
    assert result['samples']==d
    assert result['error']<.05

def test_silent_and_invalid():
    x=np.zeros((8192,2))
    with pytest.raises(ValueError):estimate_period(x,x)
    with pytest.raises(ValueError):estimate_period(x,x[:-1])
