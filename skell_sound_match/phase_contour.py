"""Skelly Sound Match — phase/contour offline research (not real-time-safe).

Fits time-invariant regularized FIR + 5-ms level contour from a training
section of the same performance. Never executes or clones proprietary DSP.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal, ndimage
from scipy.signal import fftconvolve

FS = 44100

class MatchError(ValueError): pass

def require_same_take_pair(base, target, sr_base, sr_target):
    if sr_base != sr_target or sr_base < 22050 or len(base) != len(target):
        raise MatchError('input files must have identical sample rate and duration')
    if len(base) < 4*sr_base or not np.isfinite(base).all() or not np.isfinite(target).all():
        raise MatchError('invalid or nonfinite input')
    if np.sqrt(np.mean(base**2)) < 1e-6 or np.sqrt(np.mean(target**2)) < 1e-6:
        raise MatchError('silent input')
    # Loose, training-window envelope check catches unrelated takes while
    # allowing strongly compressed/colored matching audio.
    sr=sr_base
    q=min(len(base), int(6.5*sr))
    w=max(1,round(.05*sr))
    k=q//w
    b=np.sqrt((base[:k*w].reshape(k,w)**2).mean(1))
    t=np.sqrt((target[:k*w].reshape(k,w)**2).mean(1))
    r=float(np.corrcoef(np.log1p(b*1000),np.log1p(t*1000))[0,1])
    if not np.isfinite(r) or r < 0.25:
        raise MatchError('same-take evidence too weak')
    return None

def active_mono(path):
    a,sr=sf.read(path,always_2d=True)
    if a.shape[1] not in (1,2) or not np.isfinite(a).all():raise MatchError('unsupported audio')
    if a.shape[1]==2:
        mid=a.mean(1)
        if np.sqrt(np.mean((a[:,0]-a[:,1])**2)) > .01 * np.sqrt(np.mean(mid**2)+1e-15):
            raise MatchError('meaningful stereo differences: do not downmix')
        return mid,sr
    return a[:,0],sr

def loudness_normalize(q,sr,target=-20):
    import pyloudnorm as pyln
    meter=pyln.Meter(sr)
    val=meter.integrated_loudness(np.column_stack((q,q)))
    if not np.isfinite(val):raise MatchError('cannot normalize silence')
    return q * 10**((target-val)/20)

def frame_db(q,w):
    k=len(q)//w
    return 20*np.log10(np.maximum(np.sqrt((q[:k*w].reshape(k,w)**2).mean(1)),1e-8))

def feat(y,dry,sr,w):
    k=len(y)//w
    lev=frame_db(y,w)
    drylev=frame_db(dry,w)
    f=[lev,np.clip(lev-drylev,-20,20)]
    for s in (2,8,25,50):
        p=ndimage.gaussian_filter1d(10**(lev/10),s)
        sl=10*np.log10(np.maximum(p,1e-16))
        f += [sl,np.clip(lev-sl,-20,20),np.clip((sl-np.roll(sl,4))/4,-10,10)]
    for lo,hi in ((100,400),(400,1300),(1300,4000),(4000,9000),(9000,17000)):
        b=signal.sosfilt(signal.butter(3,[lo,hi],fs=sr,btype='bandpass',output='sos'),y)
        f.append(np.clip(frame_db(b,w)-lev,-40,10))
    return np.column_stack(f),lev

def fit_fir(base,ref,sr,train=(.94,6.84),nfft=8192,taps=4095,reg=.001):
    if nfft<1024 or taps>nfft or taps<33 or taps%2!=1 or not (.000001 <= reg <= 1):
        raise MatchError('unsafe FIR settings')
    sl=slice(int(train[0]*sr),int(train[1]*sr))
    # normalize both files using training window only
    gain=np.sqrt(np.mean(base[sl]**2))/np.sqrt(np.mean(ref[sl]**2))
    r=ref*gain
    f,cross=signal.csd(base[sl],r[sl],fs=sr,nperseg=nfft,noverlap=nfft*3//4)
    _,auto=signal.welch(base[sl],fs=sr,nperseg=nfft,noverlap=nfft*3//4)
    hfull=np.fft.irfft(cross/(auto+np.percentile(auto[auto>0],80)*reg),nfft)
    pre=taps//2
    h=np.r_[hfull[-pre:],hfull[:taps-pre]]*np.hanning(taps)
    if not np.isfinite(h).all():raise MatchError('filter fitting failed')
    return h

def fit_contour(filtered,dry,reference,sr,train=(.94,6.84),strength=.6):
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import HuberRegressor
    w=round(sr*.005)
    z,lev=feat(filtered,dry,sr,w)
    rlev=frame_db(reference,w)
    k=len(lev);times=(np.arange(k)+.5)*w/sr
    selected=(times>=train[0])&(times<train[1])&(lev>-44)&(rlev>-44)
    if selected.sum()<200:raise MatchError('insufficient active training data')
    scale=StandardScaler().fit(z[selected]);t=np.clip(rlev[selected]-lev[selected],-4,4)
    model=HuberRegressor(alpha=10,epsilon=1.4,max_iter=300).fit(scale.transform(z[selected]),t)
    return {'coef':model.coef_.tolist(),'intercept':float(model.intercept_),
            'feature_means':scale.mean_.tolist(),'feature_scales':scale.scale_.tolist(),
            'strength':strength,'max_correction_db':1.5,'smoothing_frames':1.0,'frame_samples':w,
            'trained_frames':int(selected.sum())}

def apply_contour(filtered,dry,sr,m):
    w=m['frame_samples']; features,lev=feat(filtered,dry,sr,w);k=len(lev)
    co=np.asarray(m['coef']);avg=np.asarray(m['feature_means']);scale=np.asarray(m['feature_scales']);
    if co.size!=features.shape[1] or not np.isfinite(co).all() or not (0<=m['strength']<=1):
        raise MatchError('invalid contour model')
    gain=np.clip(ndimage.gaussian_filter1d(
        ((features-avg)/scale@co+m['intercept'])*m['strength'],m['smoothing_frames']),
        -m['max_correction_db'],m['max_correction_db']) * np.clip((lev+47)/15,0,1)
    interpolated=np.interp(np.arange(len(filtered)),(np.arange(k)+.5)*w,gain,left=0,right=0)
    return filtered*10**(interpolated/20)

def render(base,dry,sr,model):
    if sr!=model['sample_rate'] or len(base)!=len(dry) or not np.isfinite(base).all():raise MatchError('invalid input')
    h=np.asarray(model['fir'])
    if len(h)!=model['tap_count'] or len(h)%2!=1 or not np.isfinite(h).all():raise MatchError('invalid FIR')
    out=fftconvolve(base,h,mode='same')
    if model.get('contour'):
        out=apply_contour(out,dry,sr,model['contour'])
    out=loudness_normalize(out,sr,-20)
    if not np.isfinite(out).all():raise MatchError('nonfinite output')
    tp=float(20*np.log10(np.max(abs(signal.resample_poly(out,4,1)))+1e-15))
    if tp>-1.0:raise MatchError(f'unsafe true peak: {tp:.3f} dBTP')
    return out,{'lufs':-20.0,'true_peak_dbtp_estimate':tp,'frames':len(out)}

def fit_and_render(base,dry,ref,sr,train=(.94,6.84)):
    require_same_take_pair(base,ref,sr,sr)
    if len(dry)!=len(base):raise MatchError('dry reference length mismatch')
    h=fit_fir(base,ref,sr,train=train)
    phased=fftconvolve(base,h,mode='same')
    phased=loudness_normalize(phased,sr,-20)
    # Only the opening training window may determine target calibration.
    tr=slice(int(train[0]*sr), int(train[1]*sr))
    scale=np.sqrt(np.mean(phased[tr]**2))/np.sqrt(np.mean(ref[tr]**2))
    refnorm=ref*scale
    contour=fit_contour(phased,dry,refnorm,sr,train=train)
    model={'version':'v1.9-offline-research','sample_rate':sr,'tap_count':len(h),'fir':h.tolist(),
           'training_window_s':list(train),'fit_process':'Regularized cross-spectrum, training-only',
           'contour':contour,'latency_note':'Noncausal FIR uses ~46 ms lookahead; offline only; NOT VST3 real-time-ready'}
    out,metrics=render(base,dry,sr,model)
    return model,out,metrics

def write_verified(out_path,model_path,output,sr,model):
    p=Path(out_path);q=Path(model_path)
    if p.exists() or q.exists():raise FileExistsError('would overwrite a protected version')
    p.parent.mkdir(parents=True,exist_ok=True);q.parent.mkdir(parents=True,exist_ok=True)
    sf.write(p,np.column_stack((output,output)),sr,subtype='PCM_24')
    q.write_text(json.dumps(model,indent=2))
    return p,q

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description='Fit offline phase+contour model from the opening passage of a matched vocal.')
    p.add_argument('--base',required=True,help='Protected candidate recording (read-only)')
    p.add_argument('--dry',required=True,help='Unprocessed source (read-only)')
    p.add_argument('--reference',required=True,help='Original chain output (read-only)')
    p.add_argument('--wav',required=True,help='New WAV output, must not exist')
    p.add_argument('--model',required=True,help='New JSON model output, must not exist')
    args=p.parse_args()
    base,sr=active_mono(args.base);dry,srd=active_mono(args.dry);ref,srr=active_mono(args.reference)
    if sr!=srd or sr!=srr:raise MatchError('sample rate mismatch')
    model,wave,meters=fit_and_render(base,dry,ref,sr)
    write_verified(args.wav,args.model,wave,sr,model)
    print(json.dumps(meters,indent=2))