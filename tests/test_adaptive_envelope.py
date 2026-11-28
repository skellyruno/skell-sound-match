import numpy as np
import pytest
from skell_sound_match.wav_only.adaptive_envelope import fit_envelope, apply_envelope


def example():
    rng=np.random.default_rng(23)
    source=rng.normal(size=32000)*np.repeat(rng.uniform(.01,.5,400),80)
    delayed=np.pad(source[:-800],(800,0))
    target=.4*source+.7*delayed
    return source,target


def test_frozen_prefix_and_bounded_gain():
    x,y=example();n=16000
    a=fit_envelope(x,y,8000,n)
    y[n:]=100
    b=fit_envelope(x,y,8000,n)
    np.testing.assert_array_equal(a.weights,b.weights)
    out=apply_envelope(x,x,a,strength=1,max_db=6)
    assert np.isfinite(out).all()
    assert np.max(np.abs(out/x))<=10**(.3)+1e-12
    assert np.min(np.abs(out/x))>=10**(-.3)-1e-12


def test_silence_and_validation():
    x=np.zeros(16000);a=fit_envelope(x,x,8000,8000)
    np.testing.assert_array_equal(apply_envelope(x,x,a),x)
    with pytest.raises(ValueError):fit_envelope(x,x,8000,100)
    with pytest.raises(ValueError):apply_envelope(x,x[:-1],a)
    with pytest.raises(ValueError):apply_envelope(x,x,a,strength=2)


def test_source_only_replay_is_deterministic():
    x,y=example();a=fit_envelope(x,y,8000,16000)
    b=apply_envelope(x,x,a);c=apply_envelope(x,x,a)
    np.testing.assert_array_equal(b,c)
