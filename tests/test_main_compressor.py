import numpy as np
import pytest
from skell_sound_match.main_compressor import Compressor,render,fit,gain_curve,metrics


def audio(sr=44100,seconds=3):
    t=np.arange(sr*seconds)/sr
    a=.03+.4*(.5+.5*np.sin(2*np.pi*2.1*t))**4
    x=a*np.sin(2*np.pi*170*t)
    return np.column_stack([x,.5*x]).astype('float32')


def test_unity_and_link():
    x=audio();assert np.array_equal(x,render(x,44100,Compressor()))
    y=render(x,44100,Compressor(slope=.75));assert np.array_equal(y[:,0],2*y[:,1]);assert np.max(abs(y))<np.max(abs(x))


def test_causality_and_rates():
    for sr in (32000,44100,48000,96000,192000):
        x=audio(sr,1);r=Compressor(slope=.6,knee=3,wet=.8);y=render(x,sr,r)
        z=x.copy();z[sr//2:]=.5
        assert np.array_equal(y[:sr//2],render(z,sr,r)[:sr//2]);assert np.isfinite(y).all()


def test_curve():
    level=np.array([-30,-21,-18,-15,-10.]);g=gain_curve(level,-18,.5,6)
    assert g[0]==g[1]==0 and g[2]==-.375 and g[-1]==-4
    assert np.all(np.diff(g)<=0)
    assert np.allclose(gain_curve(level,-18,.5,0),[0,0,0,-1.5,-4])


def test_validation():
    x=audio()
    with pytest.raises(ValueError):render(x,44100,Compressor(wet=1.2))
    with pytest.raises(ValueError):fit(x,-x,44100)
    with pytest.raises(ValueError):metrics(x,x[:-1],44100)


def test_identification():
    x=audio(32000);y=render(x,32000,Compressor(fast_ms=10,slow_ms=70,threshold=-24,slope=.7,knee=3,makeup=1.4))
    r,b,info=fit(x,y,32000);k=info['split_frame'];a=metrics(render(x,32000,b)[k:],y[k:],32000);c=metrics(render(x,32000,r)[k:],y[k:],32000)
    assert c['relative_rms']<.5*a['relative_rms']
