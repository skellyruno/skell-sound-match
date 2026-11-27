import io
import wave
import struct
import pytest
from skell_sound_match.wav_only.embedded_wave import extract_embedded_wave


def wav():
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(bytes(64))
    return b.getvalue()


def test_exact_bytes():
    x=wav();assert extract_embedded_wave(b'header'+x+b'tail')==x


def test_ignores_invalid_riff():
    x=wav();assert extract_embedded_wave(b'RIFF'+bytes(32)+x)==x


def test_ambiguous():
    with pytest.raises(ValueError):extract_embedded_wave(wav()+wav())


@pytest.mark.parametrize('state',[b'not a wav'*10,wav()[:-1],wav().replace(b'WAVE',b'AVI '),wav().replace(b'data',b'JUNK')])
def test_invalid(state):
    with pytest.raises(ValueError):extract_embedded_wave(state)


def test_invalid_rate():
    x=bytearray(wav());struct.pack_into('<I',x,24,0)
    with pytest.raises(ValueError):extract_embedded_wave(bytes(x))
