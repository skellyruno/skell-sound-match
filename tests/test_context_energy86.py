import numpy as np
import pytest
from skell_sound_match.wav_only import context_energy86 as c

def audio(n=32768):
    rng=np.random.default_rng(402);return rng.normal(0,.05,(n,2)).astype('f')
def test_stft_identity():
    x=audio();np.testing.assert_allclose(c.synth(c.spec(x),len(x)),x,atol=1e-6,rtol=1e-5)
def test_static_gain():
    x=audio();y=x*.5;p,q=c.prepare(x,y);t=c.power(c.spec(x));m=c.fit(p,q,t,0,len(x),.5,0);z=c.apply(x,y,m,1);np.testing.assert_allclose(z,x,atol=1e-5,rtol=1e-4)
def test_zero_amount_preserves_anchor():
    x=audio();assert np.array_equal(c.apply(x,x,None,0),x)
def test_train_mask_excludes_later_target():
    x=audio(65536);p,q=c.prepare(x,x);t=c.power(c.spec(x));a=32768;m=c.fit(p,q,t,0,a,.5,1);t[128:]*=200;n=c.fit(p,q,t,0,a,.5,1)
    for u,v in zip(m,n):np.testing.assert_array_equal(u,v)
def test_silent_seed_finite():
    x=np.zeros((32768,2),'f');p,q=c.prepare(x,x);m=c.fit(p,q,q,0,len(x),.5,1);assert np.isfinite(c.apply(x,x,m,1)).all()
def test_short_train_rejected():
    x=audio(8192);p,q=c.prepare(x,x)
    with pytest.raises(ValueError):c.fit(p,q,q,0,4096,.5,1)
