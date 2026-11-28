"""Offline, audio-only timbre transfer baseline. No saved presets or proprietary engines.

Profiles compare distributions, never samples across unrelated performances.
Recipes contain only bounded numeric controls; render consumes new input alone.
The fixed synthetic room and two-tap echo are exploratory, not identified FX.
"""
from dataclasses import dataclass, replace
from math import gcd
import numpy as np
from scipy import signal

BANDS = (60, 200, 500, 2000, 4500, 8000, 15000)
FRAME = 2048


def _audio(x, rate):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] not in (1, 2) or len(x) < FRAME:
        raise ValueError('expected nonempty mono/stereo audio of at least 2048 frames')
    if not np.isfinite(x).all() or not np.isfinite(rate) or not 32000 <= rate <= 192000 or int(rate)!=rate:
        raise ValueError('invalid audio or sample rate')
    return np.repeat(x, 2, axis=1) if x.shape[1] == 1 else x


def profile(x, rate):
    x = _audio(x, rate)
    if rate!=44100:
        g=gcd(int(rate),44100)
        x=signal.resample_poly(x,44100//g,int(rate)//g,axis=0)
        rate=44100
    f = x[:len(x)//FRAME*FRAME].reshape(-1, FRAME, 2)
    p = np.mean(f*f, axis=(1, 2), dtype=np.float64)
    active = np.flatnonzero(p > max(float(p.max())*1e-4, 1e-12))
    if len(active) < 8:
        raise ValueError('insufficient active audio')
    active = active[np.linspace(0, len(active)-1, min(128, len(active)), dtype=int)]
    f = f[active]; p = p[active]
    db = 10*np.log10(np.maximum(p, 1e-15)); med = float(np.median(db))
    spec = abs(np.fft.rfft(f*np.hanning(FRAME)[None, :, None], axis=1))**2
    hz = np.fft.rfftfreq(FRAME, 1/rate)
    b = np.stack([spec[:, (hz >= a) & (hz < z), :].sum(axis=(1, 2)) for a,z in zip(BANDS, BANDS[1:])],axis=1)
    shape = 10*np.log10(np.maximum(b/np.maximum(b.sum(axis=1,keepdims=True),1e-15),1e-7))
    mid = np.mean(((f[:,:,0]+f[:,:,1])*.5)**2,axis=1)
    side = np.mean(((f[:,:,0]-f[:,:,1])*.5)**2,axis=1)
    width = np.clip(10*np.log10(np.maximum(side,1e-15)/np.maximum(mid,1e-15)), -36, 12)
    return {'tone': np.percentile(shape,[25,50,75],axis=0),
            'dynamics': np.percentile(db-med,[10,25,75,90]),
            'width': np.percentile(width,[25,50,75]), 'level': med,
            'active_frames': len(active)}


def distance(a,b):
    tone=float(np.mean(abs(a['tone']-b['tone'])))
    dyn=float(np.mean(abs(a['dynamics']-b['dynamics'])))
    width=float(np.mean(abs(a['width']-b['width'])))
    return dict(score=tone+.5*dyn+.2*width, tone_db=tone, dynamics_db=dyn,
                width_db=width, level_gap_db=abs(a['level']-b['level']))


@dataclass(frozen=True)
class Recipe:
    low: float=0.; body: float=0.; presence: float=0.; air: float=0.
    compression: float=0.; gate: float=0.; stereo: float=0.
    echo: float=0.; echo_ms: float=250.; room: float=0.; gain_db: float=0.
    schema: str='skelly.reference-transfer.v1'

    def checked(self):
        if self.schema!='skelly.reference-transfer.v1':
            raise ValueError('unknown recipe version')
        bounds={'low':(-12,12),'body':(-12,12),'presence':(-12,12),'air':(-12,12),
                'compression':(0,.75),'gate':(0,1),'stereo':(0,.7),'echo':(0,.6),
                'echo_ms':(80,1000),'room':(0,.6),'gain_db':(-36,36)}
        for name,(lo,hi) in bounds.items():
            v=getattr(self,name)
            if not np.isfinite(v) or not lo<=v<=hi:
                raise ValueError('invalid recipe control: '+name)
        return self


def _shift(x,n):
    y=np.zeros_like(x)
    if 0<n<len(x): y[n:]=x[:-n]
    return y


class Prepared:
    """Input-dependent basis only. No reference audio is stored or used here."""
    def __init__(self,x,rate):
        self.x=_audio(x,rate); self.rate=rate
        self.level=profile(self.x,rate)['level']
        lows=[signal.sosfilt(signal.butter(2,hz,fs=rate,output='sos'), self.x,axis=0).astype(np.float32) for hz in (250,1800,6500)]
        self.bands=np.stack([lows[0],lows[1]-lows[0],lows[2]-lows[1],self.x-lows[2]])
        pole=np.exp(-1/(.025*rate)); power=np.mean(self.x**2,axis=1)
        self.env=10*np.log10(np.maximum(signal.lfilter([1-pole],[1,-pole],power),1e-15)) - self.level
        # Original deterministic synthetic diffuse tail; not recovered target IR.
        rng=np.random.default_rng(731); t=np.arange(int(rate*.65))/rate
        ir=rng.standard_normal((len(t),2))*np.exp(-t*13)[:,None]
        ir[:int(rate*.012)]=0; ir/=max(1e-12,np.sqrt(np.sum(ir**2)/2))
        self.ir=ir.astype(np.float32)

    def render(self,r):
        r.checked()
        if (r.low,r.body,r.presence,r.air)==(0.,0.,0.,0.): y=self.x.copy()
        else:
            gains=10**(np.asarray([r.low,r.body,r.presence,r.air],np.float32)/20)
            y=np.sum(self.bands*gains[:,None,None],axis=0)
        if r.compression or r.gate:
            d=-r.compression*np.maximum(self.env+6,0)-r.gate*np.clip(-self.env-15,0,36)
            y*=10**(d[:,None]/20)
        if r.stereo:
            mid=y.mean(axis=1); s=.5*(_shift(mid,int(.011*self.rate))-_shift(mid,int(.019*self.rate)))
            y[:,0]+=r.stereo*s; y[:,1]-=r.stereo*s
        if r.echo:
            n=int(round(r.echo_ms*self.rate/1000)); y=y+r.echo*(_shift(y[:,::-1],n)+.35*_shift(y,2*n))
        if r.room:
            y=y+r.room*signal.fftconvolve(y,self.ir,axes=0)[:len(y)]
        return np.asarray(y*10**(r.gain_db/20),dtype=np.float32)


def render(x,rate,recipe):
    return Prepared(x,rate).render(recipe)


def fit(source,rate,reference,ref_rate,additional_sources=()):
    """Fit only the provided training audio; no paired waveform assumption.

    Caller must hold back independent source and reference sections before fit.
    Additional sources use a mean/worst objective to discourage take-specific fits.
    Bounded coordinate search includes unity and does not use held-out scores.
    """
    bases=[Prepared(source,rate)]+[Prepared(x,sr) for x,sr in additional_sources]
    target=profile(reference,ref_rate); r=Recipe()
    def measures(q):
        rows=[distance(profile(b.render(q),b.rate),target) for b in bases]
        mean={k:float(np.mean([v[k] for v in rows])) for k in rows[0]}
        mean['worst_score']=max(v['score'] for v in rows)
        return mean
    def objective(m): return .75*m['score']+.25*m['worst_score']
    base=measures(r); best=objective(base); count=1
    grids={'low':[-12,-6,0,6,12],'body':[-12,-6,0,6,12],
           'presence':[-12,-6,0,6,12],'air':[-12,-6,0,6,12],
           'compression':[0,.25,.5,.75],'gate':[0,.5,1],'stereo':[0,.15,.35,.7],
           'echo':[0,.15,.35,.6],'echo_ms':[125,250,375,500,750,1000], 'room':[0,.15,.35,.6]}
    def assess(q):
        nonlocal count
        count+=1
        try: return objective(measures(q))
        except ValueError: return float('inf')
    for _ in range(2):
        for key, vals in grids.items():
            if key=='echo_ms' and r.echo==0: continue
            for v in vals:
                q=replace(r,**{key:float(v)}); s=assess(q)
                if s<best-1e-7: r,best=q,s
    # Gain calibration is fit only from training audio. No peak hiding/limiting.
    level=float(np.median([profile(b.render(r),b.rate)['level'] for b in bases]))
    r=replace(r,gain_db=float(np.clip(target['level']-level,-36,36)))
    return r, {'baseline':base,'fit':measures(r),'evaluations':count,'training_sources':len(bases)}
