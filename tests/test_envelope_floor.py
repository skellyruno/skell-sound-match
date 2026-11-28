import numpy as np
from skell_sound_match.wav_only.vocal_knob_search import _features, _score, Window


def test_silence_does_not_reward_static_gain_as_dynamics_improvement():
    sr=44100
    t=np.arange(sr)/sr
    signal=np.zeros(sr)
    signal[sr//2:]=.1*np.sin(2*np.pi*440*t[sr//2:])
    stereo=np.column_stack((signal,signal))
    window=Window(0,1)
    ref=_features(stereo,sr,window)
    for gain in (.1,.5,2.):
        result=_score(ref,_features(stereo*gain,sr,window))
        assert result['envelope_mae_db']<.0001
