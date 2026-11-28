import hashlib
import pytest
from skell_sound_match.wav_only.frozen_dependencies import dependency_namespace

DIGEST = hashlib.sha256(b'parent archive').hexdigest()


def test_stable_under_unrelated_files(tmp_path):
    (tmp_path/'a').write_bytes(b'a')
    (tmp_path/'b').write_bytes(b'b')
    h = dependency_namespace(tmp_path, ['a','b'], DIGEST)
    (tmp_path/'new.py').write_bytes(b'new experiment')
    assert dependency_namespace(tmp_path, ['b','a'], DIGEST) == h


def test_changed_dependency_changes_namespace(tmp_path):
    (tmp_path/'a').write_bytes(b'a')
    h = dependency_namespace(tmp_path, ['a'], DIGEST)
    (tmp_path/'a').write_bytes(b'new version')
    assert dependency_namespace(tmp_path, ['a'], DIGEST) != h
    assert dependency_namespace(tmp_path, ['a'], '0'*64) != h


@pytest.mark.parametrize('paths', [[], ['a','a'], ['../a'], ['/a'], ['a/../b'], ['a\\b'], ['a//b'], ['C:/a']])
def test_invalid_names(tmp_path, paths):
    with pytest.raises(ValueError):
        dependency_namespace(tmp_path, paths, DIGEST)


def test_missing_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        dependency_namespace(tmp_path, ['missing'], DIGEST)


def test_bad_digest(tmp_path):
    (tmp_path/'a').touch()
    with pytest.raises(ValueError):
        dependency_namespace(tmp_path, ['a'], 'not a digest')
