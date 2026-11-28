import numpy as np
import pytest
from skell_sound_match.audio_alignment import alignment_diagnostic


def speech_like(rate=44100, length=2.6):
    t=np.arange(round(rate*length))/rate
    env=.04+.85*(np.sin(2*np.pi*2.4*t)**10)
    carrier=.13*np.sin(2*np.pi*170*t)+.11*np.sin(2*np.pi*487*t)+.07*np.sin(2*np.pi*1010*t)+.04*np.sin(2*np.pi*2770*t)
    x=(env*carrier).astype(np.float64)
    return np.stack((x,x*.85),axis=1)


@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_exact_and_level_changed_pair(rate):
    source=speech_like(rate)
    result=alignment_diagnostic(source,source*.5,rate)
    assert result.best_similarity>.99
    assert abs(result.offset_seconds)<=.011
    assert result.identity_verified is False


def test_detect_delayed_candidate():
    rate=44100
    src=speech_like(rate)
    late=np.pad(src,((round(rate*.17),0),(0,0)))[:len(src)]
    got=alignment_diagnostic(src,late,rate)
    assert abs(got.offset_seconds-.17)<.022,got
    assert got.best_similarity>.90


def test_does_not_automatically_verify_identity_even_at_one():
    src=speech_like(44100)
    v=alignment_diagnostic(src,src.copy(),44100)
    assert v.best_similarity>.99 and v.identity_verified is False


@pytest.mark.parametrize('rate',[44100,96000])
def test_silence_rejected(rate):
    src=np.zeros((rate*2,2))
    with pytest.raises(ValueError, match='silent'):
        alignment_diagnostic(src,src,rate)


def test_short_audio_rejected():
    with pytest.raises(ValueError):
        alignment_diagnostic(np.ones((100,2)),np.ones((100,2)),44100)


@pytest.mark.parametrize('rate',[0,44100.0,200000])
def test_invalid_rate(rate):
    src=speech_like(44100)
    with pytest.raises(ValueError,match='rate'):
        alignment_diagnostic(src,src,rate)


def test_nonfinite_signal_rejected():
    src=speech_like(44100)
    src[0]=np.nan
    with pytest.raises(ValueError):
        alignment_diagnostic(src,src,44100)


def test_no_sufficient_overlap():
    src=speech_like(44100,1.2)
    with pytest.raises(ValueError):
        alignment_diagnostic(src,src,44100,minimum_overlap_seconds=3)


def test_bad_offset_bounds():
    src=speech_like(44100)
    with pytest.raises(ValueError):
        alignment_diagnostic(src,src,44100,maximum_offset_seconds=float('nan'))
