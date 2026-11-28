import numpy as np
import pytest
from skell_sound_match.wav_only.stereo_delay_match import extend_decay,render


def test_geometric_extension_recovers_frozen_echo_tail():
    sr=32000;delay=1000;h=np.zeros((delay*3+17,2,2))
    for k in range(1,4):h[k*delay]=np.eye(2)*.2*.5**(k-1)
    model,report=extend_decay({'sample_rate':sr,'impulse':h},delay,3,8)
    assert abs(report['train_inferred_feedback']-.5)<1e-12
    x=np.zeros((10000,2));x[0]=[1,.5]
    y=render(x,sr,model)
    np.testing.assert_allclose(y[8000],[.2*.5**7,.1*.5**7],atol=1e-12)
    np.testing.assert_allclose(render(x[:1500],sr,model),y[:1500],atol=1e-12)
    with pytest.raises(ValueError):extend_decay({'impulse':h},delay+1,3,8)
