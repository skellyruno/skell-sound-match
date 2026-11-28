"""Offline causal M/S spectral and dynamic correction; not an original plugin clone.

Only fit reviewed same-take, same-stage audio. Keep recipes and recordings private.
These functions do not alter any preset or establish alignment by themselves.
"""
import numpy as np
from scipy import signal
from scipy.optimize import lsq_linear


def _audio(x, rate, *, max_frames=1920000):
    x = np.asarray(x, dtype=np.float32)
    if (not np.isfinite(rate) or int(rate) != rate or not 32000 <= rate <= 192000
            or x.ndim != 2 or x.shape[1] != 2 or not 1 <= len(x) <= max_frames
            or not np.isfinite(x).all() or np.max(np.abs(x)) > 4):
        raise ValueError('invalid bounded stereo audio or sample rate')
    return x


def active_partition(source, reference, rate):
    """Common zero-origin crop, partitions based on source activity, retain tails.

    Reject inadequate source or reference activity. Does not time-shift or prove
    recording identity. Full original files stay intact. Return crop end, a, b.
    """
    x,t = _audio(source, rate, max_frames=12000000), _audio(reference, rate, max_frames=12000000)
    if len(x)>60*rate or len(t)>60*rate:
        raise ValueError('activity scan exceeds 60 seconds')
    if x.shape != t.shape:
        raise ValueError('different recording geometry')
    hop = round(rate*.01)
    def last(z):
        f = z[:len(z)//hop*hop].reshape(-1,hop,2)
        if len(f)<100:
            raise ValueError('too short')
        e=np.sqrt(np.mean(f*f,axis=(1,2)))
        active=np.flatnonzero(e>max(float(e.max())*1e-3,1e-6))
        if len(active)<30:
            raise ValueError('insufficient activity')
        return int((active[-1]+1)*hop)
    end=last(x); length=min(len(x),max(end,last(t))+round(.25*rate))
    if length>1920000:
        raise ValueError('active span exceeds render budget')
    a,b=int(.45*end),int(.7*end)
    for z in (x,t):
        for w in (z[:a],z[a:b],z[b:length]):
            if len(w)<10*hop or np.mean(w*w,dtype=np.float64)<1e-10:
                raise ValueError('silent or short evaluation window')
    return length,a,b


def split_bands(audio,rate,edges=(250,1000,4000)):
    """Complementary, causal low-pass differences, in mid/side domain."""
    x=_audio(audio,rate);e=np.asarray(edges,dtype=float)
    if e.ndim!=1 or not 1<=len(e)<=5 or not np.isfinite(e).all() or e[0]<40 or e[-1]>=rate*.48 or np.any(np.diff(e)<=0):
        raise ValueError('invalid crossover frequencies')
    z=np.column_stack((x.mean(1),(x[:,0]-x[:,1])*.5)).astype('f')
    lp=[signal.sosfilt(signal.butter(2,h,fs=rate,output='sos'),z,axis=0).astype('f') for h in e]
    return np.stack([lp[0]]+[b-a for a,b in zip(lp,lp[1:])]+[z-lp[-1]],axis=1)


def _bank(B):
    B=np.asarray(B,dtype=np.float32)
    if B.ndim!=3 or B.shape[2]!=2 or not 2<=B.shape[1]<=6 or not 1<=len(B)<=1920000 or not np.isfinite(B).all():
        raise ValueError('invalid band bank')
    return B


def _decode(z):
    return np.column_stack((z[:,0]+z[:,1],z[:,0]-z[:,1])).astype('f')


def fit_energy(source_bands,target_bands,*,cap_db=8.):
    B,T=_bank(source_bands),_bank(target_bands)
    if B.shape!=T.shape or not np.isfinite(cap_db) or not 0<=cap_db<=15:
        raise ValueError('invalid paired bands or gain budget')
    z=B[::8].astype('d');t=T[::8].astype('d')
    p=np.sqrt(np.mean(z*z,axis=0));q=np.sqrt(np.mean(t*t,axis=0))
    if np.max(p)<1e-7 or np.max(q)<1e-7:
        raise ValueError('silent enrollment')
    return np.where(p>1e-7,np.clip(q/np.maximum(p,1e-7),10**(-cap_db/20),10**(cap_db/20)),1.)


def render_energy(bands,gains):
    B=_bank(bands);g=np.asarray(gains,dtype=np.float32)
    if g.shape!=B.shape[1:] or not np.isfinite(g).all() or np.any(g<10**(-15/20)-1e-6) or np.any(g>10**(15/20)+1e-6):
        raise ValueError('invalid band gains')
    return _decode(np.sum(B*g,axis=1))


def _detectors(B,hop):
    n=len(B);nb=(n+hop-1)//hop;pad=np.zeros((nb*hop,B.shape[1],2),dtype='f');pad[:n]=B
    v=np.mean(pad.reshape(nb,hop,B.shape[1],2)**2,axis=1);e=10*np.log10(np.maximum(v,1e-12))
    prev=np.vstack((np.full_like(e[:1],-120.),e[:-1]))
    slow=signal.lfilter([.12],[1,-.88],prev,axis=0,zi=np.full((1,B.shape[1],2),-120.*.88))[0]
    return e,prev,slow


def fit_dynamic(source_bands,target_bands,rate,*,cap_db=6.,regularization=15.,static=False):
    B,T=_bank(source_bands),_bank(target_bands)
    if B.shape!=T.shape or not np.isfinite(rate) or int(rate)!=rate or not 32000<=rate<=192000 or not np.isfinite(cap_db) or not 0<cap_db<=9 or not np.isfinite(regularization) or not 4<=regularization<=100 or type(static) is not bool:
        raise ValueError('invalid dynamic fit budget or geometry')
    hop=round(rate*.01);e,p,slow=_detectors(B,hop);tar,_,_=_detectors(T,hop)
    if np.max(e)<-80 or np.max(tar)<-80:
        raise ValueError('silent enrollment')
    out=[]
    for band in range(B.shape[1]):
        for c in range(2):
            u=e[:,band,c];v=tar[:,band,c];s=slow[:,band,c];q=p[:,band,c]
            act=(u>max(np.percentile(u,95)-38,-75))&(v>max(np.percentile(v,95)-38,-75))&(q>-85);act[:5]=False
            if act.sum()<15:
                out.append([0.,0.,0.,-40.]);continue
            center=float(np.median(s[act]));z=np.column_stack((np.ones(act.sum()),np.clip(s[act]-center,-24,24),np.clip(q[act]-s[act],-20,20)));y=np.clip(v[act]-u[act],-cap_db,cap_db)
            if static:coef=np.array([np.clip(np.median(y),-cap_db,cap_db),0.,0.])
            else:coef=lsq_linear(np.vstack([z,np.diag([4.,regularization,regularization])]),np.r_[y,0.,0.,0.],bounds=([-cap_db,-.30,-.25],[cap_db,.30,.25])).x
            out.append([*coef,center])
    return np.asarray(out).reshape(B.shape[1],2,4)


def render_dynamic(bands,coefficients,rate,*,cap_db=6.):
    """Gain derived exclusively from previous complete 10 ms blocks."""
    B=_bank(bands);C=np.asarray(coefficients,dtype=float)
    if not np.isfinite(rate) or int(rate)!=rate or not 32000<=rate<=192000 or not np.isfinite(cap_db) or not 0<cap_db<=9 or C.shape!=(*B.shape[1:],4) or not np.isfinite(C).all() or np.any(abs(C[:,:,0])>cap_db+1e-8) or np.any(abs(C[:,:,1])>.30000001) or np.any(abs(C[:,:,2])>.25000001):
        raise ValueError('invalid dynamic coefficients')
    hop=round(rate*.01);_,p,s=_detectors(B,hop)
    g=np.clip(C[:,:,0]+C[:,:,1]*np.clip(s-C[:,:,3],-24,24)+C[:,:,2]*np.clip(p-s,-20,20),-cap_db,cap_db);g[0]=0;g=signal.lfilter([.5],[1,-.5],g,axis=0)
    out=np.empty((len(B),2),dtype='f')
    for start in range(0,len(B),65536):
        idx=np.arange(start,min(start+65536,len(B)));i=idx//hop;f=(idx%hop)/hop;prev=g[np.maximum(i-1,0)];new=g[i]
        gg=10**((prev+(new-prev)*f[:,None,None])/20)
        out[idx]=_decode(np.sum(B[idx]*gg.astype('f'),axis=1))
    return out
