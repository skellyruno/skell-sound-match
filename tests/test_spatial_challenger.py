import numpy as np
import pytest
from skell_sound_match.wav_only.spatial_challenger import fit, render, calibrate_energy


def test_moving_delay_fit_is_causal_and_ignores_heldout_target():
    sr=32000
    rng=np.random.default_rng(133)
    source=rng.normal(0,.03,(sr*5,2))
    truth=dict(sample_rate=sr,rate=.45,base=.008,depth=.006,
               weights=[[.7,.7],[.25,-.2],[-.1,.2],[.1,-.1]])
    target=render(source,sr,truth)
    model,_=fit(source,target,sr,round(sr*3.2),rates=(.45,))
    prediction=render(source,sr,model)
    assert np.mean((prediction[sr*4:]-target[sr*4:])**2)<1e-8
    changed=target.copy();changed[sr*4:]*=-3
    other,_=fit(source,changed,sr,round(sr*3.2),rates=(.45,))
    assert model==other
    calibrated=calibrate_energy(source,target,sr,model,round(sr*3.2))
    changed_calibration=calibrate_energy(source,changed,sr,model,round(sr*3.2))
    assert calibrated==changed_calibration
    fresh=source.copy();fresh[sr*3:]=rng.normal(0,.2,fresh[sr*3:].shape)
    assert np.array_equal(render(fresh,sr,model)[:sr*3],prediction[:sr*3])


def test_spatial_fit_refuses_wrong_channel_format():
    with pytest.raises(ValueError):
        fit(np.zeros((120000,1)),np.zeros((120000,1)),32000,100000)


def test_composed_candidate_must_beat_starting_anchor_and_absolute_gates():
    from skell_sound_match.wav_only.spatial_challenger import qualifies_against_anchor
    original=dict(score=1.9,band_mae_db=2.,envelope_mae_db=2.,width_error_db=2.,lr_correlation_error=.1,gain_to_match_db=0.)
    worse=dict(original,score=2.1)
    assert not qualifies_against_anchor(worse,original)
    assert not qualifies_against_anchor(dict(original,score=1.,envelope_mae_db=10.),original)
    assert qualifies_against_anchor(dict(original,score=1.5,band_mae_db=1.8),original)
