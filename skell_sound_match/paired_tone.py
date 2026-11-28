"""Offline same-length vocal tone fitting. Training-only calibration; no pitch or FX emulation."""
from dataclasses import dataclass
import numpy as np
from scipy import signal

@dataclass(frozen=True)
class ToneRecipe:
    bands_db: tuple[float, ...] = (0.,)*6
    compression: float = 0.
    expansion: float = 0.
    threshold_db: float = -18.
    gate_db: float = -45.
    gain_db: float = 0.
    side_db: float = 0.
    drive: float = 0.

    def check(self):
        if len(self.bands_db)!=6 or not all(np.isfinite(v) and -18<=v<=18 for v in self.bands_db):
            raise ValueError('invalid EQ gains')
        for v,lo,hi in ((self.compression,0,.9),(self.expansion,0,2), (self.threshold_db,-55,0),(self.gate_db,-85,-20),(self.gain_db,-36,36),(self.side_db,-18,18),(self.drive,0,6)):
            if not np.isfinite(v) or not lo<=v<=hi: raise ValueError('invalid tone control')

class ToneBasis:
    """Causal one-pole complementary bands and linked envelope; no reference in render."""
    def __init__(self,x,rate):
        x=np.asarray(x,dtype=np.float32)
        if x.ndim!=2 or x.shape[1]!=2 or len(x)<2048 or not np.isfinite(x).all() or type(rate) is not int or not 32000<=rate<=192000:
            raise ValueError('invalid stereo audio or rate')
        self.x=x
        lows=[]
        for hz in (150,400,1200,3500,7500):
            p=np.exp(-2*np.pi*hz/rate)
            lows.append(signal.lfilter([1-p],[1,-p],x,axis=0).astype(np.float32))
        self.bands=np.stack([lows[0],*[lows[i]-lows[i-1] for i in range(1,5)],x-lows[-1]])
        power=np.mean(x*x,axis=1,dtype=np.float64)
        env=[]
        for ms in (3.,85.):
            a=-np.expm1(-1000/(ms*rate));env.append(signal.lfilter([a],[1,a-1],power))
        self.level=10*np.log10(np.maximum(np.maximum(*env),1e-15))

    def render(self,r):
        r.check()
        if all(v==0 for v in r.bands_db): y=self.x.copy()
        else: y=np.einsum('i,ijk->jk',10**(np.asarray(r.bands_db,dtype=np.float32)/20),self.bands)
        if r.compression or r.expansion or r.gain_db:
            db=r.gain_db-r.compression*np.maximum(self.level-r.threshold_db,0)-r.expansion*np.minimum(np.maximum(r.gate_db-self.level,0),48)
            y*=10**(db[:,None]/20)
        if r.side_db:
            d=((y[:,0]-y[:,1])*.5)*(10**(r.side_db/20)-1)
            y[:,0]+=d;y[:,1]-=d
        if r.drive:
            # Smooth unit-small-signal-gain saturation; drive is not makeup gain.
            y=np.tanh(y*r.drive)/r.drive
        return np.asarray(y,np.float32)
