"""Optional offline R4 comparator: pitch-conditioned multiresolution spectral profiles.

No pretrained weights, proprietary code, private recordings, or production preset changes.
Pedalboard is an external reference engine; Parselmouth supplies offline pitch labels.
"""
import numpy as np
from scipy import signal
from scipy.optimize import lsq_linear
from .reference_transfer import profile, distance as profile_distance

CENTERS = np.array([100, 220, 480, 1050, 2300, 5000, 10500])
EDGES = np.array([65, 150, 330, 720, 1550, 3400, 7300, 16000])


def _audio(x, sr):
    x = np.asarray(x, dtype=np.float64)
    if (x.ndim != 2 or x.shape[1] not in (1, 2) or len(x) < 4096
            or not np.isfinite(x).all() or not np.isfinite(sr)
            or not 32000 <= sr <= 192000 or int(sr) != sr):
        raise ValueError('expected finite mono/stereo frames at 32–192 kHz')
    return x


def pitch_track(x, sr):
    import parselmouth
    x = _audio(x, sr)
    pitch = parselmouth.Sound(x.mean(axis=1), sr).to_pitch(
        time_step=.01, pitch_floor=65, pitch_ceiling=550)
    return pitch.xs(), pitch.selected_array['frequency']


def shape(x, sr, track, source=None):
    """Unpaired distribution comparison. Freeze activity and pitch to dry source."""
    x = _audio(x, sr)
    source = x if source is None else _audio(source, sr)
    if source.shape != x.shape:
        raise ValueError('source geometry differs')
    times, f0 = (np.asarray(v) for v in track)
    if (times.ndim != 1 or times.shape != f0.shape or not len(times)
            or not np.isfinite(times).all() or not np.isfinite(f0).all()
            or np.any(np.diff(times) <= 0) or np.any(f0 < 0)):
        raise ValueError('invalid pitch track')
    out = {}
    for n in (1024, 2048, 4096):
        hop = n // 2
        f = np.lib.stride_tricks.sliding_window_view(x, n, axis=0)[::hop]
        dry = np.lib.stride_tricks.sliding_window_view(source, n, axis=0)[::hop]
        p = np.mean(dry*dry, axis=(1,2))
        active = p > max(p.max()*1e-4, 1e-12)
        if active.sum() < 8:
            continue
        hz = np.fft.rfftfreq(n, 1/sr)
        spec = np.sum(abs(np.fft.rfft(f*np.hanning(n), axis=-1))**2, axis=1)
        bands = np.stack([spec[:,(hz>=lo)&(hz<hi)].sum(1) for lo,hi in zip(EDGES,EDGES[1:])],1)
        total = bands.sum(1,keepdims=True)
        db = 10*np.log10(np.maximum(bands / np.maximum(total,1e-20), 1e-7))
        t = (np.arange(len(f))*hop+n/2)/sr
        right = np.clip(np.searchsorted(times,t),0,len(times)-1)
        left = np.maximum(0,right-1)
        near = np.where(abs(t-times[left])<=abs(t-times[right]),left,right)
        voiced = f0[near] > 0
        for group, mask in [('all',active),('voiced',active&voiced),('unvoiced',active&~voiced)]:
            if mask.sum() >= 8:
                out[n,group] = np.percentile(db[mask],[25,50,75],axis=0)
    if not out:
        raise ValueError('no active spectral frames')
    return out


def distance(a,b):
    keys = sorted(set(a)&set(b))
    if not keys:
        raise ValueError('no shared spectral groups')
    return float(np.mean([np.mean(abs(a[k]-b[k])) for k in keys]))


def peak_db(x):
    x = np.asarray(x)
    if x.ndim != 2 or not x.size or not np.isfinite(x).all():
        raise ValueError('invalid peak input')
    return float(20*np.log10(max(1e-12,np.max(abs(signal.resample_poly(x,4,1,axis=0))))))


def finish(x, ceiling=-1.5):
    """Offline scalar attenuation, not a limiter; report the exact applied gain."""
    if not np.isfinite(ceiling) or ceiling > 0:
        raise ValueError('invalid peak ceiling')
    gain = min(0., ceiling-peak_db(x)-.001)
    return np.asarray(x)*10**(gain/20), gain


