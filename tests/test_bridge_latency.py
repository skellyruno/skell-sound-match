import numpy as np
import pytest
from skell_sound_match.wav_only.bridge_latency import render_bridge

def source():return np.arange(400,dtype='f').reshape(200,2)/400

def test_raw():
    x=source();y,l=render_bridge(x,lambda z:(np.pad(z,((44,0),(0,0)))[:len(z)],44),mode='raw',max_latency=64)
    assert l==44 and np.array_equal(x,y)

def test_aligned_no_double_crop():
    x=source();y,l=render_bridge(x,lambda z:(z.copy(),153),mode='aligned',max_latency=256)
    assert l==153 and np.array_equal(x,y)

@pytest.mark.parametrize('mode,cap',[('guess',64),('raw',-1),('aligned',True),('raw',192001)])
def test_contract(mode,cap):
    with pytest.raises(ValueError):render_bridge(source(),lambda z:(z,0),mode=mode,max_latency=cap)

@pytest.mark.parametrize('renderer',[lambda z:(z,65),lambda z:(z,True),lambda z:(z[:-1],0),lambda z:(z*np.nan,0)])
def test_bad_bridge(renderer):
    with pytest.raises(ValueError):render_bridge(source(),renderer,mode='raw',max_latency=64)
