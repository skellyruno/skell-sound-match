import struct
import pytest
from skell_sound_match.wav_only.fst_mixer import parse_mixer_fst

def rows():
    return [(0,c,31,0x7040+s,1 if c==0 else 640) for s in range(10) for c in (0,1)]+[(0,c,31,0x7040,-10) for c in (192,193,194,208,209,210,216,217,218,224,225,226)]

def file(r=None,kind=64,extra=b''):
    payload=b''.join(struct.pack('<IBBHi',*x) for x in (rows() if r is None else r))
    events=b'\xe1'+bytes([len(payload)%128+128,len(payload)//128])+payload+extra
    return b'FLhd'+struct.pack('<I3H',6,kind,1,96)+b'FLdt'+struct.pack('<I',len(events))+events

def test_valid():
    m=parse_mixer_fst(file());assert m['track']==1 and len(m['slots'])==10
    assert m['slots'][6]==dict(slot=6,enabled=True,wet_raw=640) and m['mixer'][194]==-10

@pytest.mark.parametrize('row_index,field,value',[(0,0,1),(0,2,30),(0,3,0x7080),(0,4,2),(1,4,12801),(1,4,-1),(1,1,0),(20,1,255),(21,1,192),(20,3,0x7041)])
def test_bad_rows(row_index,field,value):
    r=rows();v=list(r[row_index]);v[field]=value;r[row_index]=tuple(v)
    with pytest.raises(ValueError):parse_mixer_fst(file(r))

@pytest.mark.parametrize('raw',[b'',file()[:-1],file(kind=0),file(rows()[:-1]),file(extra=b'\xe1\x80'),file(extra=b'\xe1\x80\x80\x80\x80\x80'),file()+b'x',file(extra=b'\xe1\x00')])
def test_bad_envelope(raw):
    with pytest.raises(ValueError):parse_mixer_fst(raw)
