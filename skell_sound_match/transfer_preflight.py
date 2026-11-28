"""Read-only validation of a research transfer. No production preset writer.

The expected digest and target commit must come from a trusted checkpoint,
not from the untrusted manifest. Registry is read from the audited destination.
"""
import hashlib
import json
import math
import re

BOUNDS = dict(low=(-9,9),mid=(-9,9),high=(-9,9),compression=(0,.8),
              side=(-12,12),gain=(-18,18),drive=(0,4),echo=(0,.7),
              delay_ms=(20,900),motion=(0,.7),motion_hz=(.15,8))


def _hex(v,n):
    return isinstance(v,str) and re.fullmatch('[0-9a-f]{%d}'%n,v) is not None


def _number(v,lo,hi):
    return type(v) in (int,float) and lo <= v <= hi and math.isfinite(v)


def _require(condition,message):
    if not condition:
        raise ValueError(message)


def _unique(pairs):
    obj={}
    for k,v in pairs:
        _require(k not in obj,'duplicate JSON key')
        obj[k]=v
    return obj


def validate_transfer(raw, *, expected_sha256, target_commit, registry):
    """Validate identity, schema, research restrictions and recipe bounds.

    A successful result establishes structural compatibility for the research
    adapter only, not source provenance, audio equivalence or import approval.
    """
    _require(isinstance(raw,bytes) and len(raw)<=4*1024*1024,'invalid manifest size')
    _require(_hex(expected_sha256,64) and hashlib.sha256(raw).hexdigest()==expected_sha256,'manifest digest mismatch')
    _require(_hex(target_commit,40),'invalid destination commit')
    _require(isinstance(registry,dict) and set(registry)==set(range(len(registry))) and all(isinstance(v,str) and v for v in registry.values()),'invalid registry')
    def reject_constant(v): raise ValueError('nonfinite JSON constant')
    root=json.loads(raw,object_pairs_hook=_unique,parse_constant=reject_constant)
    _require(isinstance(root,dict),'invalid root')
    _require(root.get('format')=='skell.soundmatch.research-transfer' and type(root.get('version')) is int and root['version']==1,'unknown transfer version')
    _require(root.get('not_a_skellpreset_package') is True and root.get('production_import_allowed') is False,'research restriction missing')
    _require(root.get('audited_target_commit')==target_commit,'destination commit mismatch')
    schema=root.get('schema_audit',{})
    _require(isinstance(schema,dict) and schema.get('schemaVersion')==2 and schema.get('slotCount')==16 and schema.get('parameterCount')==16 and schema.get('legacySlotCount')==10 and schema.get('registryEffectCount')==len(registry) and schema.get('role_mapping_only') is True and schema.get('existing_factory_and_parameter_ids_unchanged') is True,'destination schema mismatch')
    entries=root.get('entries')
    _require(isinstance(entries,list) and 0<len(entries)<=512,'invalid stage list')
    ids=set(); names=set(); selected=renderable=0
    for e in entries:
        _require(isinstance(e,dict),'invalid stage')
        key=e.get('stable_research_id'); name=e.get('name')
        _require(_hex(key,12) and key not in ids and isinstance(name,str) and name and name not in names,'invalid or duplicate stage identity')
        ids.add(key);names.add(name)
        _require(e.get('production_import_allowed') is False and e.get('preset_promotion') is False,'stage promotion prohibited')
        state=e.get('port_status')
        _require(state in ('blocked_reference','no_processing_needed_on_tested_stage','research_only_adapter_or_upstream_chain_required'),'unknown stage state')
        _require(_hex(e.get('reference_sha256'),64) and (_hex(e.get('source_sha256'),64) or state=='blocked_reference' and e.get('source_sha256') is None),'invalid audio hash')
        review=e.get('review_status'); h=e.get('selected_sha256')
        _require(review in ('A','B','C','neither','unreviewed_or_not_in_lab'),'invalid review status')
        if review in ('A','B','C'):
            _require(_hex(h,64) and e.get('preserve_exact_selected_preview') is True and _hex(e.get('preview_group_id'),12),'missing selected preview identity');selected+=1
        else: _require(h is None,'unexpected selected preview')
        roles=e.get('roles'); mapping=e.get('suggested_existing_effect_roles')
        _require(isinstance(roles,list) and all(isinstance(r,str) and r for r in roles) and len(set(roles))==len(roles) and isinstance(mapping,dict) and set(mapping)==set(roles),'invalid role map')
        for items in mapping.values():
            _require(isinstance(items,list) and items,'invalid role alternatives')
            for item in items:
                _require(isinstance(item,dict) and type(item.get('id')) is int and item['id'] in registry and item.get('name')==registry[item['id']],'effect role ID/name mismatch')
        for recipe,threshold,trim in [('recipe_r19','threshold_r19','training_trim_r19'),('recipe_r21','threshold_r21','trim_r21')]:
            p=e.get(recipe)
            if p is None:
                _require(e.get(threshold) is None and e.get(trim) is None,'orphan recipe settings');continue
            _require(state=='research_only_adapter_or_upstream_chain_required','unexpected blocked or identity recipe')
            _require(isinstance(p,dict) and set(p)==set(BOUNDS) and all(_number(p[k],*b) for k,b in BOUNDS.items()),'invalid correction recipe')
            _require(_number(e.get(threshold),-90,0) and _number(e.get(trim),-120,0),'invalid calibration')
        renderable+=e.get('recipe_r19') is not None
    _require(type(root.get('selected_preview_count')) is int and root['selected_preview_count']==selected,'selected count mismatch')
    return {'stages':len(entries),'renderable_research_stages':renderable,'selected_previews':selected,'production_import_allowed':False}
