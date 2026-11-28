"""Offline 44.1 kHz learned stereo chain. Fit on an explicit training pair;
render from an input seed only. FIR lead is declared offline lookahead.
Native/pitch seed generation is a separate caller responsibility.
"""
import numpy as np
from scipy import signal, fft

SR = 44100


def _audio(x):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 2 or not 1 <= len(x) <= 3000000 or not np.isfinite(x).all() or np.max(abs(x)) > 32:
        raise ValueError('bounded finite 44.1 kHz stereo input required')
    return x


def _rms(x):
    return float(np.sqrt(np.mean(x.astype('d') ** 2)))


def _filt(x, f, kind='lowpass'):
    return signal.sosfilt(signal.butter(2, f, fs=SR, btype=kind, output='sos').astype('f'), x, axis=0).astype('f')


def _env(x, ms):
    a = np.exp(-1000 / (ms * SR))
    return np.sqrt(np.maximum(signal.lfilter([1-a], [1,-a], x*x), 1e-12)).astype('f')


def features(x, scale, kind):
    x = _audio(x)
    if kind not in ('linear','dynamic') or not np.isfinite(scale) or not 1e-5 <= scale <= 32:
        raise ValueError('invalid feature contract')
    m=x.mean(1);s=(x[:,0]-x[:,1])*.5
    if kind=='linear':return np.column_stack((m,s))
    v=np.clip(np.log2(np.maximum(_env(np.max(abs(x),axis=1),15),scale*.035)/scale),-5,3).astype('f')
    slow=_env(np.max(abs(x),axis=1),100)
    v2=np.clip(np.log2(np.maximum(slow,scale*.035)/scale),-5,3).astype('f')
    gate=np.clip((20*np.log10(np.maximum(slow,1e-8)/scale)+32)/12,0,1).astype('f')
    lo=_filt(m,350);hi=_filt(m,4300,'highpass')
    enh=hi*np.clip(np.log2(np.maximum(_env(hi,8),scale*.008)/(scale*.15)),-4,3).astype('f')
    return np.column_stack((m,s,m*v,m*v2,m*(gate-1),np.tanh(m/(scale*1.5))*scale*1.5-m,lo*v,enh,s*v))


def fit_kernel(source, target, *, kind, nfft, lead, taps, regularization):
    """Only pass training samples, not the validation or held-out recording."""
    x=_audio(source);t=_audio(target)
    if t.shape!=x.shape or nfft not in (2048,4096,8192,16384) or type(lead) is not int or not 32<=lead<=128 or type(taps) is not int or not 128<=taps<=6144 or taps+lead>nfft or not .0001<=regularization<=1:
        raise ValueError('invalid fit geometry')
    scale=max(_rms(x),1e-5);B=features(x,scale,kind)
    starts=np.arange(0,len(x)-nfft+1,nfft//2)
    if len(starts)<4:raise ValueError('insufficient training duration')
    starts=starts[np.linspace(0,len(starts)-1,min(len(starts),220),dtype=int)]
    win=signal.windows.hann(nfft,sym=False).astype('f')
    sc=np.maximum(np.sqrt(np.mean(B**2,axis=0)),max(_rms(B)*.003,1e-6))
    X=np.stack([fft.rfft(B[j:j+nfft]*win[:,None]/sc,axis=0) for j in starts],axis=1)
    Y=np.stack([fft.rfft(t[j:j+nfft]*win[:,None],axis=0) for j in starts],axis=1)
    G=np.einsum('bfi,bfj->bij',X.conj(),X,optimize=True);R=np.einsum('bfi,bfo->bio',X.conj(),Y,optimize=True)
    diag=np.diagonal(G,axis1=1,axis2=2).real;floor=np.maximum(diag.mean(1)*.01,max(float(diag.mean())*1e-6,1e-10));idx=np.arange(B.shape[1]);G[:,idx,idx]+=regularization*np.maximum(diag,floor[:,None])+1e-8
    h=(fft.irfft(np.linalg.solve(G,R),n=nfft,axis=0)/sc[None,:,None]).astype('f')
    k=np.concatenate((h[-lead:],h[:taps]),axis=0);k[-64:]*=np.linspace(1,0,64,dtype='f')[:,None,None];k[:32]*=np.linspace(0,1,32,dtype='f')[:,None,None]
    if not np.isfinite(k).all():raise ValueError('nonfinite fit')
    return k,scale


def render(source, *, kind, scale, lead, kernel, spatial_features=(), spatial_weights=()):
    """Render a frozen learned chain without target audio or any fitting."""
    x=_audio(source)
    if kind=='identity':
        if lead!=0 or kernel is not None:raise ValueError('invalid identity contract')
        y=x.copy()
    else:
        B=features(x,scale,kind);k=np.asarray(kernel,dtype='f')
        if type(lead) is not int or not 0<=lead<=128 or k.ndim!=3 or k.shape[1:]!=(B.shape[1],2) or not lead<len(k)<=6272 or not np.isfinite(k).all() or np.max(abs(k))>32:
            raise ValueError('invalid frozen kernel')
        y=np.zeros_like(x)
        for i in range(B.shape[1]):
            for c in range(2):
                if np.any(k[:,i,c]):y[:,c]+=signal.oaconvolve(B[:,i],k[:,i,c])[lead:lead+len(x)]
    if spatial_features:
        w=np.asarray(spatial_weights,dtype='f')
        if len(spatial_features)>32 or w.shape!=(len(spatial_features),2) or not np.isfinite(w).all() or np.max(abs(w))>1:raise ValueError('invalid spatial weights')
        m=y.mean(1);out=[]
        for typ,v,c in spatial_features:
            if typ=='echo' and type(v) is int and 0<=v<=110250 and 20<=c<=18000:
                out.append(np.pad(_filt(m,c),(v,0))[:len(m)])
            elif typ=='room' and .1<=v<=3 and c in (0,1):
                n=int(SR*min(3,v*1.5));tt=np.arange(n)/SR;h=np.random.default_rng(550+c).standard_normal(n).astype('f')*np.exp(-6.908*tt/v)*(1-np.exp(-tt/.015));h=_filt(h.astype('f'),4500);h/=max(np.linalg.norm(h),1e-9);out.append(signal.oaconvolve(m,h)[:len(m)])
            else:raise ValueError('invalid spatial feature')
        y+=np.column_stack(out).astype('f')@w
    elif len(spatial_weights):raise ValueError('weights without features')
    if not np.isfinite(y).all():raise ValueError('nonfinite render')
    return y
