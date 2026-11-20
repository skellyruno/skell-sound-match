import json
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.quality_gate import evaluate, measure, cli

SR=16000

def tone(sec=3.0):
    t=np.arange(int(sec*SR))/SR
    carrier=np.sin(2*np.pi*205*t)+.2*np.sin(2*np.pi*615*t)
    mod=.25+.12*np.sin(2*np.pi*.6*t)
    return (carrier*mod)[:,None]

def test_identity_has_zero_error():
    x=tone()
    s=measure(x,x,SR)
    assert s['waveform_correlation_signed'] > .9999999
    assert s['multires_spectral_mae_db'] < 1e-10
    assert s['envelope_20ms_mae_db'] == 0

def test_polarity_is_not_hidden():
    x=tone()
    assert measure(x,-x,SR)['waveform_correlation_signed'] < -.9999

def test_strict_shape_checks():
    x=tone(15)
    with pytest.raises(ValueError, match='identical shapes'):
        evaluate(x,x,x[:-1],SR)
    with pytest.raises(ValueError, match='identical shapes'):
        evaluate(x,x,np.column_stack((x,x)),SR)

def test_no_split_leakage():
    x=tone(15)
    with pytest.raises(ValueError, match='Chronological'):
        evaluate(x,x,x,SR,windows={'training':(.8,6), 'validation':(5.5,10), 'test':(11,14)})

def test_nonfinite_input_rejected():
    x=tone(15)
    y=x.copy();y[4,0]=np.nan
    with pytest.raises(ValueError, match='finite'):
        evaluate(x,x,y,SR)

def test_loudness_gain_cheat_rejected():
    x=tone(15)*.15
    report=evaluate(x,x,x*2.0,SR)
    assert report['status']=='unsafe_or_unfair_audition'
    assert any('loudness' in z for z in report['audition_blockers'])

def test_bad_peaks_rejected():
    x=tone(15)*4
    report=evaluate(x*.25,x*.25,x,SR,max_loudness_delta=20)
    assert any('true-peak' in z for z in report['audition_blockers'])

def test_strict_safety_no_promotion_for_identical():
    x=tone(15)*.15
    r=evaluate(x,x,x,SR)
    assert r['status']=='mixed_or_insufficient_improvement'
    assert r['improved_on_both_holdout_sections']==[]

def test_candidate_that_fixes_mismatch_is_audition_only():
    x=tone(15)*.2
    champ=x*.92
    r=evaluate(x,champ,x,SR)
    assert r['status']=='audition_candidate_no_auto_promotion'
    assert r['improved_on_both_holdout_sections']

def test_cli_refuses_overwrite_and_does_not_publish_paths(tmp_path):
    x=tone(15)*.15
    files=[]
    for name,scale in [('reference',1),('champion',.92),('candidate',1)]:
        path=tmp_path/f'private-{name}.wav'
        sf.write(path,x*scale,SR,subtype='PCM_24')
        files.append(str(path))
    out=tmp_path/'output.json'
    cli([*files,'--out',str(out)])
    result=json.loads(out.read_text())
    assert result['paths_recorded'] is False
    assert all(len(x)==64 for x in result['input_sha256'].values())
    assert 'private-reference' not in out.read_text()
    with pytest.raises(FileExistsError):
        cli([*files,'--out',str(out)])