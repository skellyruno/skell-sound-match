"""Bounded, read-only FL mixer FST event extraction. No opaque DSP interpretation."""
import struct
from dataclasses import dataclass
MAX=16*1024*1024
CODES={192,193,194,208,209,210,216,217,218,224,225,226}
@dataclass(frozen=True)
class Stage:
    slot:int
    name:str
    raw:bytes
    enabled:bool
    wet_raw:int

def parse(raw):
    if not isinstance(raw,bytes) or not 22<=len(raw)<=MAX or raw[:4]!=b'FLhd' or struct.unpack_from('<I',raw,4)[0]!=6 or struct.unpack_from('<H',raw,8)[0]!=64 or raw[14:18]!=b'FLdt' or 22+struct.unpack_from('<I',raw,18)[0]!=len(raw):raise ValueError('invalid mixer envelope')
    pos=22; pending=None; loc=None; version=''; track=None; states={}; controls=None
    while pos<len(raw):
        e=raw[pos];pos+=1
        if e<192:n=1 if e<64 else 2 if e<128 else 4
        else:
            n=0
            for j in range(5):
                if pos>=len(raw):raise ValueError('truncated length')
                b=raw[pos];pos+=1;n|=(b&127)<<(j*7)
                if b<128:break
            else:raise ValueError('oversized length')
        if n>len(raw)-pos:raise ValueError('truncated event')
        d=raw[pos:pos+n];pos+=n
        if e==199:
            if version:raise ValueError('duplicate version')
            version=d.rstrip(b'\0').decode('ascii')
        elif e==201:
            if pending is not None or loc is not None:raise ValueError('incomplete plugin state')
            if not 4<=len(d)<=256 or len(d)%2 or d[-2:]!=b'\0\0':raise ValueError('invalid plugin name')
            pending=d[:-2].decode('utf-16le')
            if not pending or '\0' in pending:raise ValueError('invalid plugin name')
        elif e==212:
            if pending is None or loc is not None or len(d)!=52:raise ValueError('invalid plugin location')
            t,s=struct.unpack_from('<ii',d)
            if not 0<=t<128 or not 0<=s<10 or (track is not None and track!=t) or s in states:raise ValueError('ambiguous plugin location')
            track=t;loc=s
        elif e==213:
            if pending is None or loc is None or not d:raise ValueError('orphan plugin state')
            states[loc]=(pending,d);pending=None;loc=None
        elif e==225:
            if controls is not None or n!=384:raise ValueError('unsupported mixer block')
            controls=list(struct.iter_unpack('<IBBHi',d))
    if pending is not None or loc is not None or track is None or not states or controls is None:raise ValueError('missing stage or control data')
    # Two observed encodings: legacy 0x2000 + track*64, modern 0x7000 + track*64.
    # Validate the whole block against the explicit event-212 track, not a guess based on version.
    bases={key-(key&63)-track*64 for _,_,_,key,_ in controls}
    if len(bases)!=1 or next(iter(bases)) not in (0x2000,0x7000):raise ValueError('unknown mixer key layout')
    slots={}; mixer={}
    for res,code,kind,key,value in controls:
        if res or kind!=31:raise ValueError('invalid control row')
        s=key&63
        if code in (0,1):
            if s>=10 or (s,code) in slots or (code==0 and value not in (0,1)) or (code==1 and not 0<=value<=12800):raise ValueError('invalid slot control')
            slots[s,code]=value
        elif s or code not in CODES or code in mixer:raise ValueError('invalid mixer control')
        else:mixer[code]=value
    if len(slots)!=20 or len(mixer)!=12:raise ValueError('incomplete mixer control block')
    return {'version':version,'track':track,'key_base':next(iter(bases)),'stages':[Stage(s,n,d,bool(slots[s,0]),slots[s,1]) for s,(n,d) in sorted(states.items())],'mixer':mixer}
