import numpy as np
from skell_sound_match.wav_only.stereo_delay_match import fit,render


def test_cross_channel_echo_retains_stereo_and_generalizes():
    sr=32000;rng=np.random.default_rng(18);x=rng.normal(0,.03,(sr*6,2));n=round(.3*sr)
    y=x.copy();y[n:,0]+=x[:-n,1]*.2;y[n:,1]+=x[:-n,0]*.15
    model,meta=fit(x,y,sr,sr*4,search=(.25,.35));z=render(x,sr,model)
    assert abs(meta['first_echo_ms']-300)<1
    assert np.mean((z[sr*4:]-y[sr*4:])**2)<1e-8
    assert np.isfinite(render(rng.normal(0,.02,x.shape),sr,model)).all()
