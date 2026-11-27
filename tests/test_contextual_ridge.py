import numpy as np
import pytest
from skell_sound_match.wav_only.contextual_ridge import fit_complex_ridge, replay_complex_ridge

def data():
    r=np.random.default_rng(66)
    x=(r.normal(size=(200,9,3))+1j*r.normal(size=(200,9,3))).astype('complex64')
    h=(r.normal(size=(9,3,2))+1j*r.normal(size=(9,3,2))).astype('complex64')
    y=replay_complex_ridge(x,h);m=np.arange(200)<140
    return x,y,m

def test_known_transfer():
    x,y,m=data();h=fit_complex_ridge(x,y,m,1e-5);p=replay_complex_ridge(x,h)
    assert np.linalg.norm(p[~m]-y[~m])/np.linalg.norm(y[~m])<1e-4

def test_holdout_does_not_change_weights():
    x,y,m=data();h=fit_complex_ridge(x,y,m);y[~m]=np.nan;x[~m]=np.nan
    np.testing.assert_array_equal(h,fit_complex_ridge(x,y,m))

def test_zero_features_finite():
    h=fit_complex_ridge(np.zeros((4,2,3)),np.ones((4,2,2)),np.ones(4,bool))
    assert np.isfinite(h).all() and not np.any(h)

@pytest.mark.parametrize('bad',['mask','reg','input','target','shape'])
def test_invalid(bad):
    x,y,m=data();r=.025
    if bad=='mask':m[:]=False
    if bad=='reg':r=0
    if bad=='input':x[0]=np.inf
    if bad=='target':y[0]=np.nan
    if bad=='shape':y=y[:199]
    with pytest.raises(ValueError):fit_complex_ridge(x,y,m,r)

def test_replay_shape_rejected():
    x,y,m=data();h=fit_complex_ridge(x,y,m)
    with pytest.raises(ValueError):replay_complex_ridge(x[:,:,:2],h)
