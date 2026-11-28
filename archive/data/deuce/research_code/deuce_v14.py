#!/usr/bin/env python3
"""Skelly Deuce v1.4 — fitted 5 ms phrase-envelope residual.

A safe offline AUDITION stage above protected v1.3A.  Train uses the same dry
performance and reference ONLY within the declared training window.  Apply
reads only dry audio + saved model and does not access the reference.

No claim of replicating proprietary compressors or real-time performance.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import soundfile as sf
from scipy import ndimage,signal
import pyloudnorm as pyln
import deuce_v13 as prior
import deuce_contour_v09 as trees
import skelly_soundmatch_v08 as pairguard

TRAIN=(0.94,6.84)

def hashfile(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def mono(path):
    z,s=sf.read(path,always_2d=True)
    if z.shape[1] not in (1,2):raise ValueError('Only mono or dual-mono WAV supported')
    if z.shape[1] == 2:
        mid=z.mean(axis=1);side=(z[:,0]-z[:,1])*.5
        if np.sqrt(np.mean(side*side))/max(np.sqrt(np.mean(mid*mid)),1e-12)>.03:
            raise ValueError('Meaningful stereo effect detected; use a dedicated stereo matching stage')
    if len(z)<s*3 or not np.isfinite(z).all():raise ValueError('Invalid or too short audio')
    return z.mean(axis=1),int(s)

def frames(dry,y,sr):
    if len(dry)!=len(y) or sr<8000:raise ValueError('Incompatible audio')
    w=round(sr*.005)
    k=len(y)//w
    a=y[:k*w].reshape(k,w);d=dry[:k*w].reshape(k,w)
    ld=lambda z:20*np.log10(np.sqrt(np.mean(z*z,axis=1))+1e-9)
    ly=ld(a);lr=ld(d);peak=20*np.log10(np.max(abs(a),axis=1)+1e-9)
    ys=ndimage.gaussian_filter1d(ly,3);rs=ndimage.gaussian_filter1d(lr,3)
    F=np.column_stack([ly,ys,ndimage.gaussian_filter1d(ly,15),lr,rs,
         peak-ly,ys-np.roll(ys,3),np.roll(ys,-3)-ys,rs-ys])
    return F,w,k,ly

def _target_loudness(z,sr,lufs=-20):
    stereo=np.column_stack((z,z))
    measured=float(pyln.Meter(sr).integrated_loudness(stereo))
    if not np.isfinite(measured):raise ValueError('Cannot normalize silent audio')
    return z*10**((lufs-measured)/20)

def render(dry,sr,m):
    if sr!=m['sample_rate'] or len(dry)>sr*90 or not np.isfinite(dry).all():
        raise ValueError('Invalid dry audio or incompatible sample rate')
    # This exact prior remains the protected, listening-preferred v1.3A.
    y=prior.render(dry,sr,m['v13A_prior'])
    y=_target_loudness(y,sr)
    F,w,k,level=frames(dry,y,sr)
    p=m['residual_contour']
    if not (0<=p['strength']<=1.5 and 0<p['max_prediction_db']<=2 and
            .5<=p['smoothing_frames']<=10):raise ValueError('Unsafe gain parameters')
    gains=trees._tree_predict(F,p['trees'])
    gain=np.clip(gains,-p['max_prediction_db'],p['max_prediction_db'])
    gain=ndimage.gaussian_filter1d(gain,p['smoothing_frames'])*p['strength']
    gain=np.interp(np.arange(len(y)),(np.arange(k)+.5)*w,gain,left=gain[0],right=gain[-1])
    result=y*10**(gain/20)
    if not np.isfinite(result).all():raise ValueError('Nonfinite result')
    return result

def fit(dry_path, reference_path, prior_model, out_path):
    if Path(out_path).exists():raise FileExistsError(out_path)
    from sklearn.ensemble import HistGradientBoostingRegressor
    x,sr=mono(dry_path);ref,rs=mono(reference_path)
    if len(x)!=len(ref) or sr!=rs:raise ValueError('Dry and reference must align')
    if len(x)<sr*10:raise ValueError('Need at least 10 seconds for training and evaluation passages')
    pairguard.pair_check(x,ref,sr)
    m=json.loads(Path(prior_model).read_text())
    if m['sample_rate']!=sr:raise ValueError('Prior model sample rate mismatch')
    y=_target_loudness(prior.render(x,sr,m),sr)
    # Training/reference sample gain must be consistent. Apply only reference
    # training-section gain calibration, never full-file held-out content.
    lo,hi=(int(v*sr) for v in TRAIN)
    r_scale=np.sqrt(np.mean(y[lo:hi]**2))/max(np.sqrt(np.mean(ref[lo:hi]**2)),1e-10)
    ref=ref*r_scale
    F,w,k,ly=frames(x,y,sr)
    target=20*np.log10(np.sqrt(np.mean(ref[:k*w].reshape(k,w)**2,axis=1))+1e-9)
    T=np.arange(k)*w/sr
    tr=(T>=TRAIN[0])&(T<TRAIN[1])&(ly>-37)&(target>-37)
    if tr.sum()<300:raise ValueError('Not enough aligned active vocal frames')
    reg=HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=12,
        min_samples_leaf=30,learning_rate=.045,l2_regularization=25,random_state=1)
    reg.fit(F[tr],np.clip(target-ly,-4,4)[tr])
    model=trees._tree_export(reg)
    if np.max(np.abs(reg.predict(F)-trees._tree_predict(F,model)))>1e-7:
        raise RuntimeError('Serialized model prediction mismatch')
    saved={'version':'1.4', 'sample_rate':sr,'offline_only':True,
         'v13A_prior':m,'training_window_s':list(TRAIN),
         'residual_contour':{'trees':model,'strength':1.25,
             'max_prediction_db':2,'smoothing_frames':1,
             'trained_active_frames':int(tr.sum()),'control_rate_ms':1000*w/sr},
         'reference_sha256':hashfile(reference_path), 'dry_sha256':hashfile(dry_path),
         'note':'Only training window used for fitting. Middle and later passages were inspected during development, so not independent blind validation.'}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(saved,indent=2)+'\n')
    return saved

def apply(dry_path,model_path,out_path, lufs=-20):
    out=Path(out_path)
    if out.exists():raise FileExistsError(out)
    dry,sr=mono(dry_path); m=json.loads(Path(model_path).read_text())
    y=render(dry,sr,m)
    y=_target_loudness(y,sr,lufs)
    true_peak=20*np.log10(np.max(np.abs(signal.resample_poly(y,4,1)))+1e-12)
    if true_peak>-1:raise ValueError(f'True peak {true_peak:.2f} dBTP exceeds -1; reject, do not silently turn down')
    stereo=np.column_stack((y,y))
    out.parent.mkdir(parents=True,exist_ok=True)
    sf.write(out,stereo,sr,subtype='PCM_24')
    z,rs=sf.read(out,always_2d=True)
    actual=pyln.Meter(sr).integrated_loudness(z)
    tp=20*np.log10(np.max(np.abs(signal.resample_poly(z[:,0],4,1)))+1e-12)
    if not np.isfinite(z).all() or abs(actual-lufs)>.05 or tp>-1+.02 or len(z)!=len(dry):
        out.unlink(missing_ok=True);raise RuntimeError('Saved PCM verification failed')
    return {'file':str(out),'sample_rate':rs,'frames':len(z), 'lufs':round(float(actual),4), 'truepeak_dbtp':round(float(tp),4)}

if __name__=='__main__':
    ap=argparse.ArgumentParser();sb=ap.add_subparsers(dest='action',required=True)
    fitcmd=sb.add_parser('fit');ac=sb.add_parser('apply')
    for s in (fitcmd,ac):
        s.add_argument('--dry',required=True);s.add_argument('--out',required=True)
    fitcmd.add_argument('--reference',required=True);fitcmd.add_argument('--prior',required=True)
    ac.add_argument('--model',required=True)
    args=ap.parse_args()
    if args.action=='fit':
        z=fit(args.dry,args.reference,args.prior,args.out);print(json.dumps({'model':args.out,'training':z['training_window_s']}))
    else:print(json.dumps(apply(args.dry,args.model,args.out),indent=2))
