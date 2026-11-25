"""Conservative evidence gates for reconstructed vocal effect chains.
A numerical pass is never proof of FL Studio parity or owner approval.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence

METRICS = ("tone_db", "dynamics_db", "width_db", "band_width")

@dataclass(frozen=True)
class StageEvidence:
    slot: int
    kind: str
    state_sha256: str | None = None
    available: bool = False

def check_stage_order(stages: Sequence[StageEvidence]) -> tuple[str, ...]:
    """Validate without silently reordering or inventing an effect state."""
    blockers: list[str] = []
    previous = -1
    for stage in stages:
        if not isinstance(stage.slot, int) or stage.slot < 0:
            blockers.append("invalid slot index")
        if stage.slot <= previous:
            blockers.append("duplicate or out-of-order mixer slot")
        previous = stage.slot
        if not stage.kind or not isinstance(stage.kind, str):
            blockers.append("missing effect kind")
        if stage.state_sha256 is not None and (len(stage.state_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in stage.state_sha256)):
            blockers.append("invalid state checksum")
        if stage.available and stage.state_sha256 is None:
            blockers.append("available stage has no verified saved state")
        if not stage.available:
            blockers.append(f"unavailable stage at slot {stage.slot}")
    return tuple(dict.fromkeys(blockers))

def _metrics(x: Mapping[str, float]) -> dict[str, float]:
    values: dict[str, float] = {}
    for k in ("score", *METRICS):
        if k not in x or not isinstance(x[k], (int, float)) or not isfinite(x[k]) or x[k] < 0:
            raise ValueError(f"invalid metric: {k}")
        values[k] = float(x[k])
    return values

def evaluate_evidence(
    baseline_training: Mapping[str, float],
    candidate_training: Mapping[str, float],
    baseline_later: Mapping[str, float],
    candidate_later: Mapping[str, float],
    *,
    estimated_true_peak_db: float,
    source_active: bool,
    reference_active: bool,
    compared_same_stage: bool,
    independent_performance: bool = False,
    untouched_holdout: bool = False,
    owner_listening_approved: bool = False,
    max_metric_regression: float = .25,
    minimum_later_improvement: float = .05,
    maximum_peak_db: float = -1.0,
) -> dict[str, object]:
    """Separate experimental matching gates from permission to promote a preset.

    The caller must verify provenance and use training-only gain calibration.
    """
    bt, ct = _metrics(baseline_training), _metrics(candidate_training)
    bh, ch = _metrics(baseline_later), _metrics(candidate_later)
    if not all(isinstance(b, bool) for b in (source_active, reference_active,
                compared_same_stage, independent_performance, untouched_holdout,
                owner_listening_approved)):
        raise ValueError("evidence flags must be booleans")
    if not all(isfinite(v) for v in (estimated_true_peak_db,
        max_metric_regression, minimum_later_improvement, maximum_peak_db)):
        raise ValueError("nonfinite gate")
    if max_metric_regression < 0 or minimum_later_improvement < 0 or maximum_peak_db > 0:
        raise ValueError("invalid gate")
    reasons = []
    if not source_active or not reference_active:
        reasons.append("inactive reference or source partition")
    if any(ct[k] > bt[k] + max_metric_regression for k in METRICS):
        reasons.append("training metric regression")
    if any(ch[k] > bh[k] + max_metric_regression for k in METRICS):
        reasons.append("later-section metric regression")
    if not ct["score"] < bt["score"]:
        reasons.append("training score not improved")
    if not ch["score"] <= bh["score"] - minimum_later_improvement:
        reasons.append("later-section improvement insufficient")
    if estimated_true_peak_db > maximum_peak_db:
        reasons.append("peak ceiling exceeded")
    experimental_pass = len(reasons) == 0
    if not compared_same_stage:
        reasons.append("reference stage unverified")
    if not independent_performance:
        reasons.append("no independent-performance validation")
    if not untouched_holdout:
        reasons.append("holdout previously evaluated or unverified")
    if not owner_listening_approved:
        reasons.append("owner listening approval missing")
    return {
        "experimental_pass": experimental_pass,
        "eligible_for_preset_promotion": len(reasons) == 0,
        "reasons": tuple(dict.fromkeys(reasons)),
        "later_score_improvement": bh["score"] - ch["score"],
    }
