"""Validate private battle picks and prepare a safe next-round work queue.

Consumes owner-exported *metadata only*, not audio or private model files.
A winner is a relative listening preference, NEVER approval of a sound match.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "skelly.sound-battle-feedback.v1"
PLAN_SCHEMA = "skelly.sound-battle-plan.v1"


def _required_string(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()) or len(value) > 4096:
        raise ValueError(f"Invalid {field}")
    return value


def validate_and_plan(payload: dict[str, Any], reference_issues: set[str] | None = None) -> dict[str, Any]:
    """Strictly validate feedback, resolve hidden labels, and preserve all ties.

    reference_issues requires explicit evidence from an audit/user report; it is
    not inferred from text. A flagged round never becomes approved by a vote.
    """
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("Unrecognized battle feedback schema")
    session = _required_string(payload.get("session_id"), "session_id")
    results = payload.get("results")
    if not isinstance(results, list) or not results or len(results) > 500:
        raise ValueError("Expected 1-500 battle results")
    flags = set(reference_issues or ())
    groups = []
    seen_groups: set[str] = set()
    for raw in results:
        if not isinstance(raw, dict):
            raise ValueError("Invalid battle entry")
        group_id = _required_string(raw.get("group_id"), "group_id")
        if group_id in seen_groups:
            raise ValueError(f"Duplicate group: {group_id}")
        seen_groups.add(group_id)
        preset = _required_string(raw.get("preset"), "preset")
        notes = _required_string(raw.get("notes", ""), "notes", allow_empty=True)
        versions = raw.get("candidate_versions")
        if not isinstance(versions, list) or len(versions) < 2 or len(versions) > 12:
            raise ValueError(f"Invalid candidates for {group_id}")
        identities: dict[str, str] = {}
        for v in versions:
            if not isinstance(v, dict):
                raise ValueError("Candidate must be an object")
            letter = _required_string(v.get("letter"), "letter")
            identity = _required_string(v.get("identity"), "candidate identity")
            if len(letter) != 1 or letter not in "ABCDEFGHIJKL" or letter in identities:
                raise ValueError(f"Invalid or duplicate candidate letter in {group_id}")
            if identity in identities.values():
                raise ValueError(f"Duplicate candidate identity in {group_id}")
            identities[letter] = identity
        winner = _required_string(raw.get("winner", ""), "winner", allow_empty=True)
        eliminate = _required_string(raw.get("eliminate", ""), "eliminate", allow_empty=True)
        if winner not in (*identities.keys(), "tie", "") or eliminate not in (*identities.keys(), ""):
            raise ValueError(f"Unknown winner or elimination in {group_id}")
        if winner and winner == eliminate:
            raise ValueError(f"Winner cannot be eliminated in {group_id}")
        declared = raw.get("survivors")
        expected = [identity for letter, identity in identities.items() if letter != eliminate]
        if declared != expected:
            raise ValueError(f"Survivor list does not match candidate IDs in {group_id}")
        issue = group_id in flags
        if winner == "tie":
            disposition = "tie_with_elimination" if eliminate else "undecided_all_survive"
        elif winner:
            disposition = "provisional_winner" if not issue else "reference_repair_required"
        else:
            disposition = "no_vote"
        queue_state = "ready_for_challenger" if len(expected) == 2 and not issue else (
            "repair_reference_first" if issue else "refine_before_next_vote")
        groups.append({
            "group_id": group_id, "preset": preset,
            "winner_letter": winner, "winner_identity": identities.get(winner),
            "eliminated_letter": eliminate, "eliminated_identity": identities.get(eliminate),
            "survivors": expected,
            "candidate_versions": [dict(letter=l, identity=n) for l,n in identities.items()],
            "notes": notes,
            "disposition": disposition,
            "queue_state": queue_state,
            "reference_status": "UNVERIFIED_REPAIR_REQUIRED" if issue else "NOT_INDEPENDENTLY_VERIFIED",
            "listening_approved": False,
        })
    unknown = flags - seen_groups
    if unknown:
        raise ValueError("Reference issue flag does not match any battle: " + ", ".join(sorted(unknown)))
    return {"schema": PLAN_SCHEMA, "source_schema": SCHEMA, "session_id": session,
            "summary": {"groups": len(groups),
                        "provisional_winners": sum(g["disposition"] == "provisional_winner" for g in groups),
                        "reference_repair": sum(g["queue_state"] == "repair_reference_first" for g in groups),
                        "ties": sum(g["winner_letter"] == "tie" for g in groups),
                        "ready_for_challenger": sum(g["queue_state"] == "ready_for_challenger" for g in groups)},
            "groups": groups}


def _md(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def to_markdown(plan: dict[str, Any]) -> str:
    out = ["# Skelly sound battle — verified owner feedback register",
           "", f"Session: `{_md(plan['session_id'])}`. Relative preferences only; no original/reference can win.",
           "", "| Preset | Preferred | Eliminated | Surviving candidate identities | Next step |",
           "|---|---|---|---|---|"]
    for g in plan["groups"]:
        label = g["winner_letter"] or "not voted"
        pref = f"{label}: `{g['winner_identity']}`" if g["winner_identity"] else label
        drop = f"{g['eliminated_letter']}: `{g['eliminated_identity']}`" if g["eliminated_identity"] else "none"
        out.append("| " + " | ".join([_md(g["preset"]), _md(pref), _md(drop),
                                       ", ".join(f"`{_md(x)}`" for x in g["survivors"]), g["queue_state"]]) + " |")
    out += ["", "## Owner listening notes and explicit validation boundaries", ""]
    for g in plan["groups"]:
        out.append(f"**{_md(g['preset'])}:** {_md(g['notes']) or 'No comment supplied'}. "
                   f"Decision: `{g['disposition']}`. Reference: `{g['reference_status']}`.")
        out.append("")
    out += ["## Next-battle rules", "",
            "- Exactly two survivors: preserve their frozen identities; add **one new challenger** after a measurable improvement, not a relabeled duplicate.",
            "- Three survivors after a tie: preserve all three and **do not fabricate an elimination**; improve a failed component or gather another comparison before a new three-way battle.",
            "- Reference issue: hold promotion and rebuild a verified matching **same-take and same-stage** reference first. A vote does not override a broken original.",
            "- Candidate wins are relative preferences, never evidence of a fully matched original, independent-take transfer, or a native/Windows VST3 release.",
            "- Keep owner recordings, learned filters, FLP/FST binaries and audio-embedded HTML out of public GitHub.", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Owner's SKELLY_BATTLE_PICKS.json")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--reference-issue", action="append", default=[],
                        help="Explicitly mark a group whose original/reference needs repair")
    args = parser.parse_args(argv)
    plan = validate_and_plan(json.loads(args.input.read_text(encoding="utf-8")), set(args.reference_issue))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    targets = [args.output_dir / "BATTLE_NEXT_ROUND_PLAN.json", args.output_dir / "BATTLE_RESULTS.md"]
    if any(p.exists() for p in targets):
        parser.error("Refusing to overwrite prior battle analysis")
    targets[0].write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    targets[1].write_text(to_markdown(plan), encoding="utf-8")
    print(json.dumps({"output": [str(x) for x in targets], "summary": plan["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
