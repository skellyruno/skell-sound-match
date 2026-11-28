import numpy as np
import pytest
from skell_sound_match import research_r4 as r

SR = 44100

def sample(f=180, n=44100):
    t=np.arange(n)/SR
    x=.12*(np.sin(2*np.pi*f*t)+.25*np.sin(2*np.pi*f*5*t))*(.6+.4*np.sin(2*np.pi*3*t)**2)
    return np.stack([x,x],axis=1)

def test_fixed_activity_gain_invariance():
    x=sample(); t=np.arange(0,1,.01); track=(t,np.full_like(t,180.))
    a=r.shape(x,SR,track,x); b=r.shape(x*.3,SR,track,x)
    assert a.keys()==b.keys() and r.distance(a,b)<1e-7
    c=r.shape(np.zeros_like(x),SR,track,x)
    assert c.keys()==a.keys() and r.distance(a,c)>1

def test_invalid_geometry_and_track():
    x=sample(); track=(np.array([0.,.01]),np.array([180.,180.]))
    with pytest.raises(ValueError): r.shape(x,SR,track,x[:-1])
    with pytest.raises(ValueError): r.shape(x,SR,(track[0],np.array([np.nan,0.])))
    with pytest.raises(ValueError): r.shape(x,SR,(track[0][::-1],track[1]))
    with pytest.raises(ValueError): r.shape(x,SR,track,np.zeros_like(x))
    with pytest.raises(ValueError): r.shape(x,22050,track)

def test_scalar_finish_preserves_channel_ratios():
    x=sample()*12
    y,g=r.finish(x)
    assert g<0 and r.peak_db(y)<=-1.5
    assert np.allclose(y,x*10**(g/20))
    safe=sample(); z,g=r.finish(safe); assert g==0 and np.array_equal(z,safe)
    with pytest.raises(ValueError): r.finish(x,1.)
    with pytest.raises(ValueError): r.finish(np.full_like(x,np.nan))

def test_pedalboard_fit_and_fixed_gain():
    pytest.importorskip('pedalboard'); pytest.importorskip('parselmouth')
    a,b=sample(170),sample(200)
    ref=r.render(sample(185),SR,[0,-2,0,2,0,1,0],None)
    g,th,info=r.fit([a,b],ref,SR)
    assert len(g)==7 and np.all(np.abs(g)<=10)
    assert info['evaluations']==13 and info['train_score']<=info['dry_train_score']
    for x in (a,b):
        y=r.render(x,SR,g,th)*10**(info['gain_db']/20)
        assert y.shape==x.shape and r.peak_db(y)<=-1.5+1e-4
    with pytest.raises(ValueError): r.fit([a],ref,SR)
    with pytest.raises(ValueError): r.render(a,SR,[0]*6,None)
    with pytest.raises(ValueError): r.render(a,SR,[0]*7,-100)

def test_paired_multiresolution_loss():
    torch=pytest.importorskip('torch'); torch.set_num_threads(1)
    x=sample(n=8192)
    assert r.paired_mrstft(x,x)==0
    assert r.paired_mrstft(x*.9,x)>0
    with pytest.raises(ValueError): r.paired_mrstft(x[:-1],x)
    with pytest.raises(ValueError): r.paired_mrstft(x,np.full_like(x,np.nan))
