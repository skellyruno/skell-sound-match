import struct
import pytest
from skell_sound_match.wav_only.flp_tempo_prefix import tempo_prefix


def fixture(tempo=123456):
    def v(e,b):return bytes([e,len(b)])+b
    def d(e,n):return bytes([e])+struct.pack('<I',n)
    payload=v(199,b'26.1.6.5639\0')+d(159,5639)+d(169,15)+bytes([28,1,172,1,1,0])+v(192,'example\0'.encode('utf-16le'))+bytes([37,1])+v(200,'project\0'.encode('utf-16le'))+d(156,tempo)+bytes([67,1,0,9,1,11,0])+b'opaque remainder'
    return b'FLhd'+struct.pack('<IHHH',6,0,1,96)+b'FLdt'+struct.pack('<I',len(payload))+payload


def test_fractional_bpm():assert tempo_prefix(fixture())==123.456


def test_opaque_tail_not_scanned():assert tempo_prefix(fixture(100001))==100.001


@pytest.mark.parametrize('tempo',[0,9999,522001,0xffffffff])
def test_invalid_tempo(tempo):
    with pytest.raises(ValueError):tempo_prefix(fixture(tempo))


@pytest.mark.parametrize('mutator',[lambda b:b[:-1],lambda b:b.replace(b'5639\0',b'5638\0'),lambda b:b.replace(bytes([172,1,1,0]),bytes([172,1,2,0])),lambda b:b.replace(bytes([156]),bytes([155]),1),lambda b:b'XX'+b[2:]])
def test_invalid_prefix(mutator):
    with pytest.raises(ValueError):tempo_prefix(mutator(fixture()))
