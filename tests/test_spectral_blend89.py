import numpy as np
from skell_sound_match.wav_only import spectral_blend89 as b,context_energy86 as c

def audio(n=32768):return np.random.default_rng(89).normal(0,.03,(n,2)).astype('f')
def test_blend_zero():
 x=audio();Z=np.stack([c.spec(x),c.spec(x*.5)]);np.testing.assert_allclose(b.apply(Z,np.zeros((2,c.NB,1)),len(x),0),x,atol=1e-6)
def test_blend_convex_learns_known_gain():
 x=audio();Z=np.stack([c.spec(x*.5),c.spec(x)]);W=b.fit(Z,c.spec(x),0,len(x),.001);assert (W>=-1e-6).all() and (W.sum(-1)<=1+1e-6).all();y=b.apply(Z,W,len(x));assert np.mean((y-x)**2)<np.mean((x*.5-x)**2)*.01
def test_blend_train_excludes_later():
 x=audio(65536);Z=np.stack([c.spec(x*.5),c.spec(x)]);T=c.spec(x);a=b.fit(Z,T,0,32768,.03);T[128:]*=100;v=b.fit(Z,T,0,32768,.03);np.testing.assert_array_equal(a,v)
