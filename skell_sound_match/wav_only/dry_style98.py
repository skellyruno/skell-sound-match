"""Standalone dry-input-only cross-performance recipe prototype.
No target samples or prior rendered WAVs are required by replay. Offline STFT.
"""
import numpy as np
from scipy import signal,ndimage
from . import cross_take_features98 as c

def fit_direct(p,q):
    def desc(a):
        e=10*np.log10(a[:,0].sum(1)+c.EPS);m=e>max(-65,np.percentile(e,90)-32);rel=10*np.log10((a[m,0]+c.EPS)/(a[m,0,1:5].sum(1,keepdims=True)+c.EPS));return e[m],np.median(rel,0)
    x,a=desc(p);y,b=desc(q);knots=np.quantile(x,[.04,.1,.25,.5,.75,.9,.98]);dest=np.quantile(y,[.04,.1,.25,.5,.75,.9,.98]);ride=np.clip((dest-np.median(y))-(knots-np.median(x)),-11,9);g=np.clip(b-a,-15,12);g-=np.mean(g[1:5]);g[0]=np.clip(g[0],-9,0);g[-1]*=.5
    return dict(knots=knots,ride=ride,eq=g)

def interp(g):
    f=np.log(np.maximum(c.F,1));v=np.log(c.CENTERS);return np.interp(f,v,g)

def direct(z,p,m,tone,dyn):
    e=10*np.log10(p[:,0].sum(1)+c.EPS);g=ndimage.gaussian_filter1d(np.interp(e,m['knots'],m['ride'])*dyn,3);z=z.copy();z[:,0]*=10**((g[:,None]+tone*interp(m['eq'])[None,:])/20);z[:,1]=0;return z

def space(x,preset):
    sr=c.SR;u=x.mean(1);idx=np.arange(len(u));delays,depth,rate,rt,pred=[([8.3,19.1,34.7],.35,.27,.55,13),([13.7,26.3,38.9],.8,.43,1.15,22),([5.9,21.1,42.7],1.4,.66,1.9,32)][int(preset)]
    v=[]
    for i in range(2):
        y=np.zeros(len(u),'f')
        for j,d in enumerate(delays):
            lag=(d+depth*np.sin(2*np.pi*rate*(1+.39*j)*idx/sr+j*1.9+i*2.7))*sr*.001;y+=np.interp(idx-lag,idx,u,left=0,right=0).astype('f')*(1 if j==0 else .65 if j==1 else .4)
        v.append(y/2.05)
    early=np.column_stack(v);tail=[]
    for ch in range(2):
        rng=np.random.default_rng(9800+ch+11*int(preset));n=int(rt*sr*1.3);t=np.arange(n)/sr;h=rng.normal(size=n)*10**(-3*t/rt);h=signal.sosfilt(signal.butter(2,[170,6500],btype='bandpass',fs=sr,output='sos'),h);h[:int(pred*.001*sr)]=0;h=h/max(np.linalg.norm(h),1e-12);tail.append(signal.oaconvolve(u,h.astype('f'))[:len(u)])
    return early,np.column_stack(tail).astype('f')

def space_gains(p,q,reg=0.25):
    a=c.descriptors(p);b=c.descriptors(q);g=np.clip(b['side']-a['side'],-14,12);g[0]*=.6;g[-1]*=.6;return g*(1-reg)

def apply_space(z,g,amount):
    v=z.copy();v[:,1]*=10**(interp(g)*amount/20)[None,:];return v

def mix(x,preset,early,tail):
    a,b=space(x,preset);return (x+a*early+b*tail).astype('f')

def peak(y):return float(20*np.log10(max(1e-12,np.max(abs(signal.resample_poly(y,4,1,axis=0))))))

def normalize(y,target):
    import pyloudnorm as pyln
    meter=pyln.Meter(c.SR);level=meter.integrated_loudness(y)
    if not np.isfinite(level) or not np.isfinite(target):raise ValueError('silent or invalid loudness')
    y=y*10**((target-level)/20);ceiling=10**(-1.35/20)
    for _ in range(3):
        e=np.max(abs(y),axis=1);g=np.minimum(1,ceiling/np.maximum(e,1e-8));g=ndimage.minimum_filter1d(g,size=265);g=ndimage.uniform_filter1d(g,size=131);g=np.minimum(g,ceiling/np.maximum(e,1e-8));gr=ndimage.minimum_filter1d(g,size=1103,origin=551);y=y*gr[:,None];delta=target-meter.integrated_loudness(y)
        if abs(delta)<.08:break
        y=y*10**(np.clip(delta,-1,1)/20)
    p=peak(y);return (y*min(1,10**((-1.25-p)/20))).astype('f')

def replay(x,m):
    x=np.asarray(x,dtype='f')
    if x.ndim!=2 or x.shape[1]!=2 or len(x)<c.SR or not np.isfinite(x).all():raise ValueError('expected finite stereo PCM at 44.1 kHz, at least one second')
    z=c.spec(x);p=c.power(z);y=normalize(c.synth(direct(z,p,m,float(m['tone']),float(m['dyn'])),len(x)),float(m['lufs']));v=mix(y,int(m['preset']),float(m['early']),float(m['tail']));return normalize(c.synth(apply_space(c.spec(v),m['g'],float(m['amount'])),len(x)),float(m['lufs']))
