"""Verify immutable search checkpoints before skipping work on resume.
Only the completed report and its digest-matched recipe count as complete.
"""
import hashlib
import json
import math
from pathlib import Path


def verified_report(directory, case_id, dry_sha, target_sha):
    """Return a validated report, or None for a missing/invalid checkpoint.

    Rejected checkpoints must be preserved or quarantined before recomputing.
    No private audio is read by this helper.
    """
    if not isinstance(case_id, str) or not case_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in case_id):
        raise ValueError('invalid case ID')
    d = Path(directory)
    try:
        report = json.loads((d / (case_id + '.json')).read_text(encoding='utf-8'))
        if report['id'] != case_id or report['source_dry_sha'] != dry_sha or report['source_target_sha'] != target_sha:
            return None
        selected = report['selected']
        n = report['trial_count']
        if type(n) is not int or n <= 0 or n != len(report['trials']):
            return None
        if hashlib.sha256((d / (case_id + '_safe.npz')).read_bytes()).hexdigest() != selected['recipe_sha256']:
            return None
        vals = [selected['heldout']['score'], selected['heldout48_resampled44']['score'], selected['peak44_dbTP'], selected['peak48_dbTP'], selected['stress44_dbTP'], selected['stress48_dbTP']]
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vals) or min(vals[:2]) < 0:
            return None
        safe = vals[2] <= -1 and vals[3] <= -1 and vals[4] <= 0 and vals[5] <= 0
        if selected['safe'] is not safe:
            return None
        return report
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
