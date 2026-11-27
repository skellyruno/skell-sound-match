"""Training-only stereo echo recurrence diagnostic. No target at replay."""
import numpy as np
from scipy import signal


def stereo_echo_recurrence(main, wet_delta, min_lag, max_lag):
    """Find the dominant normalized positive-lag echo in each channel.

    Caller supplies only the allowed training prefix. Correlation is evidence
    for a recurrence, not proof of a particular delay plugin or routing.
    Returns (lag, signed correlation) per output channel; None for silence.
    """
    x = np.asarray(main, dtype=np.float64)
    y = np.asarray(wet_delta, dtype=np.float64)
    if (x.ndim != 1 or y.shape != (len(x), 2) or not len(x)
            or not np.isfinite(x).all() or not np.isfinite(y).all()
            or type(min_lag) is not int or type(max_lag) is not int
            or not 1 <= min_lag <= max_lag < len(x)):
        raise ValueError('invalid paired training data or lag bounds')
    ex = np.linalg.norm(x)
    result = []
    for c in range(2):
        ey = np.linalg.norm(y[:, c])
        if ex <= 1e-12 or ey <= 1e-12:
            result.append(None)
            continue
        corr = signal.correlate(y[:, c], x, method='fft')[len(x)-1:]
        q = corr[min_lag:max_lag+1] / (ex*ey)
        k = int(np.argmax(np.abs(q)))
        result.append((min_lag+k, float(np.clip(q[k], -1, 1))))
    return result


def diagnostic_spectrum(candidate, target, rate):
    """Auxiliary phase-insensitive magnitude and temporal-envelope diagnostics.

    No alignment correction or scoring gate is applied. These measurements
    are not perceptual listening scores; keep the original composite gate.
    """
    x = np.asarray(candidate, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    if (x.ndim != 2 or x.shape[1] != 2 or t.shape != x.shape
            or len(x) < 2048 or not np.isfinite(x).all() or not np.isfinite(t).all()
            or type(rate) is not int or not 8000 <= rate <= 192000):
        raise ValueError('expected aligned finite stereo audio')
    out = {}
    for n in (256, 1024, 2048):
        _, _, a = signal.stft(x, fs=rate, nperseg=n, noverlap=3*n//4, axis=0, boundary=None, padded=False)
        _, _, b = signal.stft(t, fs=rate, nperseg=n, noverlap=3*n//4, axis=0, boundary=None, padded=False)
        p, q = np.abs(a), np.abs(b)
        floor = max(float(q.max())*.001, 1e-10)
        w = q/(q+floor*10)
        d = np.abs(20*np.log10((p+floor)/(q+floor)))
        out[f'weighted_logmag_{n}_db'] = float(np.sum(w*d)/max(w.sum(),1e-12))
    hop=max(1,round(rate*.01)); length=len(x)//hop*hop
    a=np.sqrt(np.mean(x[:length].reshape(-1,hop,2)**2,axis=(1,2)))
    b=np.sqrt(np.mean(t[:length].reshape(-1,hop,2)**2,axis=(1,2)))
    keep=b>max(float(b.max())*.025,1e-8)
    out['active_envelope_error_db']=float(np.mean(np.abs(20*np.log10((a[keep]+1e-5)/(b[keep]+1e-5))))) if keep.any() else 0.
    def stereo(v):
        return float(np.dot(v[:,0],v[:,1])/max(np.linalg.norm(v[:,0])*np.linalg.norm(v[:,1]),1e-12))
    out['stereo_correlation_error']=abs(stereo(x)-stereo(t))
    return out
