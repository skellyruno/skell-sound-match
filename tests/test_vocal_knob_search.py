import json

import numpy as np
import pytest
import soundfile as sf

from skell_sound_match.wav_only.vocal_knob_search import (
    Window, KNOBS, _score, _features, optimize, render, run_files,
)

SR = 32000
PAIR = {"same_take": True, "take_id": "synthetic-001",
        "source_stage": "standalone_main", "target_stage": "target_processed_main"}


def tone(seconds=2.1):
    t = np.arange(int(SR * seconds)) / SR
    base = .04*np.sin(2*np.pi*200*t)*(1+.2*np.sin(2*np.pi*2*t))
    highs = .015*np.sin(2*np.pi*4800*t)
    return np.column_stack((base+highs, base+.4*highs)).astype(np.float64)


def kw():
    return {k: v[2] for k, v in KNOBS.items()}


def test_finishing_identity_and_mono_no_fake_width():
    x=tone()
    assert np.max(abs(render(x,SR,kw())-x))<1e-10
    mono=np.column_stack((x[:,0],x[:,0]))
    p=kw();p['side_gain']=1.8
    y=render(mono,SR,p)
    assert np.max(abs(y[:,0]-y[:,1]))<1e-10


def test_feature_score_prefers_matching_spectral_content():
    x=tone()
    ref=render(x,SR,kw()|{'air_db':3.0})
    fref=_features(ref,SR,Window(.25,1))
    raw=_score(fref,_features(x,SR,Window(.25,1)))
    same=_score(fref,_features(ref,SR,Window(.25,1)))
    assert raw['score']>same['score']
    assert same['score']<1e-5


def test_search_deterministic_and_holdout_regression_gate():
    x=tone()
    ref=render(x,SR,kw()|{'air_db':3})
    kwargs={'pairing':PAIR,'train':Window(0.15,.9),'holdout':Window(1.2,1.95),'seed':7,'budget':24}
    a=optimize(x,ref,SR,**kwargs)
    b=optimize(x,ref,SR,**kwargs)
    assert a.params==b.params
    assert a.trial_holdout['score'] <= a.baseline_holdout['score']
    assert a.accepted_for_listening
    assert a.evaluation_count==24


def test_all_equal_is_not_false_improvement():
    x=tone()
    r=optimize(x,x,SR,pairing=PAIR,train=Window(.1,.8),holdout=Window(1.1,1.8),budget=8)
    assert not r.accepted_for_listening


def test_pairing_and_window_rejection():
    x=tone()
    base={'train':Window(.1,.8),'holdout':Window(1.1,1.8),'budget':8}
    with pytest.raises(ValueError,match='same_take'):
        optimize(x,x,SR,pairing=PAIR|{'same_take':False},**base)
    with pytest.raises(ValueError,match='stages'):
        optimize(x,x,SR,pairing=PAIR|{'target_stage':''},**base)
    with pytest.raises(ValueError,match='non-overlapping'):
        optimize(x,x,SR,pairing=PAIR,train=Window(.1,1.2),holdout=Window(1.1,1.8),budget=8)
    with pytest.raises(ValueError,match='frame count'):
        optimize(x,x[:-1],SR,pairing=PAIR,**base)
    with pytest.raises(ValueError):
        render(x,SR,kw()|{'side_gain':8.})


def test_private_file_mode_refuses_to_overwrite(tmp_path):
    x=tone()
    src=tmp_path/'source.wav';ref=tmp_path/'target.wav'
    sf.write(src,x,SR)
    sf.write(ref,render(x,SR,kw()|{'air_db':2.0}),SR)
    out=tmp_path/'private_results'
    args={'pairing':PAIR, 'train':Window(.2,.9),'holdout':Window(1.2,1.9),'budget':14}
    result=run_files(src,ref,out,**args)
    assert result['approved'] is False
    assert result['source_sha256'] != result['reference_sha256']
    assert (out/'experimental_candidate.wav').exists()
    assert json.loads((out/'trial_report.json').read_text())['validation_scope']=='same_take_holdout_not_independent_performance'
    with pytest.raises(FileExistsError):run_files(src,ref,out,**args)


def test_optional_pedalboard_fx_runtime_and_stereo():
    pytest.importorskip('pedalboard')
    x=tone(.55)
    from skell_sound_match.wav_only.vocal_knob_search import FX_KNOBS
    p=kw()|{k:v[2] for k,v in FX_KNOBS.items()}
    p['chorus_mix']=.18;p['delay_mix']=.05;p['reverb_wet']=.08
    rendered=render(x,SR,p,effects=True)
    assert rendered.shape==x.shape and np.all(np.isfinite(rendered))


