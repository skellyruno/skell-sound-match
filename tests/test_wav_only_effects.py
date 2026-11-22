from pathlib import Path
import sys
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.wav_only import wav_only_effect_match as fx


def signal_source(sr=32000, duration=6., seed=20):
    rng=np.random.default_rng(seed)
    x=.025*signal_burst(sr,duration) + .006*rng.standard_normal(round(sr*duration))
    return np.stack([x,x],axis=1)


def signal_burst(sr,duration):
    t=np.arange(round(sr*duration))/sr
    return np.sin(2*np.pi*(147*t+30*np.sin(2*np.pi*.8*t))) * (.5+.5*np.sin(2*np.pi*.43*t))


def test_causal_echo_discovery_and_unseen_holdout():
    sr=32000
    source=signal_source(sr)
    n=round(.44*sr)
    h=np.zeros((n*3+200,2))
    h[n]=[.16,.015]
    h[n*2]=[.01,.10]
    h[n*3]=[.03,.01]
    wet=fx.render_wet(source,h)
    actual,meta=fx.learn_delay(source,wet,sr,(0,round(3.3*sr)),(.38,.52))
    predicted=fx.render_wet(source,actual)
    hold=(round(3.6*sr),round(5.8*sr))
    assert abs(meta['first_delay_ms']-440)<1.5
    assert fx.wet_metrics(wet,predicted,hold)['wet_relative_rms_error']<.12
    # Editing heldout target cannot change training-derived fit.
    changed=wet.copy()
    changed[hold[0]:]=np.sin(np.arange(len(wet)-hold[0])[:,None])*.001
    another,_=fx.learn_delay(source,changed,sr,(0,round(3.3*sr)),(.38,.52))
    assert np.array_equal(actual,another)


def test_reverb_wiener_causal_fir_separate_holdout():
    sr=32000
    source=signal_source(sr)
    h=np.zeros((round(.12*sr),2))
    h[400]=[.08,.04]
    h[1500]=[.04,-.03]
    wet=fx.render_wet(source,h)
    fit,meta=fx.learn_reverb(source,wet,sr,(0,round(3.5*sr)),.2,.0005)
    hold=(round(4*sr),round(5.9*sr))
    pred=fx.render_wet(source,fit)
    assert meta['method']=='causal_regularized_fir_system_identification'
    assert fx.wet_metrics(wet,pred,hold)['wet_relative_rms_error']<.12


def test_mono_collapse_rejects_stereo_information():
    x=signal_source()
    x[:,1]*=-1
    with pytest.raises(ValueError,match='effectively mono'):
        fx.check_mono_compatible(x)


def test_rejects_overlapping_or_short_windows():
    with pytest.raises(ValueError,match='separate'):
        fx.windows_ok((1,3),(2,4),32000,32000*7)
    with pytest.raises(ValueError,match='separate'):
        fx.windows_ok((1,1.5),(4,5),32000,32000*7)


def test_rejects_bad_nan_and_sample_rate(tmp_path):
    p=tmp_path/'bad.wav'
    sf.write(p,signal_source(sr=22050),22050)
    with pytest.raises(ValueError,match='32–192'):
        fx.read_audio(p)
    with pytest.raises(ValueError):
        fx.render_wet(signal_source(),np.ones((10,1)))


def test_preview_safety_trim_is_finite():
    sr=32000
    x=signal_source(sr)
    y,info=fx.safe_preview(x*80.,-1.2)
    assert info['safety_trim_db'] < -1
    assert info['estimated_true_peak_posttrim_dbtp']<=-1.19
    assert np.isfinite(y).all() and np.max(np.abs(y))<1


def test_write_refuses_to_replace_source(tmp_path):
    x=signal_source()
    main=tmp_path/'main.wav'
    target=tmp_path/'target.wav'
    sf.write(main,x,32000,subtype='PCM_24')
    sf.write(target,x,32000,subtype='PCM_24')
    with pytest.raises(ValueError,match='collision'):
        fx.write_model_and_preview(main,target,'delay',(0,3),(4,5),tmp_path/'mod.npz',tmp_path/'rep.json',main)


def test_audio_io_and_model_apply(tmp_path):
    sr=32000
    src=signal_source(sr)
    h=np.zeros((sr,2));h[round(.4*sr)]=[.12,.02];h[round(.8*sr)]=[.02,.08]
    y=src+fx.render_wet(src,h)
    main=tmp_path/'main.wav'; target=tmp_path/'wet.wav'
    sf.write(main,src,sr,subtype='PCM_24')
    sf.write(target,y,sr,subtype='PCM_24')
    model=tmp_path/'model.npz';report=tmp_path/'report.json';preview=tmp_path/'render.flac'
    result=fx.write_model_and_preview(main,target,'delay',(0,3.5),(4,5.8),model,report,preview,delay_range=(.35,.5))
    assert result['scores']['holdout']['wet_relative_rms_error']<.20
    assert model.exists() and report.exists()
    y2,sr2=fx.read_audio(preview)
    assert y2.shape==src.shape and sr2==sr
    with pytest.raises(FileExistsError):
        fx.write_model_and_preview(main,target,'delay',(0,3.5),(4,5.8),model,report,preview)
    preview2=tmp_path/'fresh.flac'
    fx.apply_model(main,model,preview2)
    with pytest.raises(FileExistsError):
        fx.apply_model(main,model,preview2)


def test_lti_modulation_label_does_not_claim_true_chorus(tmp_path):
    x=signal_source()
    wet=fx.render_wet(x,np.vstack([np.zeros((80,2)),np.ones((1,2))*.04]))
    p=tmp_path/'main.wav';q=tmp_path/'wet.wav'
    sf.write(p,x,32000);sf.write(q,x+wet,32000)
    imp,report=fx.train_effect(p,q,'linear_fir',(0,3.5),(4,5.8),response_seconds=.06)
    assert imp.shape[1]==2
    assert 'modulation' in report['parameters']['limitation']
