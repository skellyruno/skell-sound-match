import numpy as np
from skell_sound_match.wav_only.periodic_effect_match import fit,render


def test_time_varying_model_replays_and_holdout_never_changes_fit():
    sr=32000;rng=np.random.default_rng(414);x=rng.normal(0,.02,(sr*5,2));x[:,1]=x[:,0]
    t=np.arange(len(x))/sr;y=x*(.6+.2*np.sin(2*np.pi*.4*t))[:,None]
    model,meta=fit(x,y,sr,sr*3,rates=(0.,.4))
    z=render(x,sr,model)
    assert meta['selected_rate_hz']==.4
    assert np.mean((z[sr*3:]-y[sr*3:])**2)<1e-7
    changed=y.copy();changed[sr*3:]=rng.normal(0,.5,changed[sr*3:].shape)
    another,_=fit(x,changed,sr,sr*3,rates=(0.,.4))
    assert np.array_equal(model['weights'],another['weights'])
    independent=rng.normal(0,.02,x.shape);independent[:,1]=independent[:,0]
    assert np.isfinite(render(independent,sr,model)).all()
