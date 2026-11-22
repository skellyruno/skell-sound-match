import pathlib, tempfile
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.wav_only.skelly_reference_eq_trial import (
    CENTERS, peaking, apply_eq, linked_leveler, weighted_fit, env_mae, band_mae, truepeak, match,
)

SR=44100

def test_biquads_identity_and_finite():
    x=np.random.default_rng(14).normal(0,.02,(SR,2))
    y=apply_eq(x,SR,[0.]*len(CENTERS))
    assert np.max(np.abs(y-x))<1e-11
    assert np.isfinite(y).all()


def test_biquad_musical_band_response():
    rng=np.random.default_rng(33)
    x=rng.normal(0,.02,(SR*2,2))
    y=apply_eq(x,SR,[0,0,0,0,0,0,3,0])
    assert np.max(np.abs(y))<1
    assert band_mae(y,x,SR)[0]>0


def test_stereo_leveler_block_parity_no_leak():
    rng=np.random.default_rng(7)
    x=rng.normal(0,.01,(SR//2,2));x[5000:10000,:]=0
    whole,_=linked_leveler(x,SR,-.4,.025)
    state=None;parts=[]
    for pos in range(0,len(x),127):
        y,state=linked_leveler(x[pos:pos+127],SR,-.4,.025,state=state)
        parts.append(y)
    block=np.vstack(parts)
    assert np.max(np.abs(whole-block))<1e-12
    assert np.isfinite(whole).all()
    # Identical channels must remain identical: gain is stereo linked.
    mono=np.repeat(x[:,0:1],2,axis=1)
    yy,_=linked_leveler(mono,SR,-.5,.025)
    assert np.array_equal(yy[:,0],yy[:,1])


def test_reject_invalid_leveler_and_nonfinite():
    with pytest.raises(ValueError):linked_leveler(np.zeros((100,2)),SR,.3)
    with pytest.raises(ValueError):linked_leveler(np.array([[np.nan,0.]]),SR)


def test_same_take_guard_and_nonoverlap(tmp_path):
    sr=44100;n=sr*3;t=np.arange(n)/sr
    x=np.column_stack((.015*np.sin(2*np.pi*170*t),.015*np.sin(2*np.pi*170*t)))
    f1=tmp_path/'a.wav';f2=tmp_path/'b.wav'
    sf.write(f1,x,sr,subtype='PCM_24');sf.write(f2,x[:n-1],sr,subtype='PCM_24')
    with pytest.raises(ValueError,match='Same-take'):
        match(f1,f2,(0,1),(1.5,2.5))
    sf.write(f2,x,sr,subtype='PCM_24')
    with pytest.raises(ValueError,match='overlap'):
        match(f1,f2,(0,2),(1,2.8))


def test_fit_improves_known_eq_under_holdout():
    sr=44100;t=np.arange(sr*4)/sr
    # Broadband shaped signal with a repeated but not identical holdout.
    x=np.random.default_rng(66).normal(0,.01,(len(t),2))
    source=x[:sr*2];target=apply_eq(source,sr,[0,0,2,3,1,-1,1,0])
    gains=weighted_fit(source[:sr],target[:sr],sr)
    candidate=apply_eq(source[sr:],sr,gains)
    initial=band_mae(target[sr:],source[sr:],sr)[0]
    improved=band_mae(target[sr:],candidate,sr)[0]
    assert improved<initial


def test_truepeak_and_bounded_output():
    x=np.zeros((30000,2));x[1000]=.5
    assert truepeak(x)<-1
    assert truepeak(x*10)>0

def test_end_to_end_preview_valid_pcm24_and_safe_peak(tmp_path):
    sr=44100
    rng=np.random.default_rng(101)
    x=rng.normal(0,.012,(sr*4,2))
    original=tmp_path/'dry.wav';target=tmp_path/'wet.wav';output=tmp_path/'trial.flac'
    sf.write(original,x,sr,subtype='PCM_24')
    reference=apply_eq(x,sr,[1,-1,2,1,-2,2,1,0])
    sf.write(target,reference,sr,subtype='PCM_24')
    report=match(original,target,(0,1.5),(2,3.6),output)
    y,r=sf.read(output,dtype='float64',always_2d=True)
    assert r==sr and y.shape==x.shape
    assert sf.info(output).subtype=='PCM_24'
    assert np.isfinite(y).all() and truepeak(y)<=-1.19
    assert report['scores']['holdout']['band_improvement_db']>0
    with pytest.raises(FileExistsError):match(original,target,(0,1.5),(2,3.6),output)
