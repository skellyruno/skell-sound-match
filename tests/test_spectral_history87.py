import numpy as np
import pytest
from skell_sound_match.wav_only import spectral_history87 as s

def audio(n=32768):return np.random.default_rng(87).normal(0,.03,(n,2)).astype('f')
@pytest.mark.parametrize('objective',[0,1])
def test_fit_replay_finite(objective):
 x=audio();p,q,z=s.prepare(x,x*.5);r=s.c.power(s.c.spec(x));m=s.fit(p,q,r,0,len(x),1.,1,objective);out=s.apply(x,x*.5,m,.8);assert out.shape==x.shape and np.isfinite(out).all()
def test_no_target_leakage():
 x=audio(65536);p,q,z=s.prepare(x,x);t=q.copy();stop=32768;a=s.fit(p,q,t,0,stop,1.,1,0);t[128:]*=100;b=s.fit(p,q,t,0,stop,1.,1,0);np.testing.assert_array_equal(a['coef'],b['coef'])
def test_zero_amount():
 x=audio();np.testing.assert_array_equal(s.apply(x,x,None,0),x)
def test_silence_finite():
 x=np.zeros((32768,2),'f');p,q,z=s.prepare(x,x);m=s.fit(p,q,q,0,len(x),1.,1,0);assert np.isfinite(s.apply(x,x,m,1.)).all()
def test_short_rejected():
 x=audio(4096);p,q,z=s.prepare(x,x)
 with pytest.raises(ValueError):s.fit(p,q,q,0,len(x),1.,0,0)
