import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.compressor_anchor import (
    CompressorAnchor, envelope_hypothesis, mono_wav, rms_db_frames, stage_report,
)

SR = 44100


def sine(seconds=1.0, amplitude=.1):
    t = np.arange(round(SR*seconds))/SR
    return amplitude*np.sin(2*np.pi*220*t)


def test_attenuation_over_threshold():
    x = sine(1.0)
    h = envelope_hypothesis(x, SR, CompressorAnchor(threshold_db=-38, ratio=8))
    assert h['hypothetical_gr_db'].min() < -2
    assert np.isfinite(h['hypothetical_gr_db']).all()


def test_slow_release_vs_attack():
    x = np.r_[sine(.2, .005), sine(.2,.4), sine(.6,.005)]
    h = envelope_hypothesis(x, SR)
    # Detector should rise quickly and then relax with a longer release.
    assert h['detector_db'][int(.39 * 200)] > h['detector_db'][int(.21 * 200)]
    assert h['detector_db'][int(.41 * 200)] > h['detector_db'][int(.9 * 200)]


def test_invalid_settings_rejected():
    with pytest.raises(ValueError):
        envelope_hypothesis(sine(), SR, CompressorAnchor(ratio=0))
    with pytest.raises(ValueError):
        envelope_hypothesis(sine(), SR, CompressorAnchor(attack_ms=float('nan')))


def test_nonfinite_input_rejected():
    x=sine();x[1]=np.nan
    with pytest.raises(ValueError):rms_db_frames(x, SR)


def test_stage_report_and_file_protection(tmp_path):
    src=tmp_path/'input.wav'; target=tmp_path/'target.wav'
    x=sine();sf.write(src,np.c_[x,x],SR,subtype='PCM_24')
    sf.write(target,np.c_[x*.8,x*.8],SR,subtype='PCM_24')
    before=src.read_bytes(),target.read_bytes()
    report=stage_report(src,target)
    assert report['active_frames']>10 and report['frames']==SR
    assert 'not_vendor_dsp' in report['status']
    assert before==(src.read_bytes(),target.read_bytes())


def test_reject_nonmatching_inputs(tmp_path):
    x=tmp_path/'a.wav';y=tmp_path/'b.wav'
    sf.write(x,sine(),SR);sf.write(y,sine(.5),SR)
    with pytest.raises(ValueError):stage_report(x,y)


def test_reject_stereo_side(tmp_path):
    x=tmp_path/'st.wav'; t=sine();sf.write(x,np.c_[t,-t],SR)
    with pytest.raises(ValueError):mono_wav(x)
