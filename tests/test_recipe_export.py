import copy
import pytest
from skell_sound_match.recipe_export import validate_recipe, create_integration_plan, RecipeError

BASE={'schema':'skell.sound-match.recipe','version':1,'id':'synthetic-test','stages':[{'id':'rec','processors':[{'slot':1,'name':'Synthetic Compressor','parameters':{'attack':{'value':13,'unit':'ms','status':'verified','origin':'screenshot'}}}]}]}

def test_valid():
    assert validate_recipe(BASE)==BASE

def test_missing_implementation_explicit_blocker():
    p=create_integration_plan(BASE,'skell-preset')
    assert not p['ready'] and p['blockers']

def test_mapping_respects_automation_ids():
    p=create_integration_plan(BASE,'skell-preset',{'Synthetic Compressor':{'id':'skell.comp','parameter_map':{'attack':'skell.comp.attack_ms'}}})
    assert p['ready'] and p['processors'][0]['parameters']['skell.comp.attack_ms']['value']==13

def test_fst_raw_not_percent():
    v=copy.deepcopy(BASE)
    v['stages'][0]['processors'][0]['parameters']['attack']={'value':503,'unit':'%','status':'verified','origin':'fst_raw'}
    with pytest.raises(RecipeError):validate_recipe(v)

def test_invalid_and_duplicate():
    bad=copy.deepcopy(BASE);bad['stages'][0]['processors'].append(copy.deepcopy(bad['stages'][0]['processors'][0]))
    with pytest.raises(RecipeError):validate_recipe(bad)
    with pytest.raises(RecipeError):create_integration_plan(BASE,'unsupported')

def test_audio_estimate_cannot_be_verified():
    v=copy.deepcopy(BASE);v['stages'][0]['processors'][0]['parameters']['attack']['origin']='audio_estimate'
    with pytest.raises(RecipeError):validate_recipe(v)

def test_does_not_mutate_input():
    b=copy.deepcopy(BASE);validate_recipe(BASE);create_integration_plan(BASE,'skell-adliblab')
    assert BASE==b
