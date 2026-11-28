import copy
import pytest
from skell_sound_match.recipe_export import validate_recipe,create_integration_plan,RecipeError

BASE={'schema':'skell.sound-match.recipe','version':1,'id':'safe', 'stages':[{'id':'main','processors':[
  {'slot':1,'name':'Synthetic Compressor','parameters':{'attack':{'value':12.9,'unit':'ms','status':'verified','origin':'screenshot'}}}
]}]}
MAP={'Synthetic Compressor':{'id':'native.comp.1','verified':True,'parameter_map':{'attack':{'id':'s1_attack','unit':'ms'}}}}

def test_mapping_safe_verified_works():
    p=create_integration_plan(BASE,'skell-preset',MAP)
    assert p['ready'] and p['processors'][0]['parameters']['s1_attack']['value']==12.9

def test_unapproved_does_not_become_ready():
    r=copy.deepcopy(BASE);r['not_approved_for_native_recall']=True
    assert not create_integration_plan(r,'skell-preset',MAP)['ready']

def test_mapping_must_be_verified():
    m=copy.deepcopy(MAP); m['Synthetic Compressor'].pop('verified')
    assert not create_integration_plan(BASE,'skell-preset',m)['ready']

def test_native_id_needs_verified_unit():
    m=copy.deepcopy(MAP); m['Synthetic Compressor']['parameter_map']['attack']['unit']='s'
    assert not create_integration_plan(BASE,'skell-preset',m)['ready']

def test_no_raw_to_native_parameter():
    r=copy.deepcopy(BASE);r['stages'][0]['processors'][0]['parameters']['attack']={'value':503,'unit':'raw','origin':'fst_raw','status':'verified'}
    m=copy.deepcopy(MAP);m['Synthetic Compressor']['parameter_map']['attack']['unit']='raw'
    assert not create_integration_plan(r,'skell-preset',m)['ready']

def test_unmapped_effect_state_blocks():
    r=copy.deepcopy(BASE);r['stages'][0]['processors'][0]['parameters']={}
    assert not create_integration_plan(r,'skell-preset',MAP)['ready']

def test_duplicated_native_id_rejected():
    r=copy.deepcopy(BASE);second=copy.deepcopy(r['stages'][0]['processors'][0]);second['slot']=2
    r['stages'][0]['processors'].append(second)
    assert not create_integration_plan(r,'skell-preset',MAP)['ready']

def test_invalid_nonfinite_and_missing_value_rejected():
    for v in [float('nan'),float('inf'),None,[]]:
        r=copy.deepcopy(BASE);r['stages'][0]['processors'][0]['parameters']['attack']['value']=v
        with pytest.raises(RecipeError):validate_recipe(r)

def test_actual_recipes_both_remain_blocked():
    from pathlib import Path
    from skell_sound_match.recipe_export import read_recipe
    root=Path(__file__).resolve().parents[1]
    for name in ['deuce','alchemist']:
        r=read_recipe(root/'recipes'/f'{name}.json')
        for dest in ['skell-preset','skell-adliblab']:
            p=create_integration_plan(r,dest)
            assert not p['ready'] and p['blockers']
