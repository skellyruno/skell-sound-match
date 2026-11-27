"""Conservative signature probe for observed FL 26 mixer-slot records.

Not a full project parser. A match identifies a locally well-formed record
and its raw state fingerprint, not proof of enabled state, routing or sound.
Reject ambiguous slot records when associating an exported mixer preset.
"""
from dataclasses import dataclass
import hashlib
import struct
from .flp_tempo_prefix import tempo_prefix

_MARK = b'\x9b\0\0\0\0\x80\x48\x51\x56\x00\x29\x00'


@dataclass(frozen=True)
class StageRecord:
    track: int
    slot: int
    name: str
    offset: int
    size: int
    sha256: str


def _event(raw, pos, tag, maximum):
    if pos >= len(raw) or raw[pos] != tag:
        raise ValueError('unexpected event')
    pos += 1
    n = 0
    for j in range(4):
        if pos >= len(raw):
            raise ValueError('truncated event length')
        value = raw[pos]
        pos += 1
        n |= (value & 127) << (7*j)
        if value < 128:
            break
    else:
        raise ValueError('oversized event length')
    if not 0 < n <= maximum or pos+n > len(raw):
        raise ValueError('invalid event extent')
    return raw[pos:pos+n], pos+n, pos


def probe_stage_records(raw):
    """Probe complete observed local signatures, not arbitrary raw-state bytes."""
    tempo_prefix(raw)
    pos = 22
    result = []
    while True:
        pos = raw.find(b'\xc9', pos)
        if pos < 0:
            break
        start = pos
        pos += 1
        try:
            payload, end, _ = _event(raw, start, 201, 256)
            if len(payload) < 4 or len(payload)%2 or payload[-2:] != b'\0\0':
                continue
            name = payload[:-2].decode('utf-16le')
            if not all(c.isprintable() for c in name):
                continue
            location, end, _ = _event(raw, end, 212, 52)
            if len(location) != 52:
                continue
            track, slot = struct.unpack_from('<ii', location)
            if not 0 <= track < 128 or not 0 <= slot < 10 or raw[end:end+len(_MARK)] != _MARK:
                continue
            state, end, offset = _event(raw, end+len(_MARK), 213, 16*1024*1024)
            result.append(StageRecord(track, slot, name, offset, len(state), hashlib.sha256(state).hexdigest()))
            pos = end
        except (ValueError, UnicodeError, struct.error):
            continue
    return result


def matching_tracks(records, expected):
    """Return exact slot/name/hash matches per track, rejecting duplicate slots.

    expected: iterable of (slot, plugin name, SHA256). Caller supplies verified
    enabled stages from the exported mixer FST. No match is sound validation.
    """
    keys = list(expected)
    if not keys or len({k[0] for k in keys}) != len(keys):
        raise ValueError('missing or duplicate expected slots')
    tracks = {}
    for r in records:
        tracks.setdefault(r.track, []).append(r)
    result = {}
    for track, rows in tracks.items():
        if len({r.slot for r in rows}) != len(rows):
            continue
        found = {(r.slot,r.name,r.sha256) for r in rows}
        count = sum(k in found for k in keys)
        if count:
            result[track] = count
    return result
