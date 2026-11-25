"""Conservative saved-slot coverage audit; does not infer enabled state or fidelity."""
from dataclasses import dataclass
from typing import Iterable
import re

_HASH = re.compile(r"[0-9a-f]{64}\Z")

@dataclass(frozen=True)
class SavedSlot:
    slot: int
    effect: str
    state_sha256: str

@dataclass(frozen=True)
class RenderedSlot:
    slot: int
    effect: str
    state_sha256: str
    mode: str = "state_replay"

@dataclass(frozen=True)
class Coverage:
    replayed: tuple[int, ...]
    approximate: tuple[int, ...]
    missing: tuple[int, ...]
    unexpected: tuple[int, ...]
    mismatched: tuple[int, ...]

    @property
    def all_saved_slots_accounted_for(self) -> bool:
        """Coverage only, not an assertion that every saved slot was enabled."""
        return not (self.approximate or self.missing or self.unexpected or self.mismatched)


def _index(items: Iterable[SavedSlot | RenderedSlot]) -> dict[int, SavedSlot | RenderedSlot]:
    out = {}
    for row in items:
        if type(row.slot) is not int or not 0 <= row.slot <= 255:
            raise ValueError("invalid physical slot")
        if not isinstance(row.effect, str) or not row.effect.strip():
            raise ValueError("missing effect identity")
        if not isinstance(row.state_sha256, str) or not _HASH.fullmatch(row.state_sha256):
            raise ValueError("invalid state digest")
        if row.slot in out:
            raise ValueError("duplicate physical slot")
        out[row.slot] = row
    return out


def audit_saved_slots(saved: Iterable[SavedSlot], rendered: Iterable[RenderedSlot]) -> Coverage:
    """Audit a single mixer track. Never treat an approximation as exact replay.

    The caller is responsible for source identity, actual DSP execution, enable
    state, processing order, automation and reference pairing. A complete
    coverage result is necessary evidence, not an audio or release approval.
    """
    s, r = _index(saved), _index(rendered)
    if not s:
        raise ValueError("no saved slot evidence")
    replayed, approximate, mismatched = [], [], []
    for k in sorted(s.keys() & r.keys()):
        if r[k].effect != s[k].effect or r[k].state_sha256 != s[k].state_sha256:
            mismatched.append(k)
        elif r[k].mode == "state_replay":
            replayed.append(k)
        elif r[k].mode == "approximation":
            approximate.append(k)
        else:
            raise ValueError("unknown render mode")
    return Coverage(tuple(replayed), tuple(approximate), tuple(sorted(s.keys()-r.keys())),
                    tuple(sorted(r.keys()-s.keys())), tuple(mismatched))
