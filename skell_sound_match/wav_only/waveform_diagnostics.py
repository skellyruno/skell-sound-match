"""Separate sample-alignment diagnostics from time-frequency magnitude error.
Never substitute these measurements for the existing composite score or peak guard.
"""
import numpy as np
from scipy import signal


def compare_waveforms(candidate, reference, sample_rate=44100):
    x, y = (np.asarray(v, dtype=np.float64) for v in (candidate, reference))
    if (x.shape != y.shape or x.ndim != 2 or x.shape[1] != 2 or len(x) < 2048
            or not np.isfinite(x).all() or not np.isfinite(y).all()
            or not 8000 <= sample_rate <= 192000):
        raise ValueError('expected finite, aligned stereo recordings')
    yy = float(np.sum(y*y))
    xx = float(np.sum(x*x))
    if yy < 1e-20 or xx < 1e-20:
        raise ValueError('insufficient signal energy')
    xy = float(np.sum(x*y))
    corr = float(np.clip(xy/np.sqrt(xx*yy), -1., 1.))
    scalar = xy/yy
    residual = float(np.sqrt(np.sum((x-scalar*y)**2)/xx))
    magnitude = {}
    for n in (512, 1024, 2048):
        _, _, a = signal.stft(x, fs=sample_rate, nperseg=n, noverlap=3*n//4, axis=0)
        _, _, b = signal.stft(y, fs=sample_rate, nperseg=n, noverlap=3*n//4, axis=0)
        a, b = abs(a), abs(b)
        peak = float(b.max())
        floor = max(peak*.001, 1e-7)
        active = b > max(peak*.01, 1e-7)
        if not active.any():
            raise ValueError('insufficient active spectral bins')
        magnitude[str(n)] = float(np.mean(abs(20*np.log10((a[active]+floor)/(b[active]+floor)))))
    return {'signed_waveform_correlation': corr, 'least_squares_gain': scalar,
            'gain_fit_relative_residual': residual,
            'active_stft_magnitude_error_db': magnitude}
