#!/usr/bin/env python3
"""Skelly Deuce v1.7 candidate: consonant-aware high-band balance.

Constrained offline post-process on protected v1.4. Fits from first phrase
only. Unlike an unconditional treble boost, emphasizes quiet high harmonics
inside vowels while holding/reducing strong sibilants. No proprietary DSP.
"""
from pathlib import Path
import argparse, json, hashlib
import numpy as np
import soundfile as sf
from scipy import signal, ndimage
import pyloudnorm as pyln
import deuce_v14 as prior

BAND=[6500,11000]
LOW=[500,3500]
TRAIN=[0.94,6.84]

def aud_mono(path):
    z,sr=sf.read(path,always_2d=True)
    if sr<22050 or z.shape[1] not in (1,2) or not np.isfinite(z).all():raise ValueError('invalid audio')
    if z.shape[1]==2:
        mid=z.mean(axis=1)
        if np.sqrt(np.mean((z[:,0]-z[:,1])**2)) > .01 * np.sqrt(np.mean(mid*mid)):
            raise ValueError('Meaningful stereo differences require a stereo-aware process')
    return z.mean(axis=1),sr

def rms_frames(q,w):
    k=len(q)//w
    return 20*np.log10(np.maximum(np.sqrt((q[:k*w].reshape(-1,w)**2).mean(axis=1)),1e-10))

def band(x,sr,lo,hi):
    return signal.sosfilt(signal.butter(3,[lo,hi],fs=sr,btype='bandpass',output='sos'),x)

def normalize(x,sr,target=-20):
    if len(x)<sr*3 or not np.isfinite(x).all():raise ValueError('invalid signal')
    actual=pyln.Meter(sr).integrated_loudness(np.column_stack((x,x)))
    if not np.isfinite(actual):raise ValueError('cannot normalize silence')
    return x * 10**((target-actual)/20)

def features(x,sr):
    w=round(sr*.005); k=len(x)//w
    hi=band(x,sr,*BAND)
    lo=band(x,sr,*LOW)
    lev=rms_frames(x,w)
    hib=rms_frames(hi,w)
    lob=rms_frames(lo,w)
    idx=np.clip(hib-lob,-40,5)
    return {'hi':hi, 'idx':idx, 'level':lev, 'hilvl':hib, 'w':w, 'k':k}

def estimate(y,ref,sr):
    """Fit constrained linear gain vs highband-to-midband ratio from opening phrase."""
    if len(y)!=len(ref):raise ValueError('aligned same-take material required')
    f=features(y,sr); w=f['w'];k=f['k']
    times=(np.arange(k)+.5)*w/sr
    rhi=rms_frames(band(ref,sr,*BAND),w)
    rlv=rms_frames(ref,w)
    mask=(times>=TRAIN[0])&(times<TRAIN[1])&(f['level']>-42)&(rlv>-42)&(f['hilvl']>-58)&(rhi>-58)
    if mask.sum()<300:raise ValueError('insufficient training material')
    xx=np.clip(f['idx'][mask]+12,-25,20)
    dif=np.clip(rhi[mask]-f['hilvl'][mask],-4,4)
    # robust Huber regression, separate intercept/slope; constrain physically plausible behavior
    from scipy.optimize import least_squares
    def residual(v):
        pred=v[0]+v[1]*xx
        return np.r_[pred-dif,np.sqrt(25)*v[0],np.sqrt(150)*v[1]]
    z=least_squares(residual,[0.4,-0.08],loss='huber',f_scale=0.7,bounds=([-1.5,-.3],[2.0,.05]))
    g0,slope=z.x
    return {'version':'1.7-experiment','sample_rate':sr,'training_window_s':TRAIN,'band_hz':BAND,'low_band_hz':LOW,
        'intercept_db':round(float(g0),6),'slope_db_per_ratio_db':round(float(slope),6),
        'strength':.8, 'gain_min_db':-1.0,'gain_max_db':1.8,
        'smooth_frames':2.0,'min_active_db':-45.0,'control_rate_ms':1000*w/sr,
        'trained_frames':int(mask.sum()),'description':'Consonant-aware upper-band texture. Only opening phrase used to estimate ratio map; never exact Waves or FL plugin emulation.'}