def render(x,sr,gains,threshold):
    from pedalboard import Pedalboard, PeakFilter, Compressor
    x = _audio(x,sr)
    gains = np.asarray(gains, dtype=float)
    if gains.shape != (7,) or not np.isfinite(gains).all() or np.any(abs(gains)>10):
        raise ValueError('invalid EQ gains')
    if threshold is not None and (not np.isfinite(threshold) or not -40<=threshold<=0):
        raise ValueError('invalid compressor threshold')
    fx = [PeakFilter(cutoff_frequency_hz=float(hz), gain_db=float(g), q=.85)
          for hz,g in zip(CENTERS,gains)]
    if threshold is not None:
        fx.append(Compressor(threshold_db=threshold,ratio=2.,attack_ms=8.,release_ms=90.))
    return Pedalboard(fx)(np.ascontiguousarray(x.T,dtype=np.float32),sr).T


def fit(sources, reference, sr):
    """Train only. Caller must enforce source identity and split provenance."""
    if len(sources)<2:
        raise ValueError('need >=2 training performances')
    ref = shape(reference,sr,pitch_track(reference,sr))
    ref_profile = profile(reference,sr)
    tracks = [pitch_track(x,sr) for x in sources]
    profiles = [shape(x,sr,t) for x,t in zip(sources,tracks)]
    keys = [k for k in ref if k[1]=='all' and all(k in p for p in profiles)]
    if not keys:
        raise ValueError('no shared overall profiles')
    delta = np.median([ref[k][1]-p[k][1] for p in profiles for k in keys],axis=0)
    delta = np.clip(delta-np.median(delta),-9,9)
    matrix = np.exp(-.5*(np.log2(CENTERS[:,None]/CENTERS[None,:])/.7)**2)
    gains = lsq_linear(np.vstack([matrix,.35*np.eye(7)]),np.r_[delta,np.zeros(7)],bounds=(-8,8)).x
    def evaluate(g,th):
        ys = [render(x,sr,g,th) for x in sources]
        ds = [distance(shape(y,sr,t,x),ref) for x,y,t in zip(sources,ys,tracks)]
        dyn = [profile_distance(profile(y,sr),ref_profile)['dynamics_db'] for y in ys]
        return .75*np.mean(ds)+.25*max(ds)+.5*np.mean(dyn),dyn,ys
    options = [(np.zeros(7),None)]+[(gains*s,th) for s in (.4,.75,1.,1.25) for th in (None,-18.,-28.)]
    base,base_dyn,_ = evaluate(*options[0])
    best,g,th = base,*options[0]
    for q,t in options[1:]:
        score,dyn,_ = evaluate(q,t)
        if score < best and all(a<=b+.5 for a,b in zip(dyn,base_dyn)):
            best,g,th = score,q,t
    ys = [render(x,sr,g,th) for x in sources]
    level = np.clip(ref_profile['level']-np.median([profile(y,sr)['level'] for y in ys]),-12,12)
    # Fixed trim learned exclusively from training sources, then raw held-out peak checked separately.
    level = min(float(level),-1.501-max(peak_db(y) for y in ys))
    return g,th,{'train_score':float(best),'dry_train_score':float(base),'evaluations':len(options),'gain_db':float(level)}


def paired_mrstft(x,y):
    """Independent torch diagnostic, not the upstream auraloss package."""
    import torch
    a,b = (np.asarray(z) for z in (x,y))
    if a.shape != b.shape or a.ndim!=2 or len(a)<2048 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('paired geometry differs or invalid data')
    a,b = [torch.as_tensor(z.T,dtype=torch.float32) for z in (a,b)]
    scores=[]
    for n in (512,1024,2048):
        w=torch.hann_window(n)
        u,v=[torch.stft(z,n,hop_length=n//4,window=w,return_complex=True).abs() for z in (a,b)]
        sc=torch.linalg.vector_norm(u-v)/torch.linalg.vector_norm(v).clamp_min(1e-8)
        lm=(torch.log(u.clamp_min(1e-5))-torch.log(v.clamp_min(1e-5))).abs().mean()
        scores.append(float(sc+lm))
    return float(np.mean(scores))
