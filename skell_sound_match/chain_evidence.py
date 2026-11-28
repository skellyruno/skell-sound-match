"""Conservative evidence gates for reconstructed vocal effect chains.

No DSP, source recordings, private presets or trained coefficients live here.
A passing numerical comparison is not an approval or proof of FL Studio parity.
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


@dataclass(frozen=True)
class PairProvenance:
    """Explicit recording lineage, never inferred from audio similarity alone.

    `take_id` refers to the *source performance*, not a preset or song name.
    Offset values are measured on the common sample-rate timeline. They are
    evidence supplied by a verified session/export, not automatically guessed.
    """
    source_take_id: str
    reference_take_id: str
    candidate_take_id: str
    source_sha256: str
    reference_sha256: str
    candidate_sha256: str
    source_rate: int
    reference_rate: int
    candidate_rate: int
    reference_stage: str
    candidate_stage: str
    source_offset_samples: int
    reference_offset_samples: int
    candidate_offset_samples: int
    offsets_verified: bool
    evidence_origin: str = "unverified"


def check_pair_provenance(pair: PairProvenance | None) -> tuple[str, ...]:
    """Return blockers to *exact same-take* reconstruction eligibility.

    Cross-performance style matching is still allowed experimentally, but
    cannot be promoted as a reconstructed exact effect chain via this gate.
    """
    if pair is None:
        return ("source/reference take provenance missing",)
    if not isinstance(pair, PairProvenance):
        raise TypeError("pair must be PairProvenance or None")
    reasons = []
    ids = (pair.source_take_id, pair.reference_take_id, pair.candidate_take_id)
    if not all(isinstance(x, str) and x.strip() for x in ids):
        reasons.append("source/reference take ID missing")
    elif len(set(ids)) > 1:
        reasons.append("source/reference/candidate take IDs disagree")
    digests = (pair.source_sha256, pair.reference_sha256, pair.candidate_sha256)
    if not all(isinstance(d, str) and len(d) == 64 and all(c in "0123456789abcdef" for c in d) for d in digests):
        reasons.append("source/reference/candidate file checksum missing or invalid")
    rates = (pair.source_rate, pair.reference_rate, pair.candidate_rate)
    if not all(type(rate) is int and 32000 <= rate <= 192000 for rate in rates) or len(set(rates)) > 1:
        reasons.append("source/reference/candidate sample rates disagree or invalid")
    if not pair.reference_stage or not pair.candidate_stage or pair.reference_stage != pair.candidate_stage:
        reasons.append("source/reference processing stage mismatch")
    offsets = (pair.source_offset_samples, pair.reference_offset_samples, pair.candidate_offset_samples)
    if not all(type(o) is int for o in offsets) or not isinstance(pair.offsets_verified, bool) or not pair.offsets_verified:
        reasons.append("sample offsets not independently verified")
    if pair.evidence_origin not in ("export_manifest", "verified_session"):
        reasons.append("recording provenance evidence not verified")
    return tuple(reasons)


def check_stage_order(stages: Sequence[StageEvidence]) -> tuple[str, ...]:
    """Return blockers without silently reordering an FL mixer effect chain."""
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
        if stage.state_sha256 is not None and (
            len(stage.state_sha256) != 64
            or any(c not in "0123456789abcdef" for c in stage.state_sha256)
        ):
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
    pair_provenance: PairProvenance | None = None,
    max_metric_regression: float = .25,
    minimum_later_improvement: float = .05,
    maximum_peak_db: float = -1.0,
) -> dict[str, object]:
    """Pass experimental gates separately from evidence required for promotion.

    All comparisons operate on user-provided scalar measurements; no data is
    normalized here. Caller is responsible for training-only gain calibration,
    legitimate source/reference identity and independent peak measurements.
    """
    bt, ct = _metrics(baseline_training), _metrics(candidate_training)
    bh, ch = _metrics(baseline_later), _metrics(candidate_later)
    if not all(isinstance(b, bool) for b in (source_active, reference_active, compared_same_stage,
                                              independent_performance, untouched_holdout, owner_listening_approved)):
        raise ValueError("evidence flags must be booleans")
    if not all(isfinite(v) for v in (estimated_true_peak_db, max_metric_regression,
                                     minimum_later_improvement, maximum_peak_db)):
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
    reasons.extend(check_pair_provenance(pair_provenance))
    return {
        "experimental_pass": experimental_pass,
        "eligible_for_preset_promotion": len(reasons) == 0,
        "exact_take_provenance_verified": not check_pair_provenance(pair_provenance),
        "reasons": tuple(dict.fromkeys(reasons)),
        "later_score_improvement": bh["score"] - ch["score"],
    }
