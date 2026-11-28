import numpy as np
import pytest
from scipy import signal

from skell_sound_match.wav_only.stereo_finish_audit import (
    finish_stereo, heldout_band_mae, high_shelf_sos, peaking_sos,
    side_mid_db, trim_true_peak, estimate_true_peak_db,
)


def _signal(sr=44100, seconds=1):
    t = np.arange(sr * seconds) / sr
    l = 0.05 * np.sin(2*np.pi*330*t) + 0.03*np.sin(2*np.pi*8300*t)
    r = 0.04 * np.sin(2*np.pi*330*t+0.5) + 0.015*np.sin(2*np.pi*8300*t+0.9)
    return np.column_stack((l,r))


def test_zero_eq_and_unity_width_identity():
    x=_signal()
    y=finish_stereo(x,44100)
    assert np.max(np.abs(x-y)) < 1e-11
    q=peaking_sos(44100,1250,0)
    assert np.allclose(q[:3],q[3:],atol=1e-12)


def test_side_gain_preserves_mid_and_doubles_existing_side():
    x=_signal()
    y=finish_stereo(x,44100,side_gain=2)
    assert np.allclose(y.mean(axis=1),x.mean(axis=1),atol=1e-10)
    assert np.allclose(y[:,0]-y[:,1],2*(x[:,0]-x[:,1]),atol=1e-10)
    assert side_mid_db(y)-side_mid_db(x)==pytest.approx(20*np.log10(2),abs=.01)


def test_mono_does_not_grow_fake_width():
    mono=_signal()[:,0]
    x=np.column_stack([mono,mono])
    y=finish_stereo(x,44100,air_db=4,side_gain=3)
    assert np.max(abs(y[:,0]-y[:,1])) < 1e-10


def test_high_shelf_is_stable_and_increases_air():
    x=_signal()
    y=finish_stereo(x,44100,air_db=6)
    assert np.all(np.isfinite(y))
    f,h=signal.sosfreqz(high_shelf_sos(44100,7500,6)[None,:],worN=[500,12000],fs=44100)
    assert 20*np.log10(abs(h[1])/abs(h[0])) > 4
    assert np.all(np.isfinite(peaking_sos(44100,1250,2)))


def test_trim_true_peak_is_peak_safe_and_no_upward_adjustment():
    x=_signal() * 20
    y,trim=trim_true_peak(x,-1.5)
    assert trim < 0
    assert estimate_true_peak_db(y) <= -1.49
    z,db=trim_true_peak(x*.01,-1.5)
    assert db == 0
    assert np.allclose(z,x*.01)


def test_heldout_error_identical_and_brightness_difference():
    x=_signal(seconds=2)
    same=heldout_band_mae(x,x,44100,.5,1.8)
    assert same['mae_db']<1e-10
    brighter=finish_stereo(x,44100,air_db=5)
    changed=heldout_band_mae(x,brighter,44100,.5,1.8)
    assert changed['mae_db']>0.2
    assert changed['band_errors_db'][-1]>0


def test_rejects_bad_audio_settings_and_unpaired_data():
    x=_signal()
    with pytest.raises(ValueError):finish_stereo(x[:100],44100,side_gain=5)
    with pytest.raises(ValueError):finish_stereo(x[:100],44100,air_db=30)
    with pytest.raises(ValueError):finish_stereo(x[:100,0],44100)
    with pytest.raises(ValueError):finish_stereo(np.full((100,2),float('nan')),44100)
    with pytest.raises(ValueError):heldout_band_mae(x,x[:10],44100,0,1)
    with pytest.raises(ValueError):heldout_band_mae(x,x,44100,.9,1.2)
