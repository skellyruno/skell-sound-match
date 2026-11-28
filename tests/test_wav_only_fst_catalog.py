import json
import struct
import zipfile
import pytest
from skell_sound_match.wav_only.flstudio_preset_catalog import inspect_fst, inspect_zip


def fake_fst(*names):
    payload = '\x00'.join(names).encode('utf-16le') + b'\0\0'
    return b'FLhd' + struct.pack('<IHHH', 6, 64, 42, 96) + b'FLdt' + struct.pack('<I', len(payload)) + payload


def test_order_and_repeats_without_private_paths():
    data = fake_fst('FL Studio 26.1.6.5639', 'C:\\private\\secret.wav',
                    'Fruity Chorus', 'Fruity Parametric EQ 2',
                    'Fruity Parametric EQ 2', 'Maximus')
    x = inspect_fst(data, 'name.fst')
    assert x['candidate_effect_names_in_serialized_order'] == [
        'Fruity Chorus', 'Fruity Parametric EQ 2',
        'Fruity Parametric EQ 2', 'Maximus']
    assert 'secret' not in json.dumps(x)
    assert not x['plugin_settings_verified'] and not x['active_bypass_states_verified']


def test_invalid_containers():
    data = fake_fst('Fruity Limiter')
    for bad in (b'', b'RIFF'+data[4:], data[:-1],
                data[:18]+b'\xff\xff\xff\x7f'+data[22:]):
        with pytest.raises(ValueError):
            inspect_fst(bad)


def test_zip_only_fst_metadata(tmp_path):
    path=tmp_path/'incoming.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('muffle.fst', fake_fst('FL Studio 26.1.6.5639','Fruity Love Philter'))
        z.writestr('secret.flp', b'personal project')
        z.writestr('private.wav', b'voice audio')
    result=inspect_zip(path)
    assert result['fst_count']==1
    assert result['presets'][0]['candidate_effect_names_in_serialized_order']==['Fruity Love Philter']
    assert 'personal project' not in json.dumps(result)
    assert 'voice audio' not in json.dumps(result)


def test_path_traversal_rejected(tmp_path):
    path=tmp_path/'bad.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('../private.fst',fake_fst('Fruity Chorus'))
    with pytest.raises(ValueError,match='Unsafe archive path'):
        inspect_zip(path)


def test_duplicate_entries_rejected(tmp_path):
    path=tmp_path/'duplicate.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('X.fst',fake_fst('Fruity Chorus'))
        z.writestr('x.fst',fake_fst('Fruity Chorus'))
    with pytest.raises(ValueError,match='Duplicate archive path'):
        inspect_zip(path)
