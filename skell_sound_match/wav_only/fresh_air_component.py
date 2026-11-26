"""Inspect a known-size Fresh Air component, separately from its host wrapper."""
import math
import struct


def parse_air_component(raw):
    if not isinstance(raw, bytes) or len(raw) != 2530:
        raise ValueError('unsupported component length')
    if struct.unpack_from('<II', raw) != (1, 2522):
        raise ValueError('unsupported component envelope')
    mid, high = struct.unpack_from('<2f', raw, 1290)
    trim = struct.unpack_from('<f', raw, 2526)[0]
    if not all(math.isfinite(v) for v in (mid, high, trim)) or not (0 <= mid <= 1 and 0 <= high <= 1 and -12 <= trim <= 0):
        raise ValueError('invalid component controls')
    return mid, high, trim
