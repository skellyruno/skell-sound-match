import unittest
import numpy as np
from scipy import signal
from skell_sound_match.wav_only.native_phase_eq import fit_phase_eq, EDGES


class NativePhaseEQTests(unittest.TestCase):
    def test_causal_filter_fit(self):
        rng = np.random.default_rng(55)
        x = rng.normal(0, .05, (44100, 2))
        t = signal.sosfilt(signal.butter(2, 175, fs=44100, btype='highpass', output='sos'), x, axis=0)
        a = 10**(7/40)
        w = 2*np.pi*1750/44100
        alpha, c = np.sin(w)/1.6, np.cos(w)
        t = signal.lfilter([1+alpha*a,-2*c,1-alpha*a], [1+alpha/a,-2*c,1-alpha/a], t, axis=0)*.7
        fit = fit_phase_eq(x[:26000], t[:26000])
        z = x[26000:].copy()
        cut = 20*20**fit['eqLowCut']
        z = signal.sosfilt(signal.butter(2, cut, fs=44100, btype='highpass', output='sos'), z, axis=0)
        for k in range(8):
            f = EDGES[k]*(EDGES[k+1]/EDGES[k])**fit['params'][2*k]
            a = 10**((fit['params'][2*k+1]-.5)*30/40)
            q = .4*20**fit['eqQ'][k]
            w = 2*np.pi*f/44100
            alpha, c = np.sin(w)/(2*q), np.cos(w)
            z = signal.lfilter([1+alpha*a,-2*c,1-alpha*a], [1+alpha/a,-2*c,1-alpha/a], z, axis=0)
        z *= 10**(fit['gainDb']/20)
        target = t[26000:]
        self.assertLess(np.linalg.norm(z[512:]-target[512:]), .6*np.linalg.norm(x[26512:]-target[512:]))
        self.assertTrue(all(0 <= v <= 1 for v in fit['params']+fit['eqQ']+[fit['eqLowCut']]))

    def test_reject_invalid_or_silent(self):
        x = np.zeros((4096, 2))
        with self.assertRaises(ValueError):
            fit_phase_eq(x, x)
        with self.assertRaises(ValueError):
            fit_phase_eq(x, x[:-1])
        x[0, 0] = np.nan
        with self.assertRaises(ValueError):
            fit_phase_eq(x, x)


if __name__ == '__main__':
    unittest.main()
