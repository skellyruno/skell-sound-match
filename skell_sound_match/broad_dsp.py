"""Independent offline shared tone/dynamics/stereo correction. Not FL emulation.
No reference samples or coefficients are stored in the render basis.
"""
from dataclasses import dataclass
import numpy as np
from scipy import signal

@dataclass(frozen=True)
class Recipe:
    low: float=0.; mid: float=0.; high: float=0.
    compression: float=0.; side: float=0.; gain: float=0.
    drive: float=0.; echo: float=0.; delay_ms: float=125.
    motion: float=0.; motion_hz: float=.7
    def validate(self):
        for k,lo,hi in [('low',-9,9),('mid',-9,9),('high',-9,9),('compression',0,.8),('side',-12,12),('gain',-18,18),('drive',0,4),('echo',0,.7),('delay_ms',20,900),('motion',0,.7),('motion_hz',.15,8)]:
            v=getattr(self,k)
            if not np.isfinite(v) or not lo<=v<=hi: raise ValueError(k)

class Basis:
    def __init__(self,x,rate,*,threshold_db=-24.):
        x=np.asarray(x,dtype=np.float32)
        if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.isfinite(x).all() or type(rate)!=int or not 32000<=rate<=192000 or not np.isfinite(threshold_db) or not -90<=threshold_db<=0:raise ValueError('invalid audio/rate/threshold')
        self.x=x;self.rate=rate;self.threshold_db=threshold_db
        lows=[]
        for f in (250.,3500.):
            a=-np.expm1(-2*np.pi*f/rate);lows.append(signal.lfilter([a],[1,a-1],x,axis=0).astype(np.float32))
        self.bands=np.stack((lows[0],lows[1]-lows[0],x-lows[1]))
        # Linked detector per band, fast attack / slower recovery via two powers.
        powers=np.mean(self.bands.astype(np.float64)**2,axis=2)
        env=[]
        for ms in (4.,90.):
            a=-np.expm1(-1000/(ms*rate));env.append(signal.lfilter([a],[1,a-1],powers,axis=1))
        self.over=np.maximum(10*np.log10(np.maximum(np.maximum(*env),1e-15))-threshold_db,0).astype(np.float32)
    def render(self,r):
        r.validate()
        if r.low==r.mid==r.high==r.compression==0:y=self.x.copy()
        else:
            g=np.asarray([r.low,r.mid,r.high],np.float32)[:,None]-r.compression*self.over
            y=np.einsum('ij,ijk->jk',10**(g/20),self.bands)
        if r.drive:y=np.tanh(y*r.drive)/r.drive
        if r.side:
            d=(y[:,0]-y[:,1])*.5*(10**(r.side/20)-1);y[:,0]+=d;y[:,1]-=d
        if r.motion:
            a=r.motion*np.sin(np.arange(len(y),dtype=np.float64)*(2*np.pi*r.motion_hz/self.rate));y[:,0]*=1+a;y[:,1]*=1-a
        if r.echo:
            n=max(1,round(r.delay_ms*self.rate/1000));z=y.copy()
            for i,g in ((1,r.echo),(2,r.echo*.35),(3,r.echo*.12)):
                k=i*n
                if k<len(y):z[k:]+=g*y[:-k,::-1]
            y=z
        if r.gain:y*=10**(r.gain/20)
        if not np.isfinite(y).all():raise ValueError('nonfinite render')
        return np.asarray(y,np.float32)