def render_from_v14(y,sr,model):
    if sr!=model['sample_rate'] or model['band_hz']!=BAND or model['low_band_hz']!=LOW:raise ValueError('model mismatch')
    st=float(model['strength']);mn=float(model['gain_min_db']);mx=float(model['gain_max_db']);sig=float(model['smooth_frames'])
    if not(0<=st<=1 and -2<=mn<=0<=mx<=2 and .5<=sig<=10 and np.isfinite([st,mn,mx,sig]).all()):raise ValueError('invalid stage settings')
    f=features(y,sr);w=f['w'];k=f['k']
    g=(model['intercept_db']+model['slope_db_per_ratio_db']*(f['idx']+12))*st
    g=np.clip(g,mn,mx)
    # Silence mask prevents turning soft room noise into consonant-sounding noise
    activity=np.clip((f['level']-model['min_active_db'])/12,0,1)
    g=ndimage.gaussian_filter1d(g*activity,sig)
    up=np.interp(np.arange(len(y)),(np.arange(k)+.5)*w,g,left=0,right=0)
    out=y+f['hi']*(10**(up/20)-1)
    if not np.isfinite(out).all():raise ValueError('nonfinite output')
    return out

def fit(dry,ref,v14wav,out):
    dest=Path(out)
    if dest.exists():raise FileExistsError(dest)
    x,sr=aud_mono(dry); r,sr2=aud_mono(ref); y,sr3=aud_mono(v14wav)
    if sr!=sr2 or sr!=sr3 or len(x)!=len(r) or len(x)!=len(y):raise ValueError('file format mismatch')
    # Level match to working -20 reference and v1.4, but no timing re-alignment.
    yy=normalize(y,sr); rr=normalize(r,sr)
    m=estimate(yy,rr,sr)
    m['prior_audio_sha256']=hashlib.sha256(Path(v14wav).read_bytes()).hexdigest()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(m,indent=2)+'\n')
    return m

def apply(dry,prior_model,our_model,out):
    dest=Path(out)
    if dest.exists():raise FileExistsError(dest)
    x,sr=aud_mono(dry)
    pm=json.loads(Path(prior_model).read_text())
    m=json.loads(Path(our_model).read_text())
    if m.get('prior_model_sha256') and hashlib.sha256(Path(prior_model).read_bytes()).hexdigest()!=m['prior_model_sha256']:
        raise ValueError('Prior v1.4 model checksum mismatch')
    if pm['sample_rate']!=sr or m['sample_rate']!=sr:raise ValueError('sample rate mismatch')
    y=normalize(prior.render(x,sr,pm),sr)
    z=normalize(render_from_v14(y,sr,m),sr)
    true_peak=float(20*np.log10(np.max(abs(signal.resample_poly(z,4,1)))+1e-12))
    if true_peak>-1.0:raise ValueError('true peak above -1 dBTP')
    dest.parent.mkdir(parents=True,exist_ok=True)
    sf.write(dest,np.column_stack((z,z)),sr,subtype='PCM_24')
    saved,s=sf.read(dest,always_2d=True)
    loud=float(pyln.Meter(sr).integrated_loudness(saved))
    if s!=sr or abs(loud+20)>.05 or not np.isfinite(saved).all():
        dest.unlink(missing_ok=True);raise ValueError('output verification failed')
    return {'lufs':loud,'true_peak_dbtp':true_peak,'frames':len(x),'model':str(our_model)}

def main():
    a=argparse.ArgumentParser();sub=a.add_subparsers(dest='action',required=True)
    fitc=sub.add_parser('fit');fitc.add_argument('--dry',required=True);fitc.add_argument('--reference',required=True);fitc.add_argument('--v14wav',required=True);fitc.add_argument('--out',required=True)
    app=sub.add_parser('apply');app.add_argument('--dry',required=True);app.add_argument('--prior-model',required=True);app.add_argument('--model',required=True);app.add_argument('--out',required=True)
    args=a.parse_args()
    if args.action=='fit':print(json.dumps(fit(args.dry,args.reference,args.v14wav,args.out),indent=2))
    else:print(json.dumps(apply(args.dry,args.prior_model,args.model,args.out),indent=2))
if __name__=='__main__':main()
