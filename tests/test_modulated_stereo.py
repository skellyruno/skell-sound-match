import numpy as np
import pytest

from skell_sound_match.wav_only.modulated_stereo import fit,render


def test_moving_delay_generalizes_to_disjoint_audio_and_frozen_independent_input():
    sr=32000
    rng=np.random.default_rng(432)
    source=rng.normal(0,.04,(sr*4,1))
    truth={'sample_rate':sr,'parameters':{'base_s':.006,'depth_s':.003,'rate_hz':.4,'phase_rad':0.},
           'coefficients':[[.7,.7],[.25,0.],[0.,.25]]}
    target=render(source,sr,truth)
    model,report=fit(source,target,sr,(.1,1.6),(2.,3.8),rates=(.25,.4),bases=(.006,),depths=(.003,),phases=(0.,))
    assert report['status']=='HELDOUT_RESEARCH_PASS'
    assert report['scores']['holdout']['moving']['relative_stereo_rms']<1e-4
    independent=rng.normal(0,.03,(sr*4,1))
    assert np.sqrt(np.mean((render(independent,sr,model)-render(independent,sr,truth))**2))<1e-5
    assert report['independent_performance']=='UNVERIFIED'


def test_overlap_nonfinite_and_noncausal_models_rejected():
    source=np.zeros((32000*3,1));target=np.zeros((32000*3,2))
    with pytest.raises(ValueError,match='disjoint'):fit(source,target,32000,(0,2),(1,3))
    with pytest.raises(ValueError,match='Noncausal'):
        render(source,32000,{'sample_rate':32000,'parameters':{'base_s':.001,'depth_s':.003,'rate_hz':.4,'phase_rad':0.},'coefficients':[]})
