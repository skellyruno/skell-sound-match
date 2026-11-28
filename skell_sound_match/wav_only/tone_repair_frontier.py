"""Repair scheduling for R62's unchanged metrics; research only, never promotion.
Call on training/selection metrics, never the final holdout. Keep original render
and recipe IDs outside this queue. A retained tonal seed is not release approval.
"""
from math import isfinite

KEYS = ('score', 'tone', 'env', 'wave_db', 'side')

def validate(m):
    if any(k not in m or not isfinite(m[k]) for k in KEYS):
        raise ValueError('incomplete or nonfinite metrics')
    if any(m[k] < 0 for k in ('score', 'tone', 'env', 'side')):
        raise ValueError('negative error')

def frontier(records, limit=8):
    """Keep distinct tonal, composite, envelope, side and phase repair seeds.
    Each record is (immutable recipe ID, metrics). No final-holdout data allowed.
    Extremes are protected before filling the remaining budget with Pareto seeds.
    """
    if not isinstance(limit, int) or limit < len(KEYS):
        raise ValueError('limit must cover all five metric extremes')
    rows = list(records)
    if len({k for k, _ in rows}) != len(rows):
        raise ValueError('duplicate recipe ID')
    for k, m in rows:
        if not isinstance(k, str) or not k:
            raise ValueError('invalid recipe ID')
        validate(m)
    if not rows:
        return []
    selected = []
    for field in ('tone', 'score', 'env', 'side', 'wave_db'):
        k, _ = min(rows, key=lambda r: (r[1][field], r[1]['score'], r[0]))
        if k not in selected:
            selected.append(k)
    def dominates(a, b):
        return all(a[k] <= b[k] for k in KEYS) and any(a[k] < b[k] for k in KEYS)
    pareto = [(k,m) for k,m in rows if not any(dominates(n,m) for _,n in rows)]
    for k, _ in sorted(pareto, key=lambda r: (r[1]['score'], r[1]['tone'], r[0])):
        if k not in selected and len(selected) < limit:
            selected.append(k)
    return selected

def preserves_tone(repaired, seed, installed, tolerance=.025):
    """Repair must preserve the better tone, even when seed composite was worse."""
    for m in (repaired, seed, installed):
        validate(m)
    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError('invalid tolerance')
    return repaired['tone'] <= min(seed['tone'], installed['tone']) + tolerance

def target_reached(m):
    validate(m)
    return m['score'] <= 1.0
