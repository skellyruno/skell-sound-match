import numpy as np,pytest
from skell_sound_match.wav_only import fir95 as f,robust_selection95 as s

def test_known_stereo_transfer():
 x=np.random.default_rng(95).normal(0,.1,(32768,2)).astype('f');q=np.array([[.3,.2],[-.1,.6]],'f');t=x@q;h=f.fit(x,t,0,20000,.01,nfft=1024,lead=32,length=128);y=f.apply(x,h,32);assert np.mean((y[21000:]-t[21000:])**2)<np.mean(t[21000:]**2)*.04

def test_exclude_later_target():
 x=np.random.default_rng(95).normal(0,.1,(32768,2)).astype('f');t=x*.2;a=f.fit(x,t,0,16384,.1,1024,32,128);t[16384:]*=500;b=f.fit(x,t,0,16384,.1,1024,32,128);np.testing.assert_array_equal(a,b)

def test_silence_finite():
 x=np.zeros((8192,2),'f');h=f.fit(x,x,0,len(x),.1,1024,32,128);assert np.isfinite(h).all() and not f.apply(x,h,32).any()

def test_short_train():
 x=np.zeros((1024,2),'f');
 with pytest.raises(ValueError):f.fit(x,x,0,1024,.1,1024,32,128)

def test_selection_guards():
 assert s.validate_windows([slice(12,20),slice(22,28)],10,30,2)==(slice(12,20),slice(22,28))
 for windows in ([slice(9,20)],[slice(12,20),slice(19,22)],[slice(12,31)]):
  with pytest.raises(ValueError):s.validate_windows(windows,10,30,2)

def test_relative_regret():
 assert s.regret([2,4,.5],[2,4,.5])==1.;assert s.regret([1,2,.5],[2,4,.5])<1.;assert s.regret([2,4,1],[2,4,.5])>1.;
 with pytest.raises(ValueError):s.regret([1,np.nan],[1,1])
