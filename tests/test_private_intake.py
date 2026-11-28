import json
from pathlib import Path

import pytest

from skell_sound_match.wav_only.private_intake import intake
from skell_sound_match.wav_only.skelly_bulk_match import infer, open_db, items, materialize
from test_wav_only_bulk_match import audio_bytes


@pytest.mark.parametrize('name,target,role', [
    ('deuce test dry vocals.wav','deuce','dry'),
    ('deuce test main preset vocals.wav','deuce','main'),
    ('deuce test main preset no rec preset.wav','deuce','reference-stage'),
    ('deuce test main preset vocals no chorus or delay but stereo separation 33_.wav','deuce','reference-stage'),
    ('alchemist test vocals no main effects.wav','alchemist','rec'),
    ('alchemist test main effects on .wav','alchemist','main'),
    ('alchemist test last limiter off.wav','alchemist','reference-stage'),
    ('club angelic adlib w gate w delay.wav','angelic_adlib','all'),
    ('club mufflr adlibs w gate.wav','muffle_adlib','all'),
    ('club wobble adlib w gate.wav','wobbly_adlib','all'),
    ('club zaam adlib w gate.wav','zaam_adlib','all'),
])
def test_observed_exports_group_without_negation_confusion(name,target,role):
    assert infer(name)==(target,role)


def test_retained_duplicates_survive_deleted_upload_and_preserve_history(tmp_path):
    inbox=tmp_path/'inbox';inbox.mkdir()
    a=inbox/'speakerz dry.wav';a.write_bytes(audio_bytes())
    b=inbox/'speakerz main.wav';b.write_bytes(a.read_bytes())
    workspace=tmp_path/'private'
    first=intake([inbox],workspace)
    assert first['unique_objects']==1 and first['duplicate_entries']==1
    second=intake([inbox],workspace)
    assert second['scan']['unchanged_skipped']==2
    assert second['register_snapshot']==first['register_snapshot']
    register=workspace/'PRESET_REGISTER.json'
    data=json.loads(register.read_text())
    data['presets']['speakerz']['candidate_versions']=[{'version':'protected'}]
    register.write_text(json.dumps(data))
    a.unlink();b.unlink()
    result=intake([inbox],workspace)
    assert result['unique_objects']==1
    assert json.loads(register.read_text())['presets']['speakerz']['candidate_versions']==[{'version':'protected'}]
    db=open_db(workspace)
    assert materialize(items(db)[0],workspace).exists()
    db.close()


def test_private_boundary_and_recursive_self_intake(tmp_path):
    repo=tmp_path/'repo';repo.mkdir();(repo/'.git').mkdir()
    with pytest.raises(ValueError,match='outside'):
        intake([],repo/'private')
    with pytest.raises(ValueError,match='own workspace'):
        intake([tmp_path],tmp_path/'private')


def test_existing_cached_roles_are_refreshed_after_inference_upgrade(tmp_path):
    source=tmp_path/'deuce test dry vocals.wav';source.write_bytes(audio_bytes())
    workspace=tmp_path/'private';intake([source],workspace)
    db=open_db(workspace)
    db.execute("UPDATE items SET target_id='old_wrong_group'")
    db.execute("UPDATE archives SET fingerprint=replace(fingerprint, ':roles-v3-recording-hints', '')")
    db.commit();db.close()
    result=intake([source],workspace)
    assert result['targets'][0]['id']=='deuce'
    assert result['scan']['new_or_changed_archives']==1
