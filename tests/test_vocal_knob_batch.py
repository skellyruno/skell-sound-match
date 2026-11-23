import json

import numpy as np
import pytest
import soundfile as sf

from skell_sound_match.wav_only.vocal_knob_batch import process_batch, SCHEMA
from skell_sound_match.wav_only.vocal_knob_search import KNOBS, render


def _make(tmp_path):
    sr=32000
    t=np.arange(sr*2)/sr
    x=.06*np.sin(2*np.pi*170*t)+.02*np.sin(2*np.pi*4200*t)
    x=np.column_stack((x,x*.9))
    src=tmp_path/'source.wav';ref=tmp_path/'reference.wav'
    sf.write(src,x,sr)
    p={k:v[2] for k,v in KNOBS.items()};p['air_db']=2
    sf.write(ref,render(x,sr,p),sr)
    return {'schema':SCHEMA,'pairs':[{'id':'vocals-1','source':'source.wav',
      'reference':'reference.wav','same_take':True,'take_id':'test-take',
      'source_stage':'dry_input','target_stage':'processed_main',
      'train':[.15,.8],'holdout':[1.1,1.85],'budget':10}]}


def test_batch_caches_exact_content_and_never_overwrites(tmp_path):
    doc=_make(tmp_path)
    manifest=tmp_path/'pairs.json';manifest.write_text(json.dumps(doc))
    out=tmp_path/'private_results'
    first=process_batch(manifest,out)
    assert len(first['processed'])==1 and not first['blocked']
    second=process_batch(manifest,out)
    assert len(second['cached'])==1 and not second['processed']
    assert first['processed'][0]['path']==second['cached'][0]['path']
    # Changed reference must create a different content-addressed trial directory.
    data,sr=sf.read(tmp_path/'reference.wav');sf.write(tmp_path/'reference.wav',data*.95,sr)
    third=process_batch(manifest,out)
    assert len(third['processed'])==1
    assert first['processed'][0]['path']!=third['processed'][0]['path']


def test_incomplete_pair_is_reported_not_guessed(tmp_path):
    doc=_make(tmp_path)
    doc['pairs'][0]['same_take']=False
    manifest=tmp_path/'pairs.json';manifest.write_text(json.dumps(doc))
    result=process_batch(manifest,tmp_path/'private_results')
    assert len(result['blocked'])==1
    assert 'same_take' in result['blocked'][0]['error']
    assert not result['processed']


def test_tampered_cached_audio_is_blocked(tmp_path):
    manifest=tmp_path/'pairs.json'
    manifest.write_text(json.dumps(_make(tmp_path)))
    out=tmp_path/'private_results'
    result=process_batch(manifest,out)
    report_path=__import__('pathlib').Path(result['processed'][0]['path'])
    (report_path.parent/'experimental_candidate.wav').write_bytes(b'tampered')
    result=process_batch(manifest,out)
    assert result['blocked'] and not result['cached'] and not result['processed']


def test_path_injection_and_duplicate_identity_rejected(tmp_path):
    doc=_make(tmp_path)
    doc['pairs'][0]['id']='../../danger'
    manifest=tmp_path/'pairs.json';manifest.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='safe'):
        process_batch(manifest,tmp_path/'private_results')
    doc['pairs'][0]['id']='ok'
    doc['pairs'].append(doc['pairs'][0].copy())
    manifest.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='Duplicate'):
        process_batch(manifest,tmp_path/'private_results')
