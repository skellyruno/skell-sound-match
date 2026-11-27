"""Aggregate explicitly verified, both-rate research results without inflating counts.

Callers are responsible for verifying report/recipe hashes and source identity
before passing records. This is a numerical research gate, not listening,
independent-performance or real-time plugin approval.
"""
import math
from numbers import Real


def _number(value):
    return (isinstance(value, Real) and not isinstance(value, bool)
            and math.isfinite(value))


def safe_worst_score(record):
    """Return the worst of the two scores if all four peak gates pass."""
    try:
        scores = [record['score44'], record['score48']]
        peaks = [record[k] for k in ('peak44_dbTP', 'peak48_dbTP',
                                    'stress44_dbTP', 'stress48_dbTP')]
    except (KeyError, TypeError):
        return None
    if not all(_number(v) for v in scores + peaks) or min(scores) < 0:
        return None
    if max(peaks[:2]) > -1 or max(peaks[2:]) > 0:
        return None
    return max(scores)


def summarize_milestone(expected_ids, records, ceiling=1.5, fraction=.70):
    """Count unique expected pairs, choosing their best peak-safe result.

    Missing or unsafe-only cases never qualify and stay in the denominator.
    Multiple candidate versions of one sound count once. The threshold changes
    neither the scores nor the safety gates. All input records must have been
    validated by the caller; reported-only results must not be included.
    """
    ids = list(expected_ids)
    if (not ids or any(not isinstance(x, str) or not x for x in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError('expected IDs must be unique nonempty strings')
    if (not _number(ceiling) or ceiling < 0 or not _number(fraction)
            or not 0 < fraction <= 1):
        raise ValueError('invalid ceiling or target fraction')
    best = {}
    known = set(ids)
    for r in records:
        if r.get('id') not in known:
            raise ValueError('unexpected case ID')
        score = safe_worst_score(r)
        if score is None:
            continue
        key = r['id']
        if key not in best or score < best[key]:
            best[key] = score
    passes = [i for i in ids if i in best and best[i] <= ceiling]
    required = math.ceil(len(ids) * fraction)
    return dict(total=len(ids), ceiling=ceiling, required=required,
                count=len(passes), fraction=len(passes)/len(ids),
                qualifying=passes, remaining=max(0, required-len(passes)),
                missing_safe=[i for i in ids if i not in best],
                best_safe_scores=best)
