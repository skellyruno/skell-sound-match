import numpy as np
import pytest
from skell_sound_match.wav_only.activity88 import selection_windows,selection_objective

def metric(x,t):return {'score':float(np.mean((x-t)**2))}
def test_frozen_final_window():
 a,b,v,t,f=selection_windows(100,100100);assert a==30100 and b==70100 and f==slice(70100,100100);assert v.stop<t.start<b
def test_ignore_final_target():
 x=np.ones((100000,2),'f')*.1;a,b,v,t,f=selection_windows(0,len(x));y=x.copy();s,w=selection_objective(x,y,v,t,metric);r=s(x);y[f]*=100;s2,w2=selection_objective(x,y,v,t,metric);assert r==s2(x) and w==w2==.2
def test_silent_tail_and_active_reject():
 x=np.ones((100000,2),'f')*.1;a,b,v,t,f=selection_windows(0,len(x));y=x.copy();y[t]=0;s,w=selection_objective(x,y,v,t,metric);assert w==0;x[v]=0
 with pytest.raises(ValueError):selection_objective(x,y,v,t,metric)
def test_short_rejected():
 with pytest.raises(ValueError):selection_windows(0,1000)
