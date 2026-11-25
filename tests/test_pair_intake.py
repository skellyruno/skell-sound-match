import hashlib
import json
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.pair_intake import audit_manifest


def corpus(tmp_path):
    rate=44100
    n=round(2.2*rate)
    t=np.arange(n)/rate
    x=.28*np.sin(2*np.pi*180*t)*(0.2+0.7*np.sin(2*np.pi*.6*t)**2)
    y=np.stack((x,x*.8),axis=1)
    for name, data in [('dry',y),('original',y*.7),('candidate',y*.85)]:
        sf.write(tmp_path/f'{name}.wav',data,rate,subtype='PCM_24')
    entry={'source':'dry.wav','reference':'original.wav','candidate':'candidate.wav','target':'synthetic'}
    for k,file in [('source','dry'),('reference','original'),('candidate','candidate')]:
        entry[f'{k}_expected_sha256']=hashlib.sha256((tmp_path/f'{file}.wav').read_bytes()).hexdigest()
    path=tmp_path/'manifest.json';path.write_text(json.dumps({'pairs':[entry]}))
    return entry,path


def test_no_metadata_does_not_authorize_promotion(tmp_path):
    entry,path=corpus(tmp_path)
    res=audit_manifest(path)['pairs'][0]
    assert not res['pair_provenance_gate_passed']
    assert res['alignment_diagnostic_only']['source_vs_reference']['best_similarity']>.99
    assert not res['alignment_diagnostic_only']['source_vs_reference']['identity_verified']


def test_fully_documented_same_take_can_clear_gate(tmp_path):
    entry,path=corpus(tmp_path)
    entry.update(source_take_id='TAKE-1',reference_take_id='TAKE-1',candidate_take_id='TAKE-1',
                 reference_stage='full-effects',candidate_stage='full-effects',
                 source_offset_samples=0,reference_offset_samples=0,candidate_offset_samples=0,
                 offsets_verified=True,evidence_origin='export_manifest')
    path.write_text(json.dumps({'pairs':[entry]}))
    result=audit_manifest(path)['pairs'][0]
    assert result['pair_provenance_gate_passed']
    assert result['eligible_for_preset_promotion'] is False


def test_different_takes_fail_even_with_identical_audio(tmp_path):
    entry,path=corpus(tmp_path)
    entry.update(source_take_id='A',reference_take_id='B',candidate_take_id='A',
                 reference_stage='full-effects',candidate_stage='full-effects',
                 source_offset_samples=0,reference_offset_samples=0,candidate_offset_samples=0,
                 offsets_verified=True,evidence_origin='export_manifest')
    path.write_text(json.dumps({'pairs':[entry]}))
    result=audit_manifest(path)['pairs'][0]
    assert not result['pair_provenance_gate_passed']


def test_checksum_tampering_blocks_promotion(tmp_path):
    entry,path=corpus(tmp_path)
    entry.update(source_take_id='A',reference_take_id='A',candidate_take_id='A',
                 reference_stage='full-effects',candidate_stage='full-effects',
                 source_offset_samples=0,reference_offset_samples=0,candidate_offset_samples=0,
                 offsets_verified=True,evidence_origin='verified_session',
                 reference_expected_sha256='0'*64)
    path.write_text(json.dumps({'pairs':[entry]}))
    res=audit_manifest(path)['pairs'][0]
    assert not res['pair_provenance_gate_passed']
    assert any('checksum' in r for r in res['blockers'])


def test_manifest_missing_pair_rejected(tmp_path):
    p=tmp_path/'m.json';p.write_text(json.dumps({'pairs':[{}]}))
    with pytest.raises(ValueError):audit_manifest(p)
