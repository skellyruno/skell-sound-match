import numpy as np
import pytest
from scipy import signal
from skell_sound_match.core import Audio
from skell_sound_match.serial_calibration import (fit_serial, render_serial, evaluate_sections,
                                                   fit_stage, apply_stage, safe_for_preview, SerialModel)


def mock(sr=16000, sec=7):
    t=np.arange(sr*sec)/sr
    vocal=(.11+.07*np.sin(2*np.pi*1.6*t))*(np.sin(2*np.pi*177*t)+.21*np.sin(2*np.pi*1299*t))
    rec=signal.lfilter([1.,-.25],[1.,-.12],vocal)*.76
    main=lambda x:.16*np.tanh(1.6*x/.16)
    return tuple(Audio(q[:,None],sr) for q in (vocal,rec,main(vocal),main(rec)))


def test_serial_training_and_replay():
    d,r,m,f=mock()
    state=fit_serial(d,r,m,f,train_window=(.5,3.4))
    y=render_serial(d,state)
    same=render_serial(d,state)
    assert np.array_equal(y.samples,same.samples)
    assert state.offline_only
    assert state.rec['lookahead_samples']>0 and state.main['lookahead_samples']>0
    assert all(np.isfinite(y.samples.ravel()))
    assert safe_for_preview(y)
    res=evaluate_sections(f,y,{'test':(4,6.5)},(.5,3.4))
    assert np.isfinite(res['sections']['test']['waveform_corr'])
    assert res['sections']['test']['waveform_corr']>.7


def test_does_not_mutate_original():
    aud=list(mock()); backups=[x.samples.copy() for x in aud]
    fit_serial(*aud,train_window=(.5,3.4))
    assert all(np.array_equal(x.samples,old) for x,old in zip(aud,backups))


def test_mismatch_stereo_and_nan_rejected():
    d,r,m,f=mock()
    with pytest.raises(ValueError,match='rates and sample counts'):
        fit_serial(d,r,Audio(m.samples[:-2],m.rate),f,train_window=(.5,3.4))
    stereo=Audio(np.column_stack((r.samples[:,0],-r.samples[:,0])),r.rate)
    with pytest.raises(ValueError,match='stereo'):
        fit_serial(d,stereo,m,f,train_window=(.5,3.4))
    bad=d.samples.copy();bad[0]=np.nan
    with pytest.raises(ValueError,match='Non-finite'):
        fit_serial(Audio(bad,d.rate),r,m,f,train_window=(.5,3.4))


def test_bad_preset_rejected():
    d,r,m,f=mock()
    state=fit_serial(d,r,m,f,train_window=(.5,3.4))
    invalid=dict(state.rec);invalid['max_gain_change_db']=50
    with pytest.raises(ValueError,match='Invalid/unsafe'):
        apply_stage(d.samples[:,0],d.rate,invalid)
    with pytest.raises(ValueError,match='Invalid evaluation window'):
        evaluate_sections(f,f,{'late':(4,100)},(.5,3.4))


def test_parallel_probe_does_not_claim_routing():
    from skell_sound_match.serial_calibration import probe_direct_path
    d,r,m,f=mock()
    probe=probe_direct_path(d,m,f,(.5,3.4),{'late':(4,6.5)})
    assert 'cannot prove' in probe['warning']
    assert np.isfinite(probe['sections']['late']['corr_delta'])