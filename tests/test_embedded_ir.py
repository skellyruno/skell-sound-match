from io import BytesIO
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.wav_only.embedded_ir import recover_stereo_ir


def wav(x, rate=44100):
    b = BytesIO()
    sf.write(b, x, rate, format='WAV', subtype='FLOAT')
    return b.getvalue()


def test_recovers_exact_stereo_float_and_offset():
    x = np.array([[0, 0], [.125, -.25], [.5, 0]], dtype=np.float32)
    got = recover_stereo_ir(b'header' + wav(x, 48000) + b'end')
    assert len(got) == 1 and got[0].offset == 6 and got[0].sample_rate == 48000
    np.testing.assert_array_equal(got[0].samples, x)
    assert not got[0].samples.flags.writeable


def test_skips_truncated_and_mono_and_silent():
    x = np.ones((30, 2), dtype=np.float32) * .1
    assert recover_stereo_ir(wav(x)[:-2]) == []
    assert recover_stereo_ir(wav(x[:, 0]) + wav(np.zeros_like(x))) == []
    assert len(recover_stereo_ir(b'RIFFinvalid' + wav(x))) == 1


def test_bounds():
    with pytest.raises(ValueError):
        recover_stereo_ir(b'x'*100, max_bytes=50)
