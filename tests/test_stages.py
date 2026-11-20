import numpy as np
import pytest
from scipy import signal
from skell_sound_match.core import Audio
from skell_sound_match.stages import analyze_stages

def clips(sr=22050,seconds=5.5):
    t=np.arange(round(sr*seconds))/sr
    base=(.03+.04*(.5+.5*np.sin(2*np.pi*2*t)))*(np.sin(2*np.pi*220*t)+.2*np.sin(2*np.pi*1350*t)+.07*np.sin(2*np.pi*6800*t))
    rec=signal.sosfilt(signal.butter(2,300,"highpass",fs=sr,output="sos"),base)
    main=lambda x:.6*np.tanh(3*x/.1)*.1
    return tuple(Audio(z[:,None],sr) for z in (base,rec,main(base),main(rec)))

def test_stage_measurements_are_complete_and_pure():
    sources=clips()
    copies=[a.samples.copy() for a in sources]
    r=analyze_stages(*sources,windows={"early":(.5,2.5),"later":(3,5)})
    assert r["channels"]==1
    assert set(r["window_metrics"])=={"early","later"}
    assert r["window_metrics"]["early"]["recording_stage"]["body"]["median_gain_db"] < -5
    assert r["window_metrics"]["later"]["main_input_condition_delta_db"]
    assert all(np.array_equal(a.samples,b) for a,b in zip(sources,copies))

def test_rejects_invalid_files():
    args=list(clips())
    args[2]=Audio(args[2].samples[:-20],args[2].rate)
    with pytest.raises(ValueError,match="sample-aligned"):
        analyze_stages(*args)
    args=list(clips())
    b=args[1].samples.copy();b[2,0]=np.nan;args[1]=Audio(b,args[1].rate)
    with pytest.raises(ValueError,match="Non-finite"):
        analyze_stages(*args)
    with pytest.raises(ValueError,match="Invalid stage"):
        analyze_stages(*clips(),windows={"bad":(6,7)})

def test_detects_condition_dependence():
    r=analyze_stages(*clips(),windows={"check":(.7,5)})["window_metrics"]["check"]
    assert any(abs(v)>.1 for v in r["main_input_condition_delta_db"].values())
