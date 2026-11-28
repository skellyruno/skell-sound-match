"""Bounded offline state inspection for EQUO v3/v4 and a known Fresh Air wrapper.
Unknown wrapper versions are rejected. The Air offsets are provisional until
verified by the complete original freshAirAmounts decoder.
"""
import math
import struct
from dataclasses import dataclass

@dataclass(frozen=True)
class EquoState:
    version: int
    target: tuple
    table: tuple
    knobs: tuple
    oversampling: int
    bandwidth: int
    send_track: int
    send_only: bool
    add_mode: bool
    trailing: bytes


def parse_equo(raw):
    if not isinstance(raw,bytes) or not 4139<=len(raw)<=65536:
        raise ValueError('invalid EQUO state size')
    version=struct.unpack_from('<i',raw,0)[0]
    if version not in (3,4):raise ValueError('unsupported EQUO version')
    at=4;targets=[]
    for _ in range(93):
        v,m=struct.unpack_from('<fi',raw,at);at+=8
        if not math.isfinite(v) or not 0<=v<=2 or m not in (0,1,2):raise ValueError('invalid target')
        targets.append((v,m))
    table=struct.unpack_from('<837f',raw,at);at+=3348
    if any(not math.isfinite(v) or not 0<=v<=2 for v in table):raise ValueError('invalid bank cell')
    knobs=struct.unpack_from('<5i',raw,at);at+=20
    if any(not lo<=v<=hi for v,(lo,hi) in zip(knobs,[(-12000,12000),(-128,128),(0,7000),(0,1024),(0,256)])):raise ValueError('invalid knob')
    oversampling,bandwidth,send=struct.unpack_from('<3i',raw,at)
    if oversampling not in (0,1) or not 80<=bandwidth<=500 or not -1<=send<=127:raise ValueError('invalid options')
    return EquoState(version,tuple(targets),table,knobs,oversampling,bandwidth,send,bool(raw[at+20]),bool(raw[at+21]),raw[at+23:])


def probe_fresh_air(raw):
    if not isinstance(raw,bytes) or len(raw)!=11312 or raw[217:226]!=b'Fresh Air' or raw[1716:1720]!=b'\x01\x00\x00\x00':raise ValueError('unsupported Fresh Air wrapper')
    m,h,t=struct.unpack_from('<3f',raw,1720)
    if not all(math.isfinite(v) for v in (m,h,t)) or not (0<=m<=1 and 0<=h<=1 and -12<=t<=0):raise ValueError('invalid Air controls')
    return m,h,t
