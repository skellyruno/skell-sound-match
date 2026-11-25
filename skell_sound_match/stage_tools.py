"""Offline research helpers: isolated limiter-inspired gate, causal sparse echo.
These are not a production Fruity Limiter or Delay 3 recreation.
"""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class GateSettings:
    threshold_db:float=-36.
    release_ms:float=90.
    floor_db:float=-90.
    def validate(self,rate):
        if type(rate) is not int or not 32000<=rate<=192000:raise ValueError('rate')
        if not all(np.isfinite((self.threshold_db,self.release_ms,self.floor_db))):raise ValueError('finite')
        if not -90<=self.threshold_db<=-6 or not 1<=self.release_ms<=1000 or not -120<=self.floor_db<=-6:raise ValueError('range')

def gate(x,rate,setting=GateSettings()):
    """Limiter gate-branch geometry: immediate unity above threshold, 1-pole decay below.
    Gate history is sample-count based; this batch function is prefix-causal.
    """
    setting.validate(rate)
    x=np.asarray(x,dtype=np.float32)
    if x.ndim!=2 or x.shape[1] not in (1,2) or not len(x) or not np.isfinite(x).all(): raise ValueError('audio')
    above=np.max(np.abs(x),axis=1)>=10**(setting.threshold_db/20)
    n=np.arange(len(x),dtype=np.int64)
    last=np.maximum.accumulate(np.where(above,n,-1))
    # FL gate time wheel is twice the 99%-settle time; coeff = 0.01 ** (1/(2*frames))
    quiet=n-last
    keep=np.exp(np.log(.01)/(2*(setting.release_ms/1000)*rate))
    floor=10**(setting.floor_db/20)
    gain=np.where(above,1.,floor+(1-floor)*np.exp(np.log(keep)*quiet))
    return (x*gain[:,None]).astype(np.float32)

@dataclass(frozen=True)
class EchoSettings:
    delay_ms:float=180.
    first:float=.12
    second:float=.04
    cross:float=1.
    def validate(self,rate):
        if type(rate) is not int or not 32000<=rate<=192000:raise ValueError('rate')
        if not np.isfinite([self.delay_ms,self.first,self.second,self.cross]).all():raise ValueError('finite')
        if not 30<=self.delay_ms<=1000 or abs(self.first)>1 or abs(self.second)>.7 or not 0<=self.cross<=1:raise ValueError('range')

def echo(x,rate,setting=EchoSettings()):
    """Causal 2-tap stereo wet send, no reference samples, no latency to direct path."""
    setting.validate(rate)
    x=np.asarray(x,dtype=np.float32)
    if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.isfinite(x).all():raise ValueError('audio')
    n=max(1,round(setting.delay_ms*rate/1000));y=x.copy()
    if n<len(y):
        a=x[:-n];sw=a[:,::-1];y[n:]+=setting.first*((1-setting.cross)*a+setting.cross*sw)
    if 2*n<len(y):
        a=x[:-2*n];sw=a[:,::-1];y[2*n:]+=setting.second*((1-setting.cross)*a+setting.cross*sw)
    return y
