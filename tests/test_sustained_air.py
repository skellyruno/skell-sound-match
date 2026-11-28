import numpy as np
import pytest
from skell_sound_match.sustained_air import AirSettings,SustainedAir,render

def test_chunked_identical_to_monolithic():
    rng=np.random.default_rng(53)
    x=rng.normal(size=(32000,2))*.07
    s=AirSettings()
    a=render(x,44100,s)
    b=render(x,44100,s,chunk=241)
    assert np.max(np.abs(a-b))<1e-12

def test_zero_amount_exact_bypass():
    x=np.random.default_rng(2).normal(size=(10000,1))*.04
    assert np.array_equal(render(x,44100,AirSettings(amount=0)),x)

def test_silence_finite_and_unchanged():
    x=np.zeros((4096,2))
    assert np.array_equal(render(x,48000,AirSettings()),x)

def test_stateful_mono_stereo():
    rng=np.random.default_rng(100)
    for c in (1,2):
        x=rng.normal(size=(2000,c))*.02
        y=render(x,48000,AirSettings())
        assert y.shape==x.shape and np.isfinite(y).all()

def test_invalid_rejected():
    for s in [AirSettings(amount=.9),AirSettings(attack_ms=-1),AirSettings(knee_db=0),AirSettings(threshold_db=float('nan'))]:
        with pytest.raises(ValueError):render(np.zeros((400,1)),44100,s)
    with pytest.raises(ValueError):render(np.zeros((400,1)),16000,AirSettings())
    with pytest.raises(ValueError):render(np.full((400,1),np.inf),44100,AirSettings())
    with pytest.raises(ValueError):render(np.zeros((400,3)),44100,AirSettings())
