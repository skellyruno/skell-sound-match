"""Evidence-backed plans for eventual Skell Preset / AdlibLab preset conversion.

A plan is NOT a native preset. Unsupported or unverified mappings are blockers,
never silently dropped. No parameter index is invented or renumbered.
"""
from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

SCHEMA = 'skell.sound-match.recipe'
TARGETS = ('skell-preset', 'skell-adliblab')

class RecipeError(ValueError):
    pass


def validate_recipe(data: dict) -> dict:
    if not isinstance(data, dict) or data.get('schema') != SCHEMA or data.get('version') != 1:
        raise RecipeError('Unexpected recipe schema/version')
    if not isinstance(data.get('id'), str) or not data['id'].strip():
        raise RecipeError('Recipe ID must be a nonempty string')
    stages = data.get('stages')
    if not isinstance(stages, list) or not stages:
        raise RecipeError('Recipe must contain stages')
    result = deepcopy(data)
    names = set()
    for stage in stages:
        if not isinstance(stage, dict) or not isinstance(stage.get('id'), str) or not stage['id'].strip():
            raise RecipeError('Invalid stage ID')
        if stage['id'] in names:
            raise RecipeError('Duplicate stage ID')
        names.add(stage['id'])
        seen_slots = set()
        slots=stage.get('processors', [])
        if not isinstance(slots, list):
            raise RecipeError('Processors must be a list')
        for fx in slots:
            if not isinstance(fx, dict) or type(fx.get('slot')) is not int or fx['slot'] <= 0:
                raise RecipeError('Effect slots must be positive integers')
            if fx['slot'] in seen_slots:
                raise RecipeError('Duplicate processor slot')
            seen_slots.add(fx['slot'])
            if not isinstance(fx.get('name'), str) or not fx['name'].strip():
                raise RecipeError('Missing processor name')
            params=fx.get('parameters', {})
            if not isinstance(params, dict):
                raise RecipeError('Parameters must be an object')
            for key, param in params.items():
                if not isinstance(key, str) or not key.strip():
                    raise RecipeError('Empty parameter name')
                if not isinstance(param, dict) or param.get('status') not in ('verified', 'estimated', 'unknown'):
                    raise RecipeError('Missing parameter provenance for '+key)
                if not isinstance(param.get('unit'), str) or not param['unit'].strip():
                    raise RecipeError('Parameter unit must be explicit')
                if not isinstance(param.get('origin'), str) or not param['origin']:
                    raise RecipeError('Parameter origin must be explicit')
                value=param.get('value')
                if param.get('status') == 'unknown' and value is not None:
                    raise RecipeError('Unknown parameter must not have a value')
                if param.get('status') != 'unknown' and value is None:
                    raise RecipeError('Known parameter cannot be missing a value')
                if isinstance(value, bool) or isinstance(value, (list, dict)):
                    raise RecipeError('Parameter value must be a scalar')
                if isinstance(value, (float, int)) and not math.isfinite(value):
                    raise RecipeError('Parameter value must be finite')
                if param.get('origin') == 'fst_raw' and param['unit'] != 'raw':
                    raise RecipeError('Do not automatically convert raw FST values to physical units')
                if param.get('status') == 'verified' and param.get('origin') == 'audio_estimate':
                    raise RecipeError('Audio-only estimates cannot be marked verified')
    return result


def create_integration_plan(recipe: dict, destination: str,
                            implemented_processors: dict[str, dict] | None = None) -> dict:
    """Only report READY after *all* effects/parameters have verified native mappings.

    A mapping needs:
        id: nonempty stable native effect identifier
        verified: True (DSP and units checked against the target repository)
        parameter_map: {source_name: {'id': 'actual_stable_automation_id',
                                      'unit': 'same_physical_unit'}}

    Native recipe approval is separate from mapping readiness; a historical
    match labelled unapproved can never become ready merely by mapping IDs.
    """
    data = validate_recipe(recipe)
    if destination not in TARGETS:
        raise RecipeError('Unsupported destination')
    mapping = implemented_processors or {}
    if not isinstance(mapping, dict):
        raise RecipeError('Native mappings must be an object')
    plan = {'schema': 'skell.integration.plan', 'version': 1, 'recipe': data['id'],
            'destination': destination, 'ready': False, 'processors': [], 'blockers': []}
    if data.get('not_approved_for_native_recall', False):
        plan['blockers'].append('Recipe is not approved for native recall')
    used_ids=set()
    for stage in data['stages']:
        for fx in sorted(stage.get('processors', []), key=lambda item: item['slot']):
            record={'stage':stage['id'],'slot':fx['slot'], 'source_effect':fx['name'],'status':'blocked'}
            if fx.get('empty'):
                record['status']='empty'
                plan['processors'].append(record)
                continue
            label=f"{stage['id']}:{fx['slot']}:{fx['name']}"
            if fx['name'] not in mapping:
                plan['blockers'].append(f'Missing native implementation or verified mapping for {label}')
                plan['processors'].append(record)
                continue
            native=mapping[fx['name']]
            if not isinstance(native,dict) or native.get('verified') is not True or not isinstance(native.get('id'),str) or not native['id'].strip():
                plan['blockers'].append(f'Native implementation not verified for {label}')
                plan['processors'].append(record)
                continue
            ids=native.get('parameter_map')
            if not isinstance(ids,dict):
                plan['blockers'].append(f'No verified native parameter map for {label}')
                plan['processors'].append(record)
                continue
            mapped={}
            complete=True
            for name,p in fx.get('parameters', {}).items():
                if p['status']!='verified':
                    plan['blockers'].append(f'Unverified parameter {label}.{name}')
                    complete=False
                    continue
                entry=ids.get(name)
                if not isinstance(entry,dict) or not isinstance(entry.get('id'),str) or not entry['id'].strip() or entry.get('unit') != p['unit']:
                    plan['blockers'].append(f'Unverified native parameter ID or unit for {label}.{name}')
                    complete=False
                    continue
                if p['unit']=='raw':
                    plan['blockers'].append(f'Raw plugin state cannot be converted automatically: {label}.{name}')
                    complete=False
                    continue
                target_id=entry['id']
                if target_id in used_ids:
                    plan['blockers'].append(f'Native automation ID reused in multiple slots: {target_id}')
                    complete=False
                    continue
                used_ids.add(target_id)
                mapped[target_id]={'value':p['value'],'unit':p['unit'],'source':name}
            # An effect with NO recorded parameters also needs explicit validated behavior.
            if not fx.get('parameters') and native.get('state_equivalent') is not True:
                plan['blockers'].append(f'Unknown effect state cannot be translated: {label}')
                complete=False
            record['target_id']=native['id']
            record['parameters']=mapped
            record['status']='mapped' if complete else 'partial_mapping'
            plan['processors'].append(record)
    plan['ready']=not plan['blockers'] and all(p['status'] in ('mapped','empty') for p in plan['processors'])
    return plan


def read_recipe(path: str | Path):
    return validate_recipe(json.loads(Path(path).read_text(encoding='utf-8')))
