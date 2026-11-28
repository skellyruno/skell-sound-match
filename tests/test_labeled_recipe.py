import hashlib
import json
import pytest
from skell_sound_match.wav_only.labeled_recipe import verified_labeled_recipe


def fixture(d):
    a, b = b'best composite', b'best tone'
    (d/'x_safe.npz').write_bytes(a)
    (d/'x_tone.npz').write_bytes(b)
    r = dict(id='x', source_dry_sha='d', source_target_sha='t', selected=dict(recipe_sha256=hashlib.sha256(a).hexdigest()), tone_winner=dict(recipe_sha256=hashlib.sha256(b).hexdigest()))
    (d/'x.json').write_text(json.dumps(r))
    return r


@pytest.mark.parametrize('label,suffix',[('selected','safe'),('tone_winner','tone')])
def test_exact_label(tmp_path,label,suffix):
    fixture(tmp_path)
    assert verified_labeled_recipe(tmp_path,'x',label,'d','t') == tmp_path/f'x_{suffix}.npz'


def test_corrupt_tone_does_not_fallback(tmp_path):
    fixture(tmp_path); (tmp_path/'x_tone.npz').write_bytes(b'wrong')
    assert verified_labeled_recipe(tmp_path,'x','tone_winner','d','t') is None
    assert verified_labeled_recipe(tmp_path,'x','selected','d','t') is not None


def test_missing_tone_does_not_fallback(tmp_path):
    fixture(tmp_path); (tmp_path/'x_tone.npz').unlink()
    assert verified_labeled_recipe(tmp_path,'x','tone_winner','d','t') is None


def test_source_mismatch(tmp_path):
    fixture(tmp_path)
    assert verified_labeled_recipe(tmp_path,'x','tone_winner','d','other') is None


def test_missing_label(tmp_path):
    r=fixture(tmp_path); del r['tone_winner']; (tmp_path/'x.json').write_text(json.dumps(r))
    assert verified_labeled_recipe(tmp_path,'x','tone_winner','d','t') is None


@pytest.mark.parametrize('case,label',[('../x','selected'),('','selected'),('x','other'),('x',None)])
def test_invalid_identifier(tmp_path,case,label):
    with pytest.raises(ValueError): verified_labeled_recipe(tmp_path,case,label,'d','t')
