"""Bind listening preferences to a specific immutable comparison manifest.

The export is not a preset approval. Keep the manifest and audio private.
"""
import re


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('invalid SHA-256')
    return value


def bind_feedback(payload, manifest, *, expected_format):
    """Validate complete review, then bind selected/rejected hashes.

    Assumes caller independently verifies all encoded audio hashes against the
    supplied manifest. A vote of neither rejects all candidates without deleting them.
    """
    if not isinstance(payload, dict) or payload.get('format') != expected_format:
        raise ValueError('feedback format mismatch')
    entries = payload.get('entries')
    if not isinstance(entries, list) or not isinstance(manifest, list):
        raise ValueError('invalid review structure')
    by_id = {}
    for group in manifest:
        name = group['id']
        if not isinstance(name, str) or not name or name in by_id:
            raise ValueError('invalid or duplicate comparison group')
        by_id[name] = group
    if not by_id or len(entries) != len(by_id):
        raise ValueError('incomplete feedback')
    seen = set()
    result = []
    for row in entries:
        name = row['id']
        if name not in by_id or name in seen:
            raise ValueError('unknown or duplicate vote')
        seen.add(name)
        group = by_id[name]
        ref = _hash(group['stats']['ref']['sha256'])
        if row['title'] != group['title'] or _hash(row['original_sha256']) != ref:
            raise ValueError('reference identity mismatch')
        if type(row['experimental_pass']) is not bool or type(group['passed']) is not bool or row['experimental_pass'] != group['passed']:
            raise ValueError('gate metadata mismatch')
        votes = row['vote']
        letters = ('A','B','C') if 'C' in group['stats'] else ('A','B')
        if votes not in (*letters, 'neither') or not isinstance(row['notes'], str):
            raise ValueError('invalid vote or notes')
        candidates = {k: _hash(group['stats'][k]['sha256']) for k in letters}
        if len(set(candidates.values())) != len(candidates) or ref in candidates.values():
            raise ValueError('non-distinct candidates')
        if 'candidate_sha256' in row and row['candidate_sha256'] != candidates:
            raise ValueError('candidate identity mismatch')
        result.append({'id': name, 'vote': votes, 'reference_sha256': ref,
                       'candidate_sha256': candidates,
                       'selected_sha256': candidates.get(votes),
                       'rejected_sha256': [h for k,h in candidates.items() if k != votes],
                       'notes': row['notes'],
                       'experimental_pass': group['passed'],
                       'preset_promotion': False})
    return result
