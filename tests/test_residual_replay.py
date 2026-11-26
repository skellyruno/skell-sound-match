import numpy as np
import pytest
from skell_sound_match.wav_only.residual_replay import replay_residual


def go(x, **kw):
    args = dict(taps=[0, 2], coefficients=[[.1, .2], [.1, .2]], dynamic=False, scale=.1)
    args.update(kw)
    return replay_residual(x, **args)


def test_causal_impulse():
    x = np.zeros((20, 2), np.float32); x[4] = [.5, -.25]
    y = go(x)
    assert np.all(y[:4] == 0)
    assert np.allclose(y[4], x[4] * 1.1)
    assert np.allclose(y[6], x[4] * .2)
    assert np.all(y[7:] == 0)


def test_frozen_prefix():
    x = np.random.default_rng(1).uniform(-.2, .2, (500, 2)).astype('f')
    a = dict(dynamic=True, coefficients=[[.1, .2, -.1], [-.1, 0, .1]])
    assert np.array_equal(go(x, **a)[:250], go(x[:250], **a))


@pytest.mark.parametrize('kw', [dict(taps=[-1,2]),dict(taps=[2,0]),dict(taps=[0,0]),dict(taps=[0,129]),dict(coefficients=[[.5,0],[0,0]]),dict(scale=0),dict(scale=float('nan')),dict(dynamic=True)])
def test_reject(kw):
    with pytest.raises(ValueError):go(np.zeros((20,2)), **kw)


@pytest.mark.parametrize('x', [np.zeros((3,1)), np.zeros((0,2)), np.full((2,2),np.nan)])
def test_source(x):
    with pytest.raises(ValueError):go(x)
