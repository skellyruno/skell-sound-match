import hashlib
import struct
from dataclasses import replace
import pytest
from test_flp_tempo_prefix import fixture
from skell_sound_match.wav_only.flp_stage_probe import probe_stage_records, matching_tracks


def event(tag, data):
    n=len(data); out=bytearray([tag])
    while n>=128:
        out.append((n&127)|128); n>>=7
    out.append(n);return bytes(out)+data


def record(name='Example Delay',track=4,slot=2,state=b'example state'):
    loc=struct.pack('<ii',track,slot)+bytes(44)
    return event(201,(name+'\0').encode('utf-16le'))+event(212,loc)+b'\x9b\0\0\0\0\x80\x48\x51\x56\x00\x29\x00'+event(213,state)


def project(*records):
    b=fixture()+b''.join(records)
    return b[:18]+struct.pack('<I',len(b)-22)+b[22:]


def test_exact_state_and_location():
    state=bytes(range(256));p=project(record(state=state));r=probe_stage_records(p)
    assert len(r)==1 and r[0].slot==2 and r[0].track==4
    assert p[r[0].offset:r[0].offset+r[0].size]==state
    assert matching_tracks(r,[(2,'Example Delay',hashlib.sha256(state).hexdigest())])=={4:1}


def test_ignore_partial_signature():
    assert probe_stage_records(project(record()[:-1]))==[]
    assert probe_stage_records(project(record().replace(b'\x80\x48\x51\x56',b'\x80\x48\x51\x57')))==[]


def test_wrong_track_and_slot():
    assert probe_stage_records(project(record(track=128),record(slot=-1)))==[]


def test_ambiguous_duplicate_location():
    r=probe_stage_records(project(record(),record(state=b'other')))
    assert len(r)==2
    assert matching_tracks(r,[(2,r[0].name,r[0].sha256)])=={}


def test_duplicate_expected_rejected():
    r=probe_stage_records(project(record()))
    k=(2,r[0].name,r[0].sha256)
    with pytest.raises(ValueError):matching_tracks(r,[k,k])


def test_do_not_scan_inside_recognized_payload():
    r=probe_stage_records(project(record(state=record(track=10))))
    assert len(r)==1 and r[0].track==4
