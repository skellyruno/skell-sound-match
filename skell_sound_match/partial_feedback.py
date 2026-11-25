"""Validate an explicitly partial R19 review without inferring unsubmitted votes."""
from .listening_feedback import bind_feedback


def bind_partial_feedback(payload, manifest):
    if not isinstance(payload, dict) or payload.get('format') != 'SKELLY_SOUND_MATCH_R19_FEEDBACK':
        raise ValueError('feedback format mismatch')
    entries = payload.get('entries')
    if not isinstance(entries, list) or not isinstance(manifest, list) or not manifest:
        raise ValueError('invalid review structure')
    groups = {}
    for group in manifest:
        name = group['id']
        if not isinstance(name, str) or not name or name in groups:
            raise ValueError('invalid or duplicate manifest group')
        groups[name] = group
    ids = [row['id'] for row in entries]
    if len(set(ids)) != len(ids) or any(k not in groups for k in ids):
        raise ValueError('unknown or duplicate review group')
    partial = len(ids) < len(groups)
    if type(payload.get('partial')) is not bool or payload['partial'] != partial:
        raise ValueError('inconsistent partial flag')
    selected = []
    for k in ids:
        g = groups[k]
        keys = {x for x in g['clips'] if x != 'ref'}
        if keys not in ({'A', 'B'}, {'A', 'B', 'C'}):
            raise ValueError('invalid candidate set')
        selected.append({'id': k, 'title': g['name'], 'passed': True, 'stats': g['clips']})
    if any('candidate_sha256' not in row for row in entries):
        raise ValueError('candidate hashes required')
    votes = bind_feedback(payload, selected, expected_format=payload['format']) if ids else []
    return {'votes': votes, 'unreviewed_ids': [k for k in groups if k not in ids], 'partial': partial}
