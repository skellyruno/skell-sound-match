"""Resolve an exact historical recipe without conflating safe and tone winners.
Identity verification only: a returned file is not necessarily peak-safe or
approved. No audio is loaded. Caller must independently validate DSP results.
"""
import hashlib
import json
from pathlib import Path

_LABELS = {'selected': 'safe', 'tone_winner': 'tone'}


def verified_labeled_recipe(directory, case_id, label, dry_sha, target_sha):
    if (not isinstance(case_id, str) or not case_id
            or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in case_id)):
        raise ValueError('invalid case ID')
    if not isinstance(label, str) or label not in _LABELS:
        raise ValueError('unsupported recipe label')
    directory = Path(directory)
    try:
        report = json.loads((directory / (case_id + '.json')).read_text(encoding='utf-8'))
        if (report['id'] != case_id or report['source_dry_sha'] != dry_sha
                or report['source_target_sha'] != target_sha):
            return None
        selected = report[label]
        path = directory / (case_id + '_' + _LABELS[label] + '.npz')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != selected['recipe_sha256']:
            return None
        return path
    except (OSError, ValueError, KeyError, TypeError):
        return None
