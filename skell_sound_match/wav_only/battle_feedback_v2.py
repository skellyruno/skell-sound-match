"""Strict metadata-only import of current listening lab feedback."""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "skelly.sound-battle-feedback.v2"


def _string(value: Any, field: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 4096 or (not empty and not value.strip()):
        raise ValueError(f"Invalid {field}")
    return value


def _hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"Invalid {field}")
    return value


def validate_v2(payload: dict[str, Any], reference_issues: set[str] | None = None) -> dict[str, Any]:
    """Keep exact identities/hashes; never promote draft, blocked or rating-only decisions."""
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("Unrecognized battle feedback schema")
    session = _string(payload.get("session_id"), "session_id")
    previous = payload.get("previous_sessions", [])
    if not isinstance(previous, list) or len(previous) > 500:
        raise ValueError("Invalid previous_sessions")
    previous = [_string(s, "previous_session") for s in previous]
    if session in previous or len(set(previous)) != len(previous):
        raise ValueError("Duplicate or cyclic session history")
    results = payload.get("results")
    if not isinstance(results, list) or not 1 <= len(results) <= 500:
        raise ValueError("Expected 1-500 battle results")
    flags = set(reference_issues or ())
    groups, seen = [], set()
    for raw in results:
        if not isinstance(raw, dict):
            raise ValueError("Invalid battle entry")
        gid = _string(raw.get("group_id"), "group_id")
        if gid in seen:
            raise ValueError(f"Duplicate group: {gid}")
        seen.add(gid)
        preset = _string(raw.get("preset"), "preset")
        notes = _string(raw.get("notes", ""), "notes", empty=True)
        verification = _string(raw.get("verification"), "verification")
        reference = _hash(raw.get("reference_sha256"), "reference_sha256")
        reviewable, submitted = raw.get("reviewable"), raw.get("submitted")
        if type(reviewable) is not bool or type(submitted) is not bool or (submitted and not reviewable):
            raise ValueError(f"Invalid review state in {gid}")
        versions = raw.get("candidate_versions")
        if not isinstance(versions, list) or len(versions) > 3 or (reviewable and not versions):
            raise ValueError(f"Invalid candidates for {gid}")
        candidates, identities = [], set()
        for i, v in enumerate(versions):
            if not isinstance(v, dict) or v.get("letter") != chr(65 + i):
                raise ValueError(f"Invalid candidate letter in {gid}")
            identity = _string(v.get("identity"), "candidate identity")
            if identity in identities:
                raise ValueError(f"Duplicate candidate identity in {gid}")
            identities.add(identity)
            candidates.append(dict(letter=v["letter"], identity=identity,
                                   sha256=_hash(v.get("sha256"), "candidate sha256"),
                                   status=_string(v.get("status"), "candidate status")))
        labels = {v["letter"]: v["identity"] for v in candidates}
        winner, drop = raw.get("winner", ""), raw.get("eliminate", "")
        if winner not in (*labels, "tie", "") or drop not in (*labels, ""):
            raise ValueError(f"Unknown winner or elimination in {gid}")
        if drop and winner in (drop, "tie"):
            raise ValueError(f"Invalid elimination in {gid}")
        rating = raw.get("rating")
        if rating is not None and (type(rating) is not int or not 1 <= rating <= 5 or len(labels) != 1):
            raise ValueError(f"Invalid rating in {gid}")
        if (not reviewable and (winner or drop or rating is not None)) or (len(labels) == 1 and (winner or drop)):
            raise ValueError(f"Invalid vote in {gid}")
        if submitted and ((len(labels) == 1 and rating is None) or
                          (len(labels) >= 2 and not winner) or
                          (len(labels) == 3 and winner != "tie" and not drop)):
            raise ValueError(f"Incomplete submitted vote in {gid}")
        declared = [v["identity"] for v in candidates if v["letter"] != drop]
        if raw.get("survivors") != declared:
            raise ValueError(f"Survivor list does not match candidate IDs in {gid}")
        # In-progress clicks are not decisions. Do not drop a candidate until Save & next.
        if not submitted:
            winner, drop, rating = "", "", None
        survivors = [v["identity"] for v in candidates if v["letter"] != drop]
        issue = gid in flags
        if issue:
            disposition, queue, ref_status = "reference_repair_required", "repair_reference_first", "UNVERIFIED_REPAIR_REQUIRED"
        elif not reviewable:
            disposition, queue, ref_status = "blocked", "recover_review_material", "UNVERIFIED_BLOCKED"
        else:
            ref_status = "NOT_INDEPENDENTLY_VERIFIED"
            disposition = ("similarity_rated" if rating is not None else "undecided_all_survive" if winner == "tie" else
                           "provisional_winner" if winner else "no_vote")
            queue = "ready_for_challenger" if submitted and len(survivors) == 2 else "refine_before_next_vote"
        groups.append(dict(group_id=gid, preset=preset, reviewable=reviewable, submitted=submitted,
                           rating=rating, winner_letter=winner, winner_identity=labels.get(winner),
                           eliminated_letter=drop, eliminated_identity=labels.get(drop), survivors=survivors,
                           candidate_versions=candidates, reference_sha256=reference, verification=verification,
                           notes=notes, disposition=disposition, queue_state=queue,
                           reference_status=ref_status, listening_approved=False))
    if flags - seen:
        raise ValueError("Reference issue flag does not match any battle: " + ", ".join(sorted(flags - seen)))
    return dict(schema="skelly.sound-battle-plan.v1", source_schema=SCHEMA, session_id=session,
                previous_sessions=previous, groups=groups, summary=dict(
                    groups=len(groups), provisional_winners=sum(g["disposition"] == "provisional_winner" for g in groups),
                    reference_repair=sum(g["queue_state"] == "repair_reference_first" for g in groups),
                    ties=sum(g["winner_letter"] == "tie" for g in groups),
                    ready_for_challenger=sum(g["queue_state"] == "ready_for_challenger" for g in groups),
                    rated=sum(g["rating"] is not None for g in groups), blocked=sum(not g["reviewable"] for g in groups)))
