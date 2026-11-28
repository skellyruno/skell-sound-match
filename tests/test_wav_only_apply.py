from pathlib import Path
import sys
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.wav_only.apply_reconstructed_preset import process,render_file
from skell_sound_match.wav_only.wav_only_effect_match import file_hash
from skell_sound_match.wav_only.skelly_reference_eq_trial import CENTERS


def synthetic_recipe(stage, sha):
    return {'schema':'skelly.wav-only.standalone-experiment.v1','target':'hop_out',
            'main_model':{'eq_centers_hz':list(CENTERS),'eq_gain_db':[0.]*len(CENTERS),
                'leveler_slope':0.,'leveler_tau_s':.025,'train_only_output_gain_db':0.},
            'stage_models':[{'name':stage,'sha256':sha,'mixer_gain':.7}]}


def test_replay_frozen_recipe_has_no_reference_audio_dependency(tmp_path):
    sr=32000
    n=sr*3
    t=np.arange(n)/sr
    x=(.02*np.sin(2*np.pi*180*t))[:,None]
    src=np.repeat(x,2,axis=1)
    np.savez_compressed(tmp_path/'test_model.npz',impulse=np.array([[.01,.03]]),sample_rate=np.array(sr))
    recipe=synthetic_recipe('test_model',file_hash(tmp_path/'test_model.npz'))
    result,meta=process(src,sr,recipe,tmp_path)
    assert result.shape==src.shape
    assert meta['used_stages']==['test_model']
    assert meta['estimated_true_peak_posttrim_dbtp'] <= -1.18
    assert np.max(np.abs(result-src))>.000001


def test_model_sha_guard_and_wrong_sr(tmp_path):
    sr=32000
    src=np.ones((sr*3,2))*.001
    np.savez_compressed(tmp_path/'fx.npz',impulse=np.array([[.01,.03]]),sample_rate=np.array(sr))
    recipe=synthetic_recipe('fx',file_hash(tmp_path/'fx.npz'))
    np.savez_compressed(tmp_path/'fx.npz',impulse=np.array([[.02,.04]]),sample_rate=np.array(sr))
    with pytest.raises(ValueError,match='modified'):
        process(src,sr,recipe,tmp_path)
    recipe['stage_models'][0]['sha256']=file_hash(tmp_path/'fx.npz')
    with pytest.raises(ValueError,match='Unsupported stage model'):
        process(src,48000,recipe,tmp_path)


def test_untrained_stereo_widening_is_rejected(tmp_path):
    sr=32000
    src=np.ones((sr*3,2))*.002
    np.savez_compressed(tmp_path/'fx.npz',impulse=np.array([[0.,0.]]),sample_rate=np.array(sr))
    recipe=synthetic_recipe('fx',file_hash(tmp_path/'fx.npz'))
    with pytest.raises(ValueError,match='No trained stereo-width'):
        process(src,sr,recipe,tmp_path,widen=True)


def test_standalone_refuses_replacement(tmp_path):
    sr=32000
    src=np.ones((sr*3,2))*.002
    file=tmp_path/'input.wav';sf.write(file,src,sr)
    r=tmp_path/'r.json';r.write_text('{}')
    with pytest.raises(ValueError,match='collision'):
        render_file(file,r,tmp_path,file)
