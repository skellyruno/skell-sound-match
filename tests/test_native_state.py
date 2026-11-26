import struct
import pytest
from skell_sound_match.wav_only.native_state import parse_equo,probe_fresh_air

def fixture():
    return struct.pack('<i',4)+struct.pack('<fi',1.,0)*93+struct.pack('<f',1.)*837+struct.pack('<5i',0,128,0,170,128)+struct.pack('<3i',0,150,-1)+b'\0'*11

def test_equostate():
    r=fixture();s=parse_equo(r+b'tail');assert s.version==4 and len(s.table)==837 and len(s.target)==93 and s.send_track==-1 and s.trailing==b'tail'
@pytest.mark.parametrize('off,value',[(0,8),(8,99),(4,0x7fc00000),(4096,0x7fc00000),(4116,99999),(4124,999),(4120,0)])
def test_bad_equo(off,value):
    r=bytearray(fixture());struct.pack_into('<I',r,off,value); 
    with pytest.raises(ValueError):parse_equo(bytes(r))
def test_short_equo():
    with pytest.raises(ValueError):parse_equo(fixture()[:30])
def test_air():
    r=bytearray(11312);r[217:226]=b'Fresh Air';r[1716:1720]=b'\x01\0\0\0';struct.pack_into('<3f',r,1720,.18,.18,0);assert probe_fresh_air(bytes(r))==pytest.approx((.18,.18,0))
    r[217]=0
    with pytest.raises(ValueError):probe_fresh_air(bytes(r))
