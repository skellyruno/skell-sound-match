"""Experimental causal high-band conditioner for sustained vocal details.

Band energy and gating are driven only by the *input*, never the reference.
CPU/latency claims must be checked separately in the target native DSP host.
This Python implementation is offline research, not a real-time-safe VST3.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy import signal

@dataclass(frozen=True)
class AirSettings:
    amount: float = .32
    threshold_db: float = -16.0
    knee_db: float = 4.0
    attack_ms: float = 35.0
    activity_floor_db: float = -55.0

    def validate(self, rate: int):
        if type(rate) is not int or not 32000 <= rate <= 192000:
            raise ValueError('Sample rate outside validated range')
        for name in ('amount','threshold_db','knee_db','attack_ms','activity_floor_db'):
            if not math.isfinite(getattr(self,name)):
                raise ValueError('Non-finite '+name)
        if not (0 <= self.amount <= .55 and -40 <= self.threshold_db <= 5 and
                1 <= self.knee_db <= 15 and 5 <= self.attack_ms <= 120 and
                -90 <= self.activity_floor_db <= -30):
            raise ValueError('Parameter outside validated range')


class SustainedAir:
    def __init__(self, rate:int, channels:int, settings:AirSettings):
        settings.validate(rate)
        if type(channels) is not int or channels not in (1,2):
            raise ValueError('Only mono/stereo audio supported')
        self.rate=rate; self.channels=channels; self.settings=settings
        self.hi_sos=signal.butter(3,[7900,15000],btype='bandpass',fs=rate,output='sos')
        self.low_sos=signal.butter(2,[250,4200],btype='bandpass',fs=rate,output='sos')
        self.sib_sos=signal.butter(2,[5000,15000],btype='bandpass',fs=rate,output='sos')
        self.shi=np.zeros((len(self.hi_sos),2,channels))
        self.slo=np.zeros((len(self.low_sos),2,channels))
        self.ssi=np.zeros((len(self.sib_sos),2,channels))
        self.elo=np.zeros((1,1));self.esi=np.zeros((1,1))
        self.pole=math.exp(-1/(rate*settings.attack_ms*0.001))

    def process(self,samples: np.ndarray) -> np.ndarray:
        x=np.asarray(samples,dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != self.channels or not np.isfinite(x).all():
            raise ValueError('Invalid or non-finite input array')
        if len(x)==0:
            return x.copy()
        hi,self.shi=signal.sosfilt(self.hi_sos,x,axis=0,zi=self.shi)
        low,self.slo=signal.sosfilt(self.low_sos,x,axis=0,zi=self.slo)
        sib,self.ssi=signal.sosfilt(self.sib_sos,x,axis=0,zi=self.ssi)
        b=[1-self.pole];a=[1,-self.pole]
        lo_sq=np.mean(low**2,axis=1,keepdims=True)
        si_sq=np.mean(sib**2,axis=1,keepdims=True)
        e_lo,self.elo=signal.lfilter(b,a,lo_sq,axis=0,zi=self.elo)
        e_si,self.esi=signal.lfilter(b,a,si_sq,axis=0,zi=self.esi)
        rmslo=np.sqrt(np.maximum(e_lo[:,0],0));rmshi=np.sqrt(np.maximum(e_si[:,0],0))
        ratio=20*np.log10((rmshi+1e-7)/(rmslo+1e-7))
        logits=np.clip((ratio-self.settings.threshold_db)/self.settings.knee_db,-50,50)
        vowel_gate=1/(1+np.exp(logits))
        floor=10**(self.settings.activity_floor_db/20)
        active=(rmslo/(rmslo+floor))**2
        gain=self.settings.amount*vowel_gate*active
        return x + gain[:,None]*hi


def render(x: np.ndarray, rate:int, settings:AirSettings, chunk:int|None=None) -> np.ndarray:
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=2:
        raise ValueError('Expected (samples, channels) input')
    state=SustainedAir(rate,x.shape[1],settings)
    if chunk is None:
        return state.process(x)
    if type(chunk) is not int or chunk<1:
        raise ValueError('Invalid chunk length')
    return np.concatenate([state.process(x[i:i+chunk]) for i in range(0,len(x),chunk)])
