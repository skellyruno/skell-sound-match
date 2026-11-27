import numpy as np
import pytest
from skell_sound_match.wav_only.local_context_regression import local_ridge


def data():
    rng=np.random.default_rng(68); x=rng.normal(size=(400,5)).astype('f'); h=rng.normal(size=(5,3)).astype('f'); q=rng.normal(size=(30,5)).astype('f');return x,x@h,q,q@h


def test_recovers_affine_mapping():
    x,y,q,t=data(); p=local_ridge(x,y,q,neighbors=64,components=5,ridge=.00001);np.testing.assert_allclose(p,t,atol=.002)


def test_query_batch_invariance():
    x,y,q,_=data();a=local_ridge(x,y,q,batch_size=7);b=local_ridge(x,y,q,batch_size=128);np.testing.assert_allclose(a,b,atol=1e-6)


def test_duplicate_descriptors_finite():
    x=np.ones((5,2),'f');y=np.full((5,2),2.,'f');p=local_ridge(x,y,x);assert np.isfinite(p).all();np.testing.assert_allclose(p,y,atol=.002)


def test_empty_queries():
    x,y,q,_=data();assert local_ridge(x,y,q[:0]).shape==(0,3)


@pytest.mark.parametrize('bad',['shape','nan','k','ridge','bool'])
def test_invalid(bad):
    x,y,q,_=data();kw={}
    if bad=='shape':q=q[:,:2]
    if bad=='nan':x[0,0]=np.nan
    if bad=='k':kw['neighbors']=1
    if bad=='ridge':kw['ridge']=0.
    if bad=='bool':kw['components']=True
    with pytest.raises(ValueError):local_ridge(x,y,q,**kw)
