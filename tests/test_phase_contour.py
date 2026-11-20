import hashlib
from pathlib import Path
import json
import numpy as np
import pytest
import soundfile as sf
from scipy import signal
from skell_sound_match.phase_contour import (require_same_take_pair,MatchError,fit_fir,render,
                           fit_and_render,write_verified,active_mono)

def sine_fixture(sr=44100,sec=8):
    t=np.arange(sr*sec)/sr
    x=(0.02*np.sin(2*np.pi*221*t) + 0.04*np.sin(2*np.pi*1193*t))*(0.5+0.5*np.sin(2*np.pi*1.7*t))
    x+=0.003*np.sin(2*np.pi*4000*t)
    return x,sr

def test_reject_mismatched_rates():
    x,sr=sine_fixture()
    with pytest.raises(MatchError):require_same_take_pair(x,x,sr,sr+1)

def test_reject_nonfinite_and_silent():
    x,sr=sine_fixture()
    y=x.copy();y[44]=np.nan
    with pytest.raises(MatchError):require_same_take_pair(x,y,sr,sr)
    with pytest.raises(MatchError):require_same_take_pair(np.zeros_like(x),x,sr,sr)

def test_fir_uses_training_only():
    x,sr=sine_fixture();r=x.copy()
    r[6*sr:]=np.random.default_rng(123).normal(0,.03,len(r)-6*sr)
    h1=fit_fir(x,x,sr,train=(1,4.5))
    h2=fit_fir(x,r,sr,train=(1,4.5))
    np.testing.assert_array_equal(h1,h2)

def test_known_linear_phase_filter_improves_unseen_section():
    x,sr=sine_fixture()
    # shifted equalized reference with stable linear distortion
    ref=signal.lfilter([.58,.25,.17],[1],x)
    h=fit_fir(x,ref,sr,train=(1,4.5))
    assert np.isfinite(h).all() and len(h)==4095
    y=signal.fftconvolve(x,h,mode='same')
    sl=slice(5*sr,7*sr)
    corr=lambda a,b: np.dot(a,b)/np.sqrt((a@a)*(b@b))
    assert corr(ref[sl],y[sl])>corr(ref[sl],x[sl])

def test_render_rejects_model_errors():
    x,sr=sine_fixture();bad={'sample_rate':sr,'tap_count':1,'fir':[np.nan]}
    with pytest.raises(MatchError):render(x,x,sr,bad)
    with pytest.raises(MatchError):render(x,x,sr+1,{'sample_rate':sr,'tap_count':1,'fir':[1.]})

def test_no_overwrite_or_source_mutation(tmp_path):
    x,sr=sine_fixture()
    y=tmp_path/'out.wav';m=tmp_path/'model.json'
    mdata={'version':'synthetic','sample_rate':sr,'tap_count':1,'fir':[1.], 'contour':None}
    source=tmp_path/'dry.wav';sf.write(source,x,sr)
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    write_verified(y,m,x,sr,mdata)
    with pytest.raises(FileExistsError):write_verified(y,m,x,sr,mdata)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before

def test_saved_model_replay(tmp_path):
    x,sr=sine_fixture()
    model={'sample_rate':sr,'tap_count':1,'fir':[1.0],'contour':None}
    y,m=write_verified(tmp_path/'test.wav',tmp_path/'model.json',x,sr,model)
    a,_=render(x,x,sr,json.loads(m.read_text()))
    b,_=render(x,x,sr,json.loads(m.read_text()))
    np.testing.assert_array_equal(a,b)

def test_stereo_difference_rejected(tmp_path):
    x,sr=sine_fixture()
    p=tmp_path/'stereo.wav';sf.write(p,np.stack((x,-x),axis=1),sr)
    with pytest.raises(MatchError):active_mono(p)