#!/usr/bin/env python3
"""Skelly SoundMatch v1.2: reference-trained dynamic six-band tone + level contour.

This is offline research DSP. Fit requires the *same* dry and target vocal take,
plus a v1.1 model. Apply needs only dry input and the saved JSON model.
Reference audio is NEVER accessed during apply. No proprietary plug-in parameters
are recovered. Noncausal model; not a real-time VST3.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import signal, ndimage
import soundfile as sf
import pyloudnorm as pyln
import vocalmatch_v11 as prior
import deuce_contour_v09 as contour
import skelly_soundmatch_v08 as base

BANDS=((70,250),(250,650),(650,1600),(1600,3500),(3500,7000),(7000,14000))
NFFT=2048
HOP=256


def _load_mono(path):
    x,sr=base.load(path)
    if not np.isfinite(x).all():raise ValueError('Non-finite input audio')
    return x,sr


def _base_render(dry,sr,model):
    y=prior.render(dry,sr,model)
    stereo,_=prior.loudness_safe_stereo(y,sr,-20,-1.0)
    return stereo[:,0]


def _level_to_target(y,sr,target_lufs=-20):
    stereo=np.column_stack((y,y))
    current=pyln.Meter(sr).integrated_loudness(stereo)
    if not np.isfinite(current):raise ValueError('Cannot measure reference loudness')
    return y*10**((target_lufs-current)/20)


def _stft(x,sr):
    return signal.stft(x,fs=sr,nperseg=NFFT,noverlap=NFFT-HOP,boundary='zeros')


def _band_features(Z,f):
    a=np.abs(Z)
    levels=[]
    for lo,hi in BANDS:
        sel=(f>=lo)&(f<hi)
        if not np.any(sel):raise ValueError('Sample rate too low for the requested band model')
        levels.append(20*np.log10(np.sqrt(np.mean(a[sel]**2,axis=0))+1e-10))
    levels=np.stack(levels,axis=1)
    full=20*np.log10(np.sqrt(np.mean(a**2,axis=0))+1e-10)
    F=np.column_stack([np.ones(len(full)),full,ndimage.gaussian_filter1d(full,3),
                       np.gradient(ndimage.gaussian_filter1d(full,2)),levels-full[:,None]])
    F[:,1:]=np.clip(F[:,1:],-100,100)
    return F,levels,full


def _interpolate_bands(f,g):
    mids=np.array([np.sqrt(lo*hi) for lo,hi in BANDS])
    fi=np.maximum(f,1e-7)
    i=np.searchsorted(mids,fi)
    high=np.clip(i,0,len(mids)-1)
    low=np.clip(i-1,0,len(mids)-1)
    den=np.maximum(np.log(mids[high])-np.log(mids[low]),1e-9)
    fac=np.where(low==high,0,np.clip((np.log(fi)-np.log(mids[low]))/den,0,1))
    return (g[:,low]*(1-fac)+g[:,high]*fac).T


def fit_multiband(y,r,sr,train,alpha=1000,maximum=3,sm_frames=2,strength=.85):
    from sklearn.linear_model import Ridge
    f,t,Z=_stft(y,sr);_,_,R=_stft(r,sr)
    F,Zb,full=_band_features(Z,f)
    _,Rb,_=_band_features(R,f)
    mask=(t>=train[0])&(t<train[1])&(full>-68)
    if mask.sum()<150:raise ValueError('Insufficient voiced frames for fitting dynamic tone')
    reg=Ridge(alpha=alpha)
    reg.fit(F[mask],np.clip(Rb-Zb,-8,8)[mask])
    return {'coefficients':reg.coef_.tolist(),'intercepts':reg.intercept_.tolist(),
            'max_gain_db':maximum,'smoothing_stft_frames':sm_frames,'strength':strength,
            'training_frames':int(mask.sum()),'ridge_alpha':alpha,
            'bands_hz':[list(b) for b in BANDS], 'fft_samples':NFFT,'hop_samples':HOP}


def apply_multiband(y,sr,p):
    if len(y)<NFFT:raise ValueError('Audio too short')
    f,_,Z=_stft(y,sr)
    F,_,_=_band_features(Z,f)
    coef=np.array(p['coefficients'],dtype=float)
    intercept=np.array(p['intercepts'],dtype=float)
    if coef.shape!=(len(BANDS),F.shape[1]) or intercept.shape!=(len(BANDS),):
        raise ValueError('Invalid dynamic band matrix')
    gains=F@coef.T+intercept
    gains=ndimage.gaussian_filter1d(np.clip(gains,-p['max_gain_db'],p['max_gain_db']),p['smoothing_stft_frames'],axis=0)
    gain_f=_interpolate_bands(f,gains)*p['strength']
    _,out=signal.istft(Z*10**(gain_f/20),fs=sr,nperseg=NFFT,noverlap=NFFT-HOP,boundary=True)
    return out[:len(y)]


def fit_contour(dry,y,reference,sr,training):
    from sklearn.ensemble import HistGradientBoostingRegressor
    X,hop,level,k=contour._frame_features(dry,y,sr)
    target=20*np.log10(np.sqrt(np.mean(reference[:k*hop].reshape(k,hop)**2,axis=1))+1e-12)
    difference=np.clip(target-level,-10,10)
    T=(np.arange(k)+.5)*hop/sr
    eligible=(T>=training[0])&(T<training[1])&(level>-44)&(target>-45)
    if eligible.sum()<140:raise ValueError('Insufficient active training frames for envelope')
    m=HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=6,min_samples_leaf=25,
            learning_rate=.04,l2_regularization=15,random_state=1)
    m.fit(X[eligible],difference[eligible])
    exported=contour._tree_export(m)
    err=np.max(np.abs(m.predict(X)-contour._tree_predict(X,exported)))
    if err>1e-6:raise RuntimeError('Serialized contour does not match trained model')
    return {'trees':exported,'smoothing_frames':3,'max_gain_db':3,
            'training_frames':int(eligible.sum())}


def apply_contour(dry,y,sr,p):
    X,hop,_,k=contour._frame_features(dry,y,sr)
    gains=contour._tree_predict(X,p['trees'])
    gains=np.clip(ndimage.gaussian_filter1d(gains,p['smoothing_frames']),-p['max_gain_db'],p['max_gain_db'])
    gains=np.interp(np.arange(len(y)),(np.arange(k)+.5)*hop,gains,left=gains[0],right=gains[-1])
    return y*10**(gains/20)


def apply_post_saturation(y,sr,p):
    """Optional 4x oversampled soft saturation; coefficients are saved in the model.

    This is a calibrated audition hypothesis, not an identified original plugin.
    Apply needs no reference audio and has deterministic output.
    """
    threshold=float(p.get('threshold',0.4))
    wet=float(p.get('mix',1.0))
    factor=int(p.get('oversampling',4))
    if not (0.2 <= threshold <= 2.0 and 0 <= wet <= 1 and factor in (1,2,4)):
        raise ValueError('Invalid saturation parameters')
    if not np.isfinite(y).all():
        raise ValueError('Cannot saturate non-finite audio')
    up=signal.resample_poly(y,factor,1) if factor>1 else y
    shaped=threshold*np.tanh(up/threshold)
    down=signal.resample_poly(shaped,1,factor)[:len(y)] if factor>1 else shaped
    out=(1-wet)*y+wet*down
    if not np.isfinite(out).all():
        raise ValueError('Non-finite post saturation output')
    return out


def render(dry,sr,m):
    if sr!=m['sample_rate']:raise ValueError('Sample rate mismatch')
    if len(dry)>sr*90:raise ValueError('Longer than 90 seconds not supported')
    y=_base_render(dry,sr,m['prior_v11_model'])
    y=apply_multiband(y,sr,m['multiband'])
    y=apply_contour(dry,y,sr,m['contour'])
    if m.get('post_saturation') is not None:
        y=apply_post_saturation(y,sr,m['post_saturation'])
    if not np.isfinite(y).all():raise ValueError('Invalid audio output')
    return y


def fit(dry_path,reference_path,prior_path,out_path):
    if Path(out_path).exists():raise FileExistsError(out_path)
    dry,sr=_load_mono(dry_path);r,rr=_load_mono(reference_path)
    if sr!=rr or len(dry)!=len(r):raise ValueError('Dry/processed sample counts or rates differ')
    check=base.pair_check(dry,r,sr)
    v11=json.loads(Path(prior_path).read_text())
    if sr!=v11['sample_rate']:raise ValueError('Prior model sample rate mismatch')
    z=_base_render(dry,sr,v11)
    train=base.windows(len(dry),sr)['training']
    # IMPORTANT: fit the reference's gain ONLY from the training passage.
    # Full-recording loudness normalization would leak held-out amplitude into fitting.
    cut=slice(round(train[0]*sr),round(train[1]*sr))
    tr_r=np.sqrt(np.mean(r[cut]**2))
    tr_z=np.sqrt(np.mean(z[cut]**2))
    if tr_r<1e-8 or tr_z<1e-8:raise ValueError('Training window has insufficient energy')
    train_gain_db=float(20*np.log10(tr_z/tr_r))
    r=r*10**(train_gain_db/20)
    fit_tone=fit_multiband(z,r,sr,train)
    toned=apply_multiband(z,sr,fit_tone)
    fit_level=fit_contour(dry,toned,r,sr,train)
    m={'version':'1.2','offline_only':True,'sample_rate':sr,'prior_v11_model':v11,
       'multiband':fit_tone,'contour':fit_level,'training_window_s':train,
       'reference_training_gain_db':train_gain_db,
       'reference_shasum':hashlib.sha256(Path(reference_path).read_bytes()).hexdigest(),
       'dry_shasum':hashlib.sha256(Path(dry_path).read_bytes()).hexdigest(),
       'caveat':'Model deliberately learned from one vocal take. Evaluation sections were inspected during development; not independent blind validation.',
       'pair_check':check}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(m,indent=2)+'\n')
    return m


def apply(dry_path,model_path,out_path,target_lufs=-20):
    if Path(out_path).exists():raise FileExistsError(out_path)
    dry,sr=_load_mono(dry_path)
    m=json.loads(Path(model_path).read_text())
    y=render(dry,sr,m)
    stereo,quality=prior.loudness_safe_stereo(y,sr,target_lufs,-1)
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    sf.write(out_path,stereo,sr,subtype='PCM_24')
    wr,ws=sf.read(out_path,always_2d=True)
    if len(wr)!=len(dry) or sr!=ws or not np.isfinite(wr).all():raise RuntimeError('Export invalid')
    loudness=float(pyln.Meter(sr).integrated_loudness(wr))
    tp=base.db(base.truepeak(wr[:,0]))
    if tp>-0.98:raise RuntimeError('Peak guard failed')
    return {'output':str(out_path),'sample_rate':sr,'samples':len(wr),
            'lufs':round(loudness,3),'truepeak_dbtp':round(tp,3),'safety':quality}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    f=sub.add_parser('fit')
    for s in ['dry','reference','prior','out']:f.add_argument('--'+s,required=True)
    a=sub.add_parser('apply')
    for s in ['dry','model','out']:a.add_argument('--'+s,required=True)
    a.add_argument('--lufs',type=float,default=-20)
    args=p.parse_args()
    result=fit(args.dry,args.reference,args.prior,args.out) if args.action=='fit' else apply(args.dry,args.model,args.out,args.lufs)
    if args.action=='fit':result={'model':args.out,'train_window':result['training_window_s'],'band_training_frames':result['multiband']['training_frames']}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
