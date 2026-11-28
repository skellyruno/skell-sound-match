import numpy as np
import pytest
from skell_sound_match.core import Audio
from skell_sound_match.interactions import analyze_interactions

def fixture(nonlinear=False):
    sr=22050;t=np.arange(sr*6)/sr
    amplitude=.02+.15*(.5+.5*np.sin(2*np.pi*1.2*t))
    dry=amplitude*(np.sin(2*np.pi*220*t)+.2*np.sin(2*np.pi*1500*t)+.1*np.sin(2*np.pi*6300*t))
    rec=.65*dry
    fx=(lambda z:.1*np.tanh(z/.1)) if nonlinear else (lambda z:1.35*z)
    return tuple(Audio(z[:,None],sr) for z in (dry,rec,fx(dry),fx(rec)))

def test_linear_stage_is_input_independent():
    clips=fixture(); copies=[c.samples.copy() for c in clips]
    rows=analyze_interactions(*clips,window=(.5,5.5),min_frames=8)["band_response"]
    for row in rows.values():
        a=row["main_on_dry"];b=row["main_after_recording"]
        assert a["status"]==b["status"]=="ok"
        assert abs(a["gain_median_db"]-b["gain_median_db"])<.05
        assert all(abs(v["main_gain_after_recording_minus_dry_db"])<.1 for v in row["same_input_level_differences"])
    assert all(np.array_equal(a.samples,copy) for a,copy in zip(clips,copies))

def test_nonlinear_stage_changes_transfer():
    rows=analyze_interactions(*fixture(True),window=(.5,5.5),min_frames=8)["band_response"]
    assert any(abs(v["main_on_dry"]["gain_median_db"]-v["main_after_recording"]["gain_median_db"])>.1
               for v in rows.values() if v["main_on_dry"]["status"]==v["main_after_recording"]["status"]=="ok")

def test_invalid_input_rejected():
    a=list(fixture());a[2]=Audio(a[2].samples[:-10],a[2].rate)
    with pytest.raises(ValueError,match="sample-aligned"):analyze_interactions(*a)
    a=list(fixture());a[1]=Audio(np.full_like(a[1].samples,np.nan),a[1].rate)
    with pytest.raises(ValueError,match="Non-finite"):analyze_interactions(*a)
    with pytest.raises(ValueError,match="Invalid analysis"):
        analyze_interactions(*fixture(),window=(3,7))
