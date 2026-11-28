import copy,hashlib,json
import pytest
from skell_sound_match.transfer_preflight import validate_transfer,BOUNDS

COMMIT='a'*40
REGISTRY={0:'Empty',1:'EQ'}

def fixture():
    p={k:max(lo,min(hi,0)) for k,(lo,hi) in BOUNDS.items()}
    entry=dict(stable_research_id='1'*12,name='Test',port_status='research_only_adapter_or_upstream_chain_required',production_import_allowed=False,preset_promotion=False,source_sha256='b'*64,reference_sha256='c'*64,review_status='A',selected_sha256='d'*64,preserve_exact_selected_preview=True,preview_group_id='2'*12,roles=['tone'],suggested_existing_effect_roles={'tone':[{'id':1,'name':'EQ'}]},recipe_r19=p,threshold_r19=-24,training_trim_r19=0,recipe_r21=None,threshold_r21=None,trim_r21=None)
    return dict(format='skell.soundmatch.research-transfer',version=1,not_a_skellpreset_package=True,production_import_allowed=False,audited_target_commit=COMMIT,schema_audit=dict(schemaVersion=2,slotCount=16,parameterCount=16,legacySlotCount=10,registryEffectCount=2,role_mapping_only=True,existing_factory_and_parameter_ids_unchanged=True),entries=[entry],selected_preview_count=1)

def check(m,**kwargs):
    raw=json.dumps(m).encode() if isinstance(m,dict) else m
    opts=dict(expected_sha256=hashlib.sha256(raw).hexdigest(),target_commit=COMMIT,registry=REGISTRY);opts.update(kwargs)
    return validate_transfer(raw,**opts)

def test_valid():
    assert check(fixture())==dict(stages=1,renderable_research_stages=1,selected_previews=1,production_import_allowed=False)

@pytest.mark.parametrize('field,value',[('production_import_allowed',True),('not_a_skellpreset_package',False),('version',2),('selected_preview_count',0),('audited_target_commit','e'*40)])
def test_root(field,value):
    x=fixture();x[field]=value
    with pytest.raises(ValueError):check(x)

@pytest.mark.parametrize('field,value',[('production_import_allowed',True),('preset_promotion',True),('selected_sha256',None),('reference_sha256','bad'),('review_status','neither'),('threshold_r19',1),('trim_r21',-1),('recipe_r19',{}),('port_status','blocked_reference')])
def test_entry(field,value):
    x=fixture();x['entries'][0][field]=value
    with pytest.raises(ValueError):check(x)

@pytest.mark.parametrize('value',[9.1,True,float('nan'),float('inf')])
def test_recipe_range(value):
    x=fixture();x['entries'][0]['recipe_r19']['low']=value
    with pytest.raises(ValueError):check(x)

def test_duplicate_stage():
    x=fixture();x['entries'].append(copy.deepcopy(x['entries'][0]))
    with pytest.raises(ValueError):check(x)

def test_bad_role():
    x=fixture();x['entries'][0]['suggested_existing_effect_roles']['tone'][0]['name']='Other'
    with pytest.raises(ValueError):check(x)

def test_hash():
    with pytest.raises(ValueError):check(fixture(),expected_sha256='0'*64)

def test_duplicate_key():
    with pytest.raises(ValueError):check(b'{"version":1,"version":2}')