def test_fif_ears_signal_snapshot_is_optional_and_signal_only(monkeypatch):
    from types import ModuleType
    import sys
    from skell_sound_match.wav_only.vocal_knob_search import fif_ears_signal_snapshot
    ears=ModuleType('ears')
    ea=ModuleType('ears.audio')
    layers=ModuleType('ears.layers')
    sig=ModuleType('ears.layers.signal')
    class AudioData:
        def __init__(self, **data):
            self.__dict__.update(data)
    calls=[]
    def analyze(audio):
        calls.append(audio)
        return {'status':'ok','stereo_width':.2,'spectral_centroid_hz':{'mean':2000}}
    ea.AudioData=AudioData
    sig.analyze=analyze
    for name,obj in [('ears',ears),('ears.audio',ea),('ears.layers',layers),('ears.layers.signal',sig)]:
        monkeypatch.setitem(sys.modules,name,obj)
    result=fif_ears_signal_snapshot(tone(.5),SR)
    assert set(result)=={'tool','layer','status','signal'}
    assert result['layer']=='signal'
    assert calls[0].channels==2 and calls[0].sample_rate==SR
    assert not any(k in result for k in ('tempo_bpm','key','harmony'))


def test_stereo_floor_avoids_infinite_mono_width_penalty():
    from skell_sound_match.wav_only.vocal_knob_search import _features
    x=tone()
    mono=np.column_stack((x[:,0],x[:,0]))
    target=_features(x,SR,Window(.3,.9))
    got=_features(mono,SR,Window(.3,.9))
    assert got['side_mid_db']==-40.0
    assert abs(target['side_mid_db']-got['side_mid_db'])<40.0


def test_calibrates_output_gain_on_train_not_holdout():
    x=tone()
    ref=render(x,SR,kw()|{'air_db':2.5})*.20
    result=optimize(x,ref,SR,pairing=PAIR,train=Window(.1,.9),
                    holdout=Window(1.1,1.9),seed=11,budget=35)
    assert result.params['output_gain_db'] < -12
    assert abs(result.trial_holdout['gain_to_match_db'])<1
    assert result.accepted_for_listening


def test_stereo_incompleteness_blocks_false_acceptance():
    x=tone()
    mono=np.column_stack((x[:,0],x[:,0]))
    # Target differs in stereo and tone, which the width-only finisher cannot
    # reconstruct from perfectly dual-mono input.
    target=render(x,SR,kw()|{'air_db':3.0, 'side_gain':1.7})
    result=optimize(mono,target,SR,pairing=PAIR,train=Window(.1,.9),
                    holdout=Window(1.1,1.9),budget=24)
    assert result.trial_holdout['width_error_db']>6
    assert not result.accepted_for_listening
    assert result.reason == 'REJECTED_LOUDNESS_STEREO_OR_CHARACTER'


def test_phase_audit_flags_antiphase_stereo_and_fold_down_loss():
    from skell_sound_match.wav_only.vocal_knob_search import stereo_phase_profile
    x=tone(.5)
    dual=np.column_stack((x[:,0],x[:,0]))
    antiphase=np.column_stack((x[:,0],-x[:,0]*.8))
    a=stereo_phase_profile(dual)
    b=stereo_phase_profile(antiphase)
    assert not a['strong_antiphase']
    assert a['lr_correlation']>.999
    assert b['strong_antiphase']
    assert b['lr_correlation']<-.999
    assert b['mono_fold_down_loss_db']<-10
    assert a['mono_fold_down_loss_db']==pytest.approx(0.0,abs=.001)


def test_nonfinite_window_is_rejected():
    with pytest.raises(ValueError,match='finite'):
        optimize(tone(),tone(),SR,pairing=PAIR,train=Window(float('nan'),.8),holdout=Window(1.1,1.8),budget=8)


def test_phase_profile_detects_changing_channel_relationship():
    from skell_sound_match.wav_only.vocal_knob_search import stereo_phase_profile
    x=tone(2.)
    x[:,1]=x[:,0]
    x[SR:,1]*=-1
    profile=stereo_phase_profile(x,SR)['active_200ms_correlation']
    assert profile['windows']==10
    assert profile['minimum']<-.99 and profile['maximum']>.99


def test_full_render_trim_rechecks_actual_listening_level(tmp_path):
    x=tone();x[round(2.04*SR)]=[4.,4.]
    ref=render(x,SR,kw()|{'air_db':2.})
    src=tmp_path/'source.wav';target=tmp_path/'target.wav'
    sf.write(src,x,SR,subtype='FLOAT');sf.write(target,ref,SR,subtype='FLOAT')
    result=run_files(src,target,tmp_path/'private',pairing=PAIR,train=Window(.2,.9),holdout=Window(1.2,1.9),budget=8)
    assert not result['listening_eligible']
    assert abs(result['emitted_holdout']['gain_to_match_db'])>2
    assert result['status']=='REJECTED_EMITTED_AUDIO_SAFETY_OR_LEVEL'


def test_report_marks_missing_antiphase_without_claiming_accuracy(tmp_path):
    x=tone(2)
    src=tmp_path/'mono.wav';ref=tmp_path/'spatial.wav'
    sf.write(src,np.column_stack((x[:,0],x[:,0])),SR)
    sf.write(ref,np.column_stack((x[:,0],-x[:,0]*.8)),SR)
    out=tmp_path/'private'
    result=run_files(src,ref,out,pairing=PAIR,train=Window(.15,.85),
                     holdout=Window(1.1,1.85),budget=8)
    assert result['requires_antiphase_reconstruction']
    assert not result['listening_eligible']
    assert result['stereo_phase']['reference']['strong_antiphase']
