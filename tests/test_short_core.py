import numpy as np
import pytest
from skell_sound_match.wav_only.short_core import dry_core_kernel,require_dry_core

def test_zero_lead_is_not_wrapped():
 h=np.ones((4096,2,2),'f');k=dry_core_kernel(h,taps=256);assert k.shape==(256,2,2);assert np.all(k[0]==1) and np.all(k[-1]==0)

def test_bounded_lead():
 h=np.zeros((4096,2,2),'f');h[-32:,0,0]=1;h[0,1,1]=2;k=dry_core_kernel(h,taps=768,lead=32);assert k.shape==(800,2,2) and k[32,1,1]==2 and k[31,0,0]==1 and k[0,0,0]==0

@pytest.mark.parametrize('taps,lead',[(4096,0),(128,128),(32,0),(True,0),(128,-1)])
def test_bad_support(taps,lead):
 with pytest.raises(ValueError):dry_core_kernel(np.ones((4096,2,2),'f'),taps=taps,lead=lead)

def test_no_wet():
 require_dry_core()
 with pytest.raises(ValueError):require_dry_core(spatial_features=[('room',.4,0)])
 with pytest.raises(ValueError):require_dry_core(spatial_weights=[[1,1]])
