"""Reference-grounded onset-edit audit for *offline* vocal-match experiments.

Compares the proposed output with an immutable champion and a same-take
reference. Reports changed intervals, reference-active error, and per-event
tradeoffs. This module never rewrites audio or approves a new champion.

The optional dry source is evidence for consonant-loss risks, never a free
license to optimize processing on the reference at render time.
"""
from __future__ import annotations

from typing import Any
import numpy as np
from scipy import ndimage


def _audio(value: np.ndarray, sr: int) -> np.ndarray:
    x = np.asarray(value, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] not in (1, 2) or x.shape[0] < sr // 4:
        raise ValueError('Audio must be >= 250 ms of mono/stereo frames')
    if sr < 16000 or sr > 192000 or not np.isfinite(x).all():
        raise ValueError('Invalid sample rate or nonfinite audio')
    return x


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def _db(value: float) -> float:
    return float(20 * np.log10(max(value, 1e-12)))


def _errors(reference: np.ndarray, champion: np.ndarray, candidate: np.ndarray, indices: np.ndarray) -> dict[str, float]:
    if not np.any(indices):
        return {'champion_rms_error_dbfs': -240.0, 'trial_rms_error_dbfs': -240.0, 'trial_minus_champion_db': 0.0}
    old = _db(_rms((reference-champion)[indices]))
    new = _db(_rms((reference-candidate)[indices]))
    return {'champion_rms_error_dbfs': round(old, 4),
            'trial_rms_error_dbfs': round(new, 4),
            'trial_minus_champion_db': round(new-old, 4)}


def review_onset_edit(reference: np.ndarray, champion: np.ndarray, trial: np.ndarray,
                      sr: int, *, dry: np.ndarray | None = None,
                      edit_threshold_dbfs: float = -110.0,
                      active_threshold_dbfs: float = -45.0,
                      merge_gap_ms: float = 8.0,
                      event_margin_ms: float = 100.0,
                      min_event_ms: float = 1.5) -> dict[str, Any]:
    """Return an audit report, without modifying or creating an audio file.

    Negative trial-minus-champion error means an objective improvement. Only
    time-aligned SAME-TAKE material is valid. A reference-aware score is a
    diagnostic, not a model for inference on a new recording.
    """
    ref, base, test = (_audio(v, sr) for v in (reference, champion, trial))
    if ref.shape != base.shape or ref.shape != test.shape:
        raise ValueError('Inputs must be sample aligned with identical shapes')
    if dry is not None:
        raw = _audio(dry, sr)
        if raw.shape != ref.shape:
            raise ValueError('Dry and processed audio must be sample aligned')
    else:
        raw = None
    for p in (edit_threshold_dbfs, active_threshold_dbfs, merge_gap_ms, event_margin_ms, min_event_ms):
        if not np.isfinite(p):
            raise ValueError('Nonfinite audit settings')
    if not (-140 <= edit_threshold_dbfs <= -45 and -100 <= active_threshold_dbfs <= -10):
        raise ValueError('Unsafe thresholds')
    if not (0 <= merge_gap_ms <= 200 and 0 <= event_margin_ms <= 500 and .1 <= min_event_ms <= 100):
        raise ValueError('Unsafe event interval settings')

    delta = np.max(np.abs(test - base), axis=1)
    mask = delta > 10 ** (edit_threshold_dbfs / 20)
    starts = np.flatnonzero(np.diff(np.r_[False, mask, False].astype(np.int8)) == 1)
    ends = np.flatnonzero(np.diff(np.r_[False, mask, False].astype(np.int8)) == -1)
    raw_regions = []
    gap = round(merge_gap_ms * sr / 1000)
    for lo, hi in zip(starts, ends):
        if raw_regions and lo - raw_regions[-1][1] <= gap:
            raw_regions[-1][1] = int(hi)
        else:
            raw_regions.append([int(lo), int(hi)])
    min_len = max(1, round(min_event_ms * sr / 1000))
    raw_regions = [(lo, hi) for lo, hi in raw_regions if hi-lo >= min_len]

    # Reference-active masks do not come from the candidate, thus loudness
    # differences cannot make the definition of active speech drift.
    mono = ref.mean(axis=1)
    active_rms = np.sqrt(np.maximum(ndimage.uniform_filter1d(mono**2,
                         size=max(1, round(sr * .020)), mode='nearest'), 0))
    active = active_rms > 10 ** (active_threshold_dbfs / 20)
    whole_mask = np.ones(len(ref), dtype=bool)
    changes = []
    for lo, hi in raw_regions:
        margin = round(event_margin_ms * sr / 1000)
        a,b = max(0, lo-margin), min(len(ref), hi+margin)
        loc = slice(a, b)
        envelope = (np.arange(a,b) >= lo) & (np.arange(a,b) < hi)
        metrics = _errors(ref[loc], base[loc], test[loc], np.ones(b-a,dtype=bool))
        active_edit = active[lo:hi]
        baseline_loudness = _db(_rms(base[lo:hi]))
        trial_loudness = _db(_rms(test[lo:hi]))
        entry = {'start_seconds': round(lo/sr, 5), 'end_seconds': round(hi/sr, 5),
                 'edited_duration_ms': round(1000*(hi-lo)/sr, 3),
                 'reference_active_fraction_in_edit': round(float(np.mean(active_edit)), 4),
                 'edited_trial_minus_base_rms_db': round(trial_loudness-baseline_loudness, 3),
                 'local_reference_error': metrics}
        if raw is not None:
            entry['dry_rms_in_edit_dbfs'] = round(_db(_rms(raw[lo:hi])), 3)
            entry['dry_peak_in_edit_dbfs'] = round(_db(float(np.max(np.abs(raw[lo:hi])))), 3)
        # Strong local gain is not proof of audible superiority; if within
        # 0.5 dB, treat it as inconclusive and avoid triumphalist labeling.
        entry['local_evidence'] = ('improvement' if metrics['trial_minus_champion_db'] < -.5
                                   else 'regression' if metrics['trial_minus_champion_db'] > .5
                                   else 'inconclusive')
        changes.append(entry)

    # Whole-clip time coverage is measured before interval merging; the union
    # of merged event intervals is reported separately.
    active_err = _errors(ref, base, test, active)
    silent_err = _errors(ref, base, test, ~active)
    full_err = _errors(ref, base, test, whole_mask)
    return {
        'status': 'audit_only_not_sound_approval',
        'sample_rate': sr, 'frame_count': len(ref), 'channel_count': ref.shape[1],
        'modified_sample_fraction': round(float(mask.mean()), 6),
        'modified_sample_duration_seconds': round(float(mask.sum()/sr), 4),
        'event_count': len(changes), 'events': changes,
        'whole_clip_reference_error': full_err,
        'reference_active_error': active_err,
        'reference_quiet_error': silent_err,
        'active_fraction': round(float(active.mean()), 4),
        'recommended_decision': ('keep_current_champion_until_blind_listening'
                                 if mask.mean() < .08 and active_err['trial_minus_champion_db'] > -.75
                                 else 'requires_blind_listening_and_unseen_take'),
        'limitations': ['The event positions and metrics come from the same reference recording.',
                        'Audio differences outside short edits can dominate perceived character.',
                        'No automatic champion promotion or inference from reference audio is permitted.']
    }