import struct
import pytest
from skell_sound_match.wav_only.fresh_air_component import parse_air_component


def fixture():
    raw = bytearray(2530)
    struct.pack_into('<II', raw, 0, 1, 2522)
    struct.pack_into('<2f', raw, 1290, .18, .25)
    struct.pack_into('<f', raw, 2526, -3)
    return raw


def test_valid():
    assert parse_air_component(bytes(fixture())) == pytest.approx((.18, .25, -3))


@pytest.mark.parametrize('offset,value', [(0, 0), (4, 2521), (1290, 0x7fc00000), (1294, 0x40000000), (2526, 0x7f800000), (2526, 0x3f800000)])
def test_invalid(offset, value):
    raw = fixture()
    struct.pack_into('<I', raw, offset, value)
    with pytest.raises(ValueError):
        parse_air_component(bytes(raw))


def test_length():
    with pytest.raises(ValueError):
        parse_air_component(bytes(fixture()[:-1]))
