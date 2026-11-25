import numpy as np
import pytest
from skell_sound_match.stage_diagnostics import Thresholds,freeze_thresholds,diagnostics

def sample():
    t=np.arange(4096);x=np.stack([.2*np.sin(t*.1)]*2,1);y=x.copy();x[2048:]=0;y[2048:]*=.1
    return x,y

def test_exact_and_tail():
    x,y=sample();th=freeze_thresholds(x,y,1024);d=diagnostics(x,y,y,th,1024)
    assert d['vocal_frames']==2 and d['tail_frames']==2 and d['vocal_waveform_nrmse']==0 and d['vocal_correlation']==1
    z=y.copy();z[2048:]*=.5;d=diagnostics(x,y,z,th,1024)
    assert d['vocal_waveform_nrmse']==0 and abs(d['tail_profile']['envelope_db']-6.0206)<1e-4

def test_clipped_vocal_not_erased():
    x,y=sample();y[40:50]=1;th=freeze_thresholds(x,y,1024);z=y.copy();z[40:50]=0
    d=diagnostics(x,y,z,th,1024);assert d['vocal_frames']==2 and d['rail_frames']==1 and d['vocal_valid_samples']==2038 and d['vocal_waveform_nrmse']==0

def test_opposite_polarity():
    x,y=sample();d=diagnostics(x,y,-y,freeze_thresholds(x,y,1024),1024);assert d['vocal_correlation']==-1 and d['vocal_waveform_nrmse']==2

def test_empty_masks_are_not_passes():
    x,y=sample();d=diagnostics(x*0,y,y,Thresholds(.001,.00001),1024);assert d['vocal_frames']==0 and d['vocal_waveform_nrmse'] is None

def test_end_fragment_is_reported():
    x,y=sample();d=diagnostics(x,y,y,freeze_thresholds(x,y,1000),1000);assert d['discarded_end_samples']==96

@pytest.mark.parametrize('bad',[np.zeros((4096,2)),np.full((4096,2),np.nan),np.ones((4096,1))])
def test_bad_training(bad):
    _,y=sample()
    with pytest.raises(ValueError):freeze_thresholds(bad,y,1024)

def test_mismatched_audio():
    x,y=sample()
    with pytest.raises(ValueError):diagnostics(x,y,y[:2048],freeze_thresholds(x,y,1024),1024)

def test_bad_threshold():
    x,y=sample()
    with pytest.raises(ValueError):diagnostics(x,y,y,Thresholds(-1,.001),1024)

def test_bad_frame():
    x,y=sample()
    with pytest.raises(ValueError):freeze_thresholds(x,y,0)
