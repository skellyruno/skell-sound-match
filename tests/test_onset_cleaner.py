import json
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.onset_cleaner import OnsetConfig, major_phrases, clean_onsets, cli

SR=16000

def generated():
    """Synthetic utterances with a 40 ms artificial pre-echo."""
    t=np.arange(5*SR)/SR
    clean=np.zeros_like(t)
    early=np.zeros_like(t)
    for start in (1.,3.):
        voiced=(t>=start)&(t<start+.7)
        clean[voiced]+=.18*np.sin(2*np.pi*202*t[voiced])
        echo=(t>=start-.04)&(t<start)
        early[echo]+=.025*np.sin(2*np.pi*202*t[echo])
    early+=clean
    return clean[:,None],early[:,None]

def test_detects_two_major_phrases():
    _,x=generated()
    p=major_phrases(x,SR,OnsetConfig(threshold_dbfs=-55))
    assert len(p)==2
    assert abs(p[0][0]/SR-.96)<.02
    assert abs(p[1][0]/SR-2.96)<.02

def test_mask_removes_pre_echo_without_changing_steady_vowels():
    truth,x=generated()
    xcopy=x.copy()
    y,info=clean_onsets(x,SR,OnsetConfig(threshold_dbfs=-55,onset_holdoff_ms=40,fade_ms=1.5))
    assert np.array_equal(x,xcopy)
    assert len(info['masked_intervals_samples'])==2
    for st in (1.,3.):
        pre=slice(int((st-.025)*SR),int((st-.005)*SR))
        vowel=slice(int((st+.1)*SR),int((st+.4)*SR))
        assert np.max(abs(y[pre]))<1e-9
        assert np.array_equal(y[vowel],x[vowel])
    assert np.linalg.norm(truth-y)<np.linalg.norm(truth-x)*.65

def test_stereo_same_layout_and_no_input_modification():
    truth,x=generated();s=np.concatenate([x,x*.99],axis=1);copy=s.copy()
    y,_=clean_onsets(s,SR,OnsetConfig(threshold_dbfs=-55))
    assert y.shape==s.shape and np.array_equal(s,copy)

def test_invalid_settings_and_nans_rejected():
    _,x=generated()
    with pytest.raises(ValueError):
        clean_onsets(x,SR,OnsetConfig(onset_holdoff_ms=250))
    z=x.copy();z[22]=np.nan
    with pytest.raises(ValueError):
        clean_onsets(z,SR,OnsetConfig())

def test_short_noise_does_not_trigger_phrase():
    x=np.zeros((SR*2,1))
    x[1000:1300,0]=.05
    y,info=clean_onsets(x,SR,OnsetConfig())
    assert len(info['masked_intervals_samples'])==0
    assert np.array_equal(x,y)

def test_cli_no_overwrite_and_safe_report(tmp_path):
    _,x=generated();src=tmp_path/'secret_vocal.wav'
    sf.write(src,x,SR,subtype='PCM_24')
    out=tmp_path/'new.wav';report=tmp_path/'report.json'
    cmd=[str(src),'--wav',str(out),'--report',str(report),'--threshold-dbfs','-55','--holdoff-ms','40']
    cli(cmd)
    assert out.exists() and report.exists()
    metadata=json.loads(report.read_text())
    assert metadata['reference_was_used_during_rendering'] is False
    assert metadata['source_sha256'] and len(metadata['source_sha256'])==64
    assert 'secret_vocal' not in report.read_text()
    with pytest.raises(FileExistsError):
        cli(cmd)

def test_cli_rejects_source_overwrite(tmp_path):
    _,x=generated();src=tmp_path/'in.wav';sf.write(src,x,SR)
    with pytest.raises(ValueError):
        cli([str(src),'--wav',str(src),'--report',str(tmp_path/'report.json'),
             '--threshold-dbfs','-55','--holdoff-ms','40'])