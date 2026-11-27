"""Fit a causal native EightBandTone EQ from paired, aligned training audio.

The reference is used only to choose static parameters. The return value is
editable normalized controls, not an audio-dependent FIR or a runtime target.
Callers must use a separate validation region, then test the native processor.
"""
import numpy as np
from scipy import signal, optimize

EDGES = np.array([35., 90., 185., 380., 820., 1700., 3600., 7500., 17500.])


def fit_phase_eq(source, target, sample_rate=44100, low_cut=True, max_nfev=55):
    """Return native p/Q/low-cut controls and a diagnostic transfer-fit error."""
    x = np.asarray(source, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    sr = float(sample_rate)
    if x.shape != t.shape or x.ndim != 2 or x.shape[1] != 2 or len(x) < 4096:
        raise ValueError('expected equal aligned stereo training audio')
    if not np.isfinite(x).all() or not np.isfinite(t).all() or not 32000 <= sr <= 192000:
        raise ValueError('invalid audio or sample rate')
    x, t = x.mean(axis=1), t.mean(axis=1)
    f, px = signal.welch(x, sr, nperseg=2048)
    _, pt = signal.welch(t, sr, nperseg=2048)
    _, xy = signal.csd(x, t, sr, nperseg=2048)
    coherence = np.clip(abs(xy)**2 / np.maximum(px*pt, 1e-30), 0, 1)
    mask = (f >= 65) & (f < min(15000, sr*.45)) & (px > px.max()*1e-6) & (pt > pt.max()*1e-6)
    f, px, pt, xy, coherence = f[mask], px[mask], pt[mask], xy[mask], coherence[mask]
    if len(f) < 10:
        raise ValueError('insufficient paired spectral support')
    desired = xy / np.maximum(px, 1e-20)
    z = np.exp(-2j*np.pi*f/sr)
    z2 = z*z
    weight = np.sqrt(np.maximum(coherence, .015)/np.maximum(f, 60.))
    weight /= np.sqrt(np.mean(weight**2))
    norm = np.maximum(np.sqrt(pt/px), 1e-4)
    confidence = np.minimum(1., np.sqrt(coherence)*2.)

    def model(p):
        g, q = p[:8], p[8:16]
        centers = EDGES[:-1]*(EDGES[1:]/EDGES[:-1])**p[16:24]
        amplitude = 10**(g/40)
        w = 2*np.pi*centers/sr
        c, a = np.cos(w), np.sin(w)/(2*q)
        a = a[:, None]
        c = c[:, None]
        amplitude = amplitude[:, None]
        h = (1+a*amplitude-2*c*z+(1-a*amplitude)*z2)/(1+a/amplitude-2*c*z+(1-a/amplitude)*z2)
        response = np.prod(h, axis=0)*10**(p[24]/20)
        if low_cut:
            w = 2*np.pi*(20*20**p[25])/sr
            c, a = np.cos(w), np.sin(w)/np.sqrt(2)
            response *= ((1+c)/2*(1-2*z+z2))/(1+a-2*c*z+(1-a)*z2)
        return response

    def residual(p):
        h = model(p)
        e = (h-desired)/norm
        magnitude = np.log(np.maximum(abs(h), 1e-6)/norm)
        return np.r_[weight*confidence*e.real, weight*confidence*e.imag,
                     weight*magnitude*.35, p[:8]*.018, (p[16:24]-.5)*.12]

    ratio = np.sqrt(np.mean(t*t))/max(np.sqrt(np.mean(x*x)), 1e-8)
    g = np.clip(20*np.log10(max(ratio, 1e-12)), -29, 29)
    start = np.r_[[0.]*8, [.8]*8, [.5]*8, g, .3]
    lower = np.r_[[-15.]*8, [.4]*8, [0.]*8, -30., 0.]
    upper = np.r_[[15.]*8, [8.]*8, [1.]*8, 30., 1.]
    p = optimize.least_squares(residual, start, bounds=(lower, upper),
                               max_nfev=max_nfev, ftol=1e-4, xtol=1e-4).x
    params = [v for k in range(8) for v in (float(p[16+k]), float(.5+p[k]/30))]
    return {'params': params,
            'eqQ': (np.log(p[8:16]/.4)/np.log(20)).tolist(),
            'eqLowCut': float(p[25]) if low_cut else 0.,
            'gainDb': float(p[24]),
            'meanCoherence': float(np.mean(coherence)),
            'fitError': float(np.mean(abs(model(p)-desired)/norm))}
