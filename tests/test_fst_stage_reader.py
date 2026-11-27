import struct
import pytest
from skell_sound_match.wav_only.fst_stage_reader import parse,CODES

def event(code,data):
 n=len(data);b=bytearray([code]);
 while n>=128:b.append((n&127)|128);n>>=7
 b.append(n);return bytes(b)+data

def fixture(base=0x2000,track=8,control_track=None,duplicate=False):
 def stage(s,name):return event(201,(name+'\0').encode('utf-16le'))+event(212,struct.pack('<ii',track,s)+bytes(44))+event(213,struct.pack('<8i',4,512,768,8,128,-32,96,96))
 key=base+(track if control_track is None else control_track)*64
 rows=[struct.pack('<IBBHi',0,c,31,key+s, (0 if s==0 else 1) if c==0 else 6400) for s in range(10) for c in (0,1)]
 rows += [struct.pack('<IBBHi',0,c,31,key,-32 if c==194 else 0) for c in sorted(CODES)]
 d=event(199,b'21.2.2\0')+stage(0,'Fruity Chorus')+stage(6,'Fruity Flangus')+(stage(6,'Duplicate') if duplicate else b'')+event(225,b''.join(rows))
 return b'FLhd'+struct.pack('<IHHH',6,64,1,96)+b'FLdt'+struct.pack('<I',len(d))+d

@pytest.mark.parametrize('base',[0x2000,0x7000])
def test_mixer_layout(base):
 m=parse(fixture(base));assert m['key_base']==base and m['track']==8
 a,b=m['stages'];assert a.slot==0 and not a.enabled and b.slot==6 and b.enabled and b.wet_raw==6400
 assert struct.unpack('<8i',b.raw)==(4,512,768,8,128,-32,96,96)
 assert m['mixer'][194]==-32

@pytest.mark.parametrize('raw',[fixture(0x4000),fixture(control_track=9),fixture(duplicate=True),fixture()[:-1],b'FLhd'])
def test_reject_bad_records(raw):
 with pytest.raises(ValueError):parse(raw)
