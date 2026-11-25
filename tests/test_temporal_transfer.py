import numpy as np
import pytest
from skell_sound_match.temporal_transfer import temporal_profile,compare,refine
from skell_sound_match.reference_transfer import Recipe,render


def voice(rate=44100):
    t=np.arange(3*rate)/rate
    amp=.12*(.5+.5*np.sin(2*np.pi*2.3*t))**2
    x=amp*(np.sin(2*np.pi*180*t)+.3*np.sin(2*np.pi*570*t))
    return np.column_stack([x,x]).astype('float32')


def test_gain_invariance():
    x=voice();d=compare(temporal_profile(x,44100),temporal_profile(x*.5,44100))
    assert d['guarded_score']<1e-4
    assert abs(d['level_gap_db']-6.0206)<.001


def test_pause_detection():
    x=voice();y=x.copy();y[44100:66150]=0
    a,b=temporal_profile(x,44100),temporal_profile(y,44100)
    assert b['quiet_fraction'][1]>a['quiet_fraction'][1]+.1
    assert compare(a,b)['guarded_score']>0


def test_sample_rate():
    for sr in (32000,48000,96000,192000):
        p=temporal_profile(voice(sr),sr)
        assert np.isfinite(p['articulation']).all()


def test_insufficient():
    with pytest.raises(ValueError): temporal_profile(np.zeros((10000,2)),44100)
    with pytest.raises(ValueError): refine([(voice(),44100)],voice(),44100,Recipe())


def test_refinement_boundaries():
    x=voice();initial=Recipe();q,info=refine([(x,44100),(x*.7,44100)],x,44100,initial)
    assert q==initial and not info['selected']
    assert q.echo==q.room==0
    assert np.array_equal(render(x,44100,q),x)
