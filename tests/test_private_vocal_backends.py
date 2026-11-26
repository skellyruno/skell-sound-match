import numpy as np
import pytest
from skell_sound_match.wav_only.private_vocal_backends import PrivateVocalStudy

def test_explicit_trust(tmp_path):
    with pytest.raises(ValueError):PrivateVocalStudy(tmp_path,{})
def test_missing_library(tmp_path):
    s=PrivateVocalStudy(tmp_path,{},trusted_local_build=True)
    with pytest.raises(ValueError):s.render('rverb',np.zeros((100,2)),44100,dict(decay_s=1,predelay_ms=0))
@pytest.mark.parametrize('audio',[np.zeros((100,1)),np.full((100,2),np.nan),np.full((100,2),10)])
def test_invalid_audio(tmp_path,audio):
    s=PrivateVocalStudy(tmp_path,{},trusted_local_build=True)
    with pytest.raises(ValueError):s.render('rverb',audio,44100,dict(decay_s=1,predelay_ms=0))
def test_invalid_duck(tmp_path):
    s=PrivateVocalStudy(tmp_path,{},trusted_local_build=True)
    with pytest.raises(ValueError):s.render('wet_return',np.zeros((100,2)),44100,dict(duck=True))
def test_bad_doubler(tmp_path):
    s=PrivateVocalStudy(tmp_path,{},trusted_local_build=True);p=np.zeros(57);p[17]=.99
    with pytest.raises(ValueError):s.render('doubler',np.zeros((100,2)),44100,p)
