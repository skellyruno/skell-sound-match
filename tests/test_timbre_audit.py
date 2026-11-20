import numpy as np
import pytest
from skell_sound_match.core import Audio
from skell_sound_match.timbre_audit import analyze_timbre

def example(sr=16000,dur=1.8):
    t=np.arange(round(sr*dur))/sr
    rng=np.random.default_rng(123)
    voiced=.16*np.sin(2*np.pi*240*t)*(1+.2*np.sin(2*np.pi*3*t))
    noisy=np.where(t>.9,.02*rng.normal(size=len(t)),0)
    return Audio((voiced+noisy)[:,None],sr)

def test_identical_has_zero_error():
    x=example();z=analyze_timbre(x,x,hop=160)
    assert z['active_frames']>0
    assert all(b['all_mean_abs_error_db']<1e-10 for b in z['bands'])

def test_band_difference_measurable():
    x=example(sr=44100)
    t=np.arange(len(x.samples))/x.rate
    y=Audio(x.samples+0.015*np.sin(2*np.pi*10000*t)[:,None],x.rate)
    z=analyze_timbre(x,y,hop=160)
    hi=max(z['bands'],key=lambda b:b['frequency_high_hz'])
    assert hi['all_mean_abs_error_db']>1.0

def test_mismatches_rejected():
    x=example()
    for y in [Audio(x.samples[:20000],x.rate),Audio(x.samples,x.rate+1000),Audio(np.column_stack((x.samples,x.samples)),x.rate)]:
        with pytest.raises(ValueError):analyze_timbre(x,y)

def test_invalid_parameters_rejected():
    x=example()
    for kw in [{'flatness_split':-1},{'hop':0},{'active_floor_db':0},{'fft_size':8}]:
        with pytest.raises(ValueError):analyze_timbre(x,x,**kw)

def test_nan_rejected():
    x=example();a=x.samples.copy();a[100]=np.nan
    with pytest.raises(ValueError):analyze_timbre(x,Audio(a,x.rate))
