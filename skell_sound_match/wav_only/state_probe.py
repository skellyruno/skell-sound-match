"""Offline state-envelope inspection only; no automatic effect translation.
Inspect explicit bounded raw FFBS/FabF state or an exact Waves XML chunk.
Preserve unknown trailing bytes; no inferred preset or phase-mode mapping.
"""
from dataclasses import dataclass
import hashlib
import math
import re
import struct
import xml.etree.ElementTree as ET

MAX_BYTES=16*1024*1024
ALPHABET='.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+'

@dataclass(frozen=True)
class FabState:
    format: str
    version: int
    count: int
    values: tuple
    trailing: bytes
    name_bytes: bytes
    sha256: str


def juce_component(text):
    """Decode exact JUCE size-prefixed LSB-first encoding; reject truncation."""
    size,sep,encoded=text.partition('.')
    if not sep or not re.fullmatch(r'[0-9]{1,9}',size):raise ValueError('invalid size')
    n=int(size)
    if not 12<=n<=MAX_BYTES or len(encoded)!=(8*n+5)//6:raise ValueError('invalid encoded length')
    table={c:i for i,c in enumerate(ALPHABET)};out=bytearray();acc=bits=0
    for c in encoded:
        if c not in table:raise ValueError('invalid alphabet')
        acc|=table[c]<<bits;bits+=6
        if bits>=8:
            out.append(acc&255);acc>>=8;bits-=8
    if len(out)!=n or acc:raise ValueError('nonzero padding')
    return bytes(out)


def fab_state(data):
    if not isinstance(data,bytes) or not 12<=len(data)<=MAX_BYTES:raise ValueError('invalid state size')
    if data[:4] not in (b'FFBS',b'FabF'):
        hits=re.findall(rb'<IComponent>([^<]*)</IComponent>',data)
        if len(hits)!=1:raise ValueError('expected one explicit component')
        try:raw=juce_component(hits[0].decode('ascii'))
        except UnicodeError as e:raise ValueError('invalid component text') from e
        if raw[:4] not in (b'FFBS',b'FabF'):raise ValueError('unsupported component magic')
        data=raw
    fmt=data[:4].decode('ascii');version=struct.unpack_from('<I',data,4)[0];name=b''
    if fmt=='FFBS':count=struct.unpack_from('<I',data,8)[0];at=12
    else:
        n=struct.unpack_from('<I',data,8)[0]
        if n>1024 or 20+n>len(data):raise ValueError('invalid name length')
        name=data[12:12+n];count=struct.unpack_from('<I',data,16+n)[0];at=20+n
    if not 1<=count<=4096 or at+4*count>len(data):raise ValueError('invalid value count')
    values=struct.unpack_from('<'+'f'*count,data,at)
    if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite declared value')
    return FabState(fmt,version,count,values,data[at+4*count:],name,hashlib.sha256(data).hexdigest())


def waves_active_xml(data):
    """Read active RealWorld lists from explicit embedded XML chunks.
    Does not prove mixer slot order, active mix, wrapper bypass or routing.
    """
    if not isinstance(data,bytes) or not 1<=len(data)<=MAX_BYTES:raise ValueError('invalid wrapper size')
    result=[]
    for m in re.finditer(rb'<PresetChunkXMLTree\b[^>]*>.*?</PresetChunkXMLTree>',data,re.S):
        raw=m.group()
        if len(raw)>1024*1024 or b'<!' in raw:raise ValueError('unsupported XML declaration')
        try:root=ET.fromstring(raw)
        except ET.ParseError as e:raise ValueError('invalid Waves XML') from e
        for preset in root.findall('Preset'):
            head=preset.find('PresetHeader')
            if head is None:raise ValueError('missing header')
            plugin=head.findtext('PluginName');setup=head.findtext('ActiveSetup');comp=head.findtext('PluginSubComp')
            if not plugin or setup not in ('SETUP_A','SETUP_B') or not comp:raise ValueError('missing identity or active setup')
            nodes=[v for p in preset.findall('PresetData') if p.get('Setup')==setup for v in p.findall('Parameters') if v.get('Type')=='RealWorld']
            if len(nodes)!=1 or not nodes[0].text:raise ValueError('ambiguous or missing active list')
            tokens=nodes[0].text.split()
            if not 1<=len(tokens)<=4096:raise ValueError('invalid list size')
            vals=tuple(None if v=='*' else float(v) for v in tokens)
            if not all(v is None or math.isfinite(v) for v in vals):raise ValueError('nonfinite list value')
            result.append(dict(plugin=plugin,component=comp,setup=setup,values=vals,offset=m.start(),xml_sha256=hashlib.sha256(raw).hexdigest()))
    if not result:raise ValueError('no supported Waves XML')
    return result
