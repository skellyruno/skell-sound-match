import numpy as np
import pytest
from skell_sound_match.wav_only.phase_alignment import fit,render
from skell_sound_match.wav_only.conservative_gate import render as gate


def test_causal_phase_model_has_explicit_latency_and_frozen_replay():
    sr=32000;rng=np.random.default_rng(15);x=rng.normal(0,.03,(sr*4,2));x[:,1]=x[:,0]
    target=np.concatenate((np.zeros((84,2)),x[:-84]))
    model=fit(x,target,sr,round(sr*2.3))
    a=render(x,sr,model);latency=model['latency_samples']
    assert len(a)==len(x)+latency and latency==2048
    sl=slice(sr*2,sr*3)
    assert np.sqrt(np.mean((a[latency:][sl]-target[sl])**2))<.005
    other=rng.normal(0,.02,x.shape);other[:,1]=other[:,0]
    assert np.isfinite(render(other,sr,model)).all()


def test_gate_reduces_quiet_noise_and_rejects_nonfinite():
    sr=32000;x=np.ones((sr,2))*.00001
    assert np.mean(gate(x,sr)[sr//2:]**2)<np.mean(x**2)*.01
    with pytest.raises(ValueError):gate(x*np.nan,sr)
