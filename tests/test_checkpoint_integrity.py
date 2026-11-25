import hashlib
import json
import zipfile
import pytest
from skell_sound_match.checkpoint_integrity import verify, MANIFEST, SCHEMA


def archive(tmp_path, entries, records=None):
    p = tmp_path / 'test.zip'
    if records is None:
        records = [{'path': n, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for n, b in entries]
    with zipfile.ZipFile(p, 'w') as z:
        for n, b in entries:
            z.writestr(n, b)
        z.writestr(MANIFEST, json.dumps({'schema': SCHEMA, 'files': records}))
    return p


def test_complete(tmp_path):
    p = archive(tmp_path, [('private/a.zip', b'abc'), ('notes.txt', b'notes')])
    assert verify(p)['verified_files'] == 2


@pytest.mark.parametrize('name', ['../escape', '/abs', 'a/../b', 'a//b', 'C:/x', 'a\\b'])
def test_unsafe(tmp_path, name):
    with pytest.raises(ValueError, match='unsafe'):
        verify(archive(tmp_path, [(name, b'x')]))


def test_duplicate_case(tmp_path):
    with pytest.raises(ValueError, match='duplicate'):
        verify(archive(tmp_path, [('A.txt', b'x'), ('a.txt', b'y')]))


@pytest.mark.parametrize('records', [[], [{'path':'a', 'bytes':1, 'sha256':'0'*64}], [{'path':'a', 'bytes':2, 'sha256':'0'*64}], [{'path':'missing', 'bytes':1, 'sha256':'0'*64}]])
def test_bad_manifest(tmp_path, records):
    with pytest.raises(ValueError):
        verify(archive(tmp_path, [('a', b'x')], records))
