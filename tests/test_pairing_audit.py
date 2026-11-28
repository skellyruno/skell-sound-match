import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.wav_only.pairing_audit import alignment,audit_group,file_sha


def fixture(tmp_path):
    sr=32000;rng=np.random.default_rng(24);t=np.arange(sr*4)/sr
    x=rng.normal(0,.02,(len(t),2))*(.6+.4*np.sin(2*np.pi*.9*t))[:,None]
    paths={}
    for name,a in [('source',x),('ref',x*.7),('candidate',x*.7)]:
        p=tmp_path/(name+'.wav');sf.write(p,a,sr,subtype='PCM_24');paths[name]=p
    group={'id':'s','stage':'main','recording_id':'take1',
     'source':{'path':str(paths['source']),'sha256':file_sha(paths['source'])},
     'reference':{'path':str(paths['ref']),'sha256':file_sha(paths['ref']),'stage':'main','recording_id':'take1'},
     'candidates':[{'path':str(paths['candidate']),'sha256':file_sha(paths['candidate']),
      'source_sha256':file_sha(paths['source']),'fit_reference_sha256':file_sha(paths['ref']),
      'stage':'main','recording_id':'take1','version_id':'v1','complete_stage':True}]}
    return group,x,sr


def test_hash_stage_take_and_processing_gates(tmp_path):
    group,x,sr=fixture(tmp_path)
    assert audit_group(group,tmp_path)['status']=='PAIRING_CHECKS_PASS'
    group['reference']['stage']='full_effects'
    assert 'stage mismatch' in ' '.join(audit_group(group,tmp_path)['issues'])
    group['reference']['stage']='main';group['candidates'][0]['complete_stage']=False
    assert 'omits required' in ' '.join(audit_group(group,tmp_path)['issues'])
    group['candidates'][0]['sha256']='bad'
    with pytest.raises(ValueError,match='SHA-256'):audit_group(group,tmp_path)


def test_wrong_performance_and_uncompensated_offset_cannot_pass():
    sr=32000;rng=np.random.default_rng(60);x=rng.normal(0,.03,(sr*4,2))
    t=np.arange(len(x))/sr;x*=((np.sin(t*3)**2)+.1)[:,None]
    shifted=np.concatenate((np.zeros((320,2)),x[:-320]))
    assert alignment(x,shifted,sr)['status']=='UNVERIFIED'
    other=rng.normal(0,.03,x.shape)
    assert alignment(x,other,sr)['status']=='UNVERIFIED'
    assert alignment(x,x*.5,sr)['status']=='SIGNAL_PAIR_CHECK_PASS'
