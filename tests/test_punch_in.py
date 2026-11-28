import numpy as np
import pytest
from skell_sound_match.punch_in import Region,detect_regions,blend_regions

def test_detect_separate_regions():
    sr=16000;t=np.arange(sr*5)/sr;x=np.zeros_like(t)
    for s,e in ((.4,1.5),(2.2,3.3)):
        on=(t>=s)&(t<e);x[on]=.12*np.sin(2*np.pi*220*t[on])
    r=detect_regions(x[:,None],sr)
    assert len(r)==2
    assert abs(r[0].start-.4)<.06 and abs(r[1].start-2.2)<.06

def test_blend_crossfades_only_in_gaps():
    sr=16000;n=sr*3;a=np.zeros((n,1));b=np.ones_like(a)*.5
    y=blend_regions(a,b,sr,[Region(.3,1.),Region(2.,2.7)],[0,1])
    assert np.allclose(y[round(.5*sr)],a[round(.5*sr)])
    assert np.allclose(y[round(2.3*sr)],b[round(2.3*sr)])
    assert np.all(np.diff(y[round(1.01*sr):round(1.99*sr),0])>=-1e-10)

def test_zero_weight_preserves_champion_exactly():
    sr=16000;a=np.random.default_rng(1).normal(size=(sr*3,2))*.02
    assert np.array_equal(blend_regions(a,a+.001,sr,[Region(.2,.8),Region(1.3,2.2)],[0,0]),a)

def test_reject_overlap_missing_and_unsafe_weights():
    sr=16000;a=np.zeros((sr*3,1))
    for r,w in [([Region(.5,1.5),Region(1.,2.)],[0,1]),
                ([Region(0,1)],[]),([Region(0,1)],[1.2])]:
        with pytest.raises(ValueError):blend_regions(a,a,sr,r,w)

def test_reject_invalid_audio():
    sr=16000;a=np.zeros((sr,1));bad=a.copy();bad[0,0]=np.nan
    with pytest.raises(ValueError):blend_regions(a,bad,sr,[Region(0,.5)],[.5])
    with pytest.raises(ValueError):blend_regions(a,np.zeros((sr,2)),sr,[Region(0,.5)],[.5])

def test_preserve_attacks_inside_each_phrase():
    sr=16000;n=sr*4;a=(.1*np.sin(2*np.pi*200*np.arange(n)/sr))[:,None]
    b=a*.75
    r=[Region(.5,1.4),Region(2.2,3.7)]
    y=blend_regions(a,b,sr,r,[0,1])
    assert np.array_equal(y[round(.5*sr):round(1.4*sr)],a[round(.5*sr):round(1.4*sr)])
    assert np.array_equal(y[round(2.2*sr):round(3.7*sr)],b[round(2.2*sr):round(3.7*sr)])
