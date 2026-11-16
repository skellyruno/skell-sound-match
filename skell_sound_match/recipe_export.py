"""Portable, evidence-backed sound-match recipe plans for future Skell plugins.

This module does not claim that proprietary effect states are equivalent to
Skell DSP. Unsupported effects stay blockers rather than silently disappearing.
"""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path

SCHEMA = 'skell.sound-match.recipe'

class RecipeError(ValueError):
    pass

def validate_recipe(data: dict) -> dict:
    if not isinstance(data, dict) or data.get('schema') != SCHEMA or data.get('version') != 1:
        raise RecipeError('Unexpected recipe schema/version')
    stages = data.get('stages')
    if not isinstance(stages, list) or not stages:
        raise RecipeError('Recipe must contain stages')
    result = deepcopy(data)
    names = set()
    for stage in stages:
        if not isinstance(stage, dict) or not isinstance(stage.get('id'), str) or not stage['id']:
            raise RecipeError('Invalid stage ID')
        if stage['id'] in names:
            raise RecipeError('Duplicate stage ID')
        names.add(stage['id'])
        seen_slots = set()
        for fx in stage.get('processors', []):
            if not isinstance(fx, dict) or type(fx.get('slot')) is not int or fx['slot'] <= 0:
                raise RecipeError('Effect slots must be positive integers')
            if fx['slot'] in seen_slots:
                raise RecipeError('Duplicate processor slot')
            seen_slots.add(fx['slot'])
            if not isinstance(fx.get('name'), str) or not fx['name']:
                raise RecipeError('Missing processor name')
            for key, param in fx.get('parameters', {}).items():
                if not isinstance(param, dict) or param.get('status') not in ('verified', 'estimated', 'unknown'):
                    raise RecipeError('Missing parameter provenance for '+key)
                if not isinstance(param.get('unit'), str) or not param['unit']:
                    raise RecipeError('Parameter unit must be explicit')
                if param.get('status') == 'unknown' and param.get('value') is not None:
                    raise RecipeError('Unknown parameter must not have a numeric value')
                if param.get('origin') == 'fst_raw' and param['unit'] != 'raw':
                    raise RecipeError('Do not automatically convert raw FST values to physical units')
                if param.get('status') == 'verified' and param.get('origin') == 'audio_estimate':
                    raise RecipeError('Audio-only estimates cannot be marked verified')
    return result

def create_integration_plan(recipe: dict, destination: str, implemented_processors: dict[str, dict] | None = None) -> dict:
    """Create an auditable plan; do not invent native automation IDs or DSP behavior.

    implemented_processors should map exact source effect names to corresponding
    verified native processors, e.g. {'Fruity Compressor': {'id': 'skell.comp', 'parameter_map': ...}}.
    An empty mapping is safe: all nonempty processors become integration blockers.
    """
    data = validate_recipe(recipe)
    if destination not in ('skell-preset', 'skell-adliblab'):
        raise RecipeError('Unsupported destination')
    mapping = implemented_processors or {}
    plan = {'schema':'skell.integration.plan', 'version':1, 'recipe':data['id'], 'destination':destination,
            'ready':True, 'processors':[], 'blockers':[]}
    for stage in data['stages']:
        for fx in stage.get('processors', []):
            record={'stage':stage['id'],'slot':fx['slot'],'source_effect':fx['name'],'status':'blocked'}
            if fx.get('empty'):
                record['status']='empty'
            elif fx['name'] not in mapping:
                plan['blockers'].append(f"Missing native implementation or verified mapping for {stage['id']}:{fx['name']}")
            else:
                native=mapping[fx['name']]
                ids=native.get('parameter_map', {})
                mapped={}
                for name,p in fx.get('parameters', {}).items():
                    if p['status']!='verified':
                        plan['blockers'].append(f"Unverified parameter {fx['name']}.{name}")
                    elif name not in ids:
                        plan['blockers'].append(f"No native automation ID for {fx['name']}.{name}")
                    else:
                        mapped[ids[name]]={'value':p.get('value'),'unit':p['unit'],'source':name}
                if mapped and not any(x.startswith('No native automation ID for '+fx['name']+'.') for x in plan['blockers']):
                    record['status']='partial_mapping';record['target_id']=native.get('id');record['parameters']=mapped
            plan['processors'].append(record)
    plan['ready']=len(plan['blockers'])==0
    return plan

def read_recipe(path: str | Path):
    return validate_recipe(json.loads(Path(path).read_text(encoding='utf-8')))
