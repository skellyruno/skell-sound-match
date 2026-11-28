import numpy as np
import pytest
from scipy import signal
from skell_sound_match.wav_only.native_band_energy import fit_energy_eq

EDGES=np.array([35,90,185,380,820,1700,3600,7500,17500.])

def bell(x,f,g,q,sr):
    A=10**(g/40);w=2*np.pi*f/sr;c=np.cos(w);a=np.sin(w)/(2*q)
    return signal.lfilter([1+a*A,-2*c,1-a*A],[1+a/A,-2*c,1-a/A],x,axis=0)

@pytest.mark.parametrize('sr',[44100,48000])
def test_fitted_integrated_energy(sr):
    rng=np.random.default_rng(57)
    x=rng.normal(0,.04,(sr*2,2))
    t=bell(bell(x,500.,-7.,.6,sr),4500.,5.,.8,sr)*.8
    p=fit_energy_eq(x[:sr],t[:sr],sr)
    y=x[sr:].copy()
    for k in range(8):
        f=EDGES[k]*(EDGES[k+1]/EDGES[k])**p['params'][2*k]
        y=bell(y,f,(p['params'][2*k+1]-.5)*30,.4*20**p['q'][k],sr)
    y*=10**(p['gain']/20)
    edges=[70,150,300,600,1200,2400,4800,9600,18000]
    def err(a,b):
        f,p=signal.welch(a,sr,nperseg=2048,axis=0);_,q=signal.welch(b,sr,nperseg=2048,axis=0)
        return np.mean([abs(10*np.log10(p[(f>=l)&(f<h)].sum()/q[(f>=l)&(f<h)].sum())) for l,h in zip(edges[:-1],edges[1:])])
    assert err(y[1024:],t[sr+1024:]) < .35*err(x[sr+1024:],t[sr+1024:])
    assert all(0<=v<=1 for v in p['params']+p['q'])

def test_invalid_input():
    x=np.zeros((8192,2))
    with pytest.raises(ValueError):fit_energy_eq(x,x)
    with pytest.raises(ValueError):fit_energy_eq(x,x[:-1])
