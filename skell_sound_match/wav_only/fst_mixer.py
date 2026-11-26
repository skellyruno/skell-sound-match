"""Bounded FL mixer-preset event225 reader. No plugin state interpretation.
Supports exact single-track mixer FST envelope, rejects ambiguous/malformed data.
"""
import struct
MAX_BYTES=16*1024*1024

def parse_mixer_fst(raw):
    if not isinstance(raw,bytes) or not 22<=len(raw)<=MAX_BYTES or raw[:4]!=b'FLhd' or struct.unpack_from('<I',raw,4)[0]!=6 or raw[14:18]!=b'FLdt':raise ValueError('invalid FL mixer envelope')
    if struct.unpack_from('<H',raw,8)[0]!=64:raise ValueError('not mixer FST')
    end=22+struct.unpack_from('<I',raw,18)[0]
    if end!=len(raw):raise ValueError('invalid event extent')
    pos=22;rows=[]
    while pos<end:
        event=raw[pos];pos+=1
        if event<192:n=1 if event<64 else 2 if event<128 else 4
        else:
            n=0
            for j in range(5):
                if pos>=end:raise ValueError('truncated varint')
                b=raw[pos];pos+=1;n|=(b&127)<<(7*j)
                if b<128:break
            else:raise ValueError('oversized varint')
        if n>end-pos:raise ValueError('truncated event')
        if event==225:
            if n!=384 or rows:raise ValueError('unsupported mixer parameter block')
            rows=list(struct.iter_unpack('<IBBHi',raw[pos:pos+n]))
        pos+=n
    if len(rows)!=32:raise ValueError('missing mixer parameter block')
    track=None;slots={};mixer={}
    for reserved,code,kind,key,value in rows:
        if reserved!=0 or kind!=31 or not 0x7000<=key<0x9000:raise ValueError('unsupported mixer row')
        t=(key-0x7000)>>6;s=key&63
        if track is None:track=t
        if track!=t:raise ValueError('multiple tracks')
        if code in (0,1):
            if s>=10 or (s,code) in slots or (code==0 and value not in (0,1)) or (code==1 and not 0<=value<=12800):raise ValueError('invalid slot value')
            slots[s,code]=value
        else:
            if s!=0 or code in mixer or code not in (192,193,194,208,209,210,216,217,218,224,225,226):raise ValueError('unsupported mixer control')
            mixer[code]=value
    if len(slots)!=20 or len(mixer)!=12:raise ValueError('incomplete mixer control block')
    return {'track':track,'slots':[{'slot':i,'enabled':bool(slots[i,0]),'wet_raw':slots[i,1]} for i in range(10)],'mixer':mixer}
