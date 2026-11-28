import numpy as np
import pytest
from skell_sound_match.wav_only.vocal_envelope import analyse,compare
SR=32000

def fixture():
 t=np.arange(2*SR)/SR; x=sum(np.sin(2*np.pi*180*k*t)/k for k in range(1,18))*.1
 return x,(np.arange(0,2.01,.01),np.full(201,180.))

def test_gain_and_polarity():
 x,f=fixture();a=analyse(x,SR,f0=f); b=analyse(np.column_stack([x,-x])*.3,SR,f0=f)
 m=compare(a,b);assert m['envelope_mae_db']<1e-6 and m['harmonic_fraction_error']<1e-6

def test_filter_difference():
 from scipy.signal import butter,sosfilt
 x,f=fixture();a=analyse(x,SR,f0=f);b=analyse(sosfilt(butter(2,1000,fs=SR,output='sos'),x),SR,f0=f)
 assert compare(b,a)['envelope_mae_db']>3

def test_invalid():
 x,f=fixture();a=analyse(x,SR,f0=f)
 with pytest.raises(ValueError): analyse(x,SR,f0=([0,0],[180,180]))
 with pytest.raises(ValueError): compare(a,analyse(np.zeros_like(x),SR,f0=f))
 with pytest.raises(ValueError): compare(a,analyse(x[:-320],SR,f0=f))
 with pytest.raises(ValueError): compare(a,analyse(x,SR,f0=(f[0],f[1]*2)))


def test_bounds():
 x,f=fixture();a=analyse(x,SR,f0=f)
 with pytest.raises(ValueError): analyse(x*1000,SR,f0=f)
 with pytest.raises(ValueError): compare(a,a,min_frames=0)
