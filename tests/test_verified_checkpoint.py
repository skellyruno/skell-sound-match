import hashlib
import json
import pytest
from skell_sound_match.wav_only.verified_checkpoint import verified_report


def fixture(d):
    data=b'fixed recipe'; (d/'case_safe.npz').write_bytes(data)
    r=dict(id='case',source_dry_sha='dry',source_target_sha='ref',trial_count=1,trials=[{}],selected=dict(recipe_sha256=hashlib.sha256(data).hexdigest(),heldout={'score':.8},heldout48_resampled44={'score':.9},peak44_dbTP=-1.2,peak48_dbTP=-1.1,stress44_dbTP=-.2,stress48_dbTP=-.1,safe=True))
    (d/'case.json').write_text(json.dumps(r)); return r

def test_valid(tmp_path):
    r=fixture(tmp_path); assert verified_report(tmp_path,'case','dry','ref')==r

def test_partial_missing_recipe(tmp_path):
    fixture(tmp_path); (tmp_path/'case_safe.npz').unlink(); assert verified_report(tmp_path,'case','dry','ref') is None

def test_corrupt_recipe(tmp_path):
    fixture(tmp_path); (tmp_path/'case_safe.npz').write_bytes(b'bad'); assert verified_report(tmp_path,'case','dry','ref') is None

def test_wrong_source(tmp_path):
    fixture(tmp_path); assert verified_report(tmp_path,'case','other','ref') is None

@pytest.mark.parametrize('field,value',[('safe',False),('peak44_dbTP',.1),('stress48_dbTP',float('nan'))])
def test_reject_inconsistent_metrics(tmp_path,field,value):
    r=fixture(tmp_path);r['selected'][field]=value;(tmp_path/'case.json').write_text(json.dumps(r));assert verified_report(tmp_path,'case','dry','ref') is None

def test_incomplete_trials(tmp_path):
    r=fixture(tmp_path);r['trial_count']=2;(tmp_path/'case.json').write_text(json.dumps(r));assert verified_report(tmp_path,'case','dry','ref') is None

def test_path_rejected(tmp_path):
    with pytest.raises(ValueError):verified_report(tmp_path,'../bad','dry','ref')
