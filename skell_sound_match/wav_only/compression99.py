"""R99 offline cross-performance activity and compressor descriptors.
Frame-rate ballistics for research, not a native audio-thread compressor.
"""
import numpy as np
from scipy import ndimage

SR=44100
H=512
EPS=1e-10
DT=H/SR

def level(p):
    return 10*np.log10(p[:,0].sum(1)+EPS)

def active(p):
    e=level(p)
    return e>max(-65,np.percentile(e,95)-32)

def split(p):
    a=np.flatnonzero(active(p))
    if len(a)<100:
        raise ValueError('not enough vocal activity')
    k=int(a[int(len(a)*.52)])
    j=int(a[int(len(a)*.76)])
    return [slice(0,k-3),slice(k+3,j-3),slice(j+3,len(p))]

def smooth_env(v,attack,release):
    a=np.exp(-DT/(attack*.001))
    r=np.exp(-DT/(release*.001))
    out=np.empty_like(v)
    s=float(v[0])
    for i,u in enumerate(v):
        k=a if u>s else r
        s=k*s+(1-k)*u
        out[i]=s
    return out

def comp_gain(p,m):
    e=level(p)
    det=10*np.log10(smooth_env(10**(e/10),m['attack'],m['release'])+EPS)
    over=det-m['threshold']
    k=6.
    soft=np.where(over<-k/2,0,np.where(over>k/2,over,(over+k/2)**2/(2*k)))
    g=np.clip(-soft*(1-1/m['ratio']),-18,0)
    g=20*np.log10((1-m['parallel'])+m['parallel']*10**(g/20))
    ride=np.interp(e,m['knots'],m['ride'])*m['ride_amt']
    ride=ndimage.gaussian_filter1d(ride,6)
    return g+ride
