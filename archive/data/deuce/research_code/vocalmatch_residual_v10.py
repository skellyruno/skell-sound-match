#!/usr/bin/env python3
"""Skelly VocalMatch v1.0: dry-conditioned residual dynamics/timbre model.

IMPORTANT: offline audio-matching research, NOT a VST3 implementation. The fixed
reference is used for fit only, not for apply; never processes third-party files
without permission. Owns only new output paths; never replaces originals.

Dependency: numpy, scipy, soundfile, scikit-learn (fit), pyloudnorm (audio output).

Commands:
  fit --dry raw.wav --reference desired.wav --v09-model prior.json --out model.json
  apply --dry another.wav --model model.json --out candidate.wav
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy import signal, ndimage
import soundfile as sf
import pyloudnorm as pyln
import skelly_soundmatch_v08 as base
import deuce_contour_v09 as prev

OFFSETS = (0,-16,-8,-4,-2,-1,1,2,4,8,16)
FREQ_BANDS = ((80,500),(500,1500),(1500,5000),(5000,12000))
SMOOTH_SIGMAS = (45,220,880,4410)
POLY_POWERS = (1,2,3)
MAX_SECONDS = 90

def _shift_zeros(x,offset):
    y=np.zeros_like(x)
    if offset==0:return x
    if offset>0:y[offset:]=x[:-offset]
    else:y[:offset]=x[-offset:]
    return y

def _fast_gauss(x,sigma):
    """Gaussian smoothing using FFT for wide windows, with reflect-like edges.
    For sigma<100 use SciPy's fast direct implementation. Large sigma direct
    convolution is quadratic in kernel width; FFT makes repeated matching fast.
    """
    if sigma<100:return ndimage.gaussian_filter1d(x,sigma)
    radius=int(4*sigma+0.5)
    taps=np.arange(-radius,radius+1,dtype=float)
    kernel=np.exp(-.5*(taps/sigma)**2)
    kernel/=np.sum(kernel)
    return signal.fftconvolve(np.pad(x,(radius,radius),mode='symmetric'),kernel,mode='valid')

def _features(dry,processed,sr):
    if len(dry)!=len(processed):raise ValueError('Samples not aligned')
    if len(dry)<sr:raise ValueError('Input must be at least 1 second')
    if len(dry)>MAX_SECONDS*sr:raise ValueError('Audio too long for offline model: 90 second limit')
    # Each feature uses only dry input and output of the previous processing stage.
    # A bounded lookahead (16 samples plus offline envelope) is intentional.
    f=[]
    for source in (processed,dry):
        for shift in OFFSETS:f.append(_shift_zeros(source,shift))
    for source in (processed,dry):
        for lo,hi in FREQ_BANDS:
            if hi>=.48*sr:raise ValueError('Sample rate too low for model filters')
            sos=signal.butter(2,(lo,hi),fs=sr,btype='bandpass',output='sos')
            f.append(signal.sosfilt(sos,source))
    p99=np.percentile(np.abs(processed),99)+1e-10
    # σ=4410 at 44.1 kHz is a 100ms Gaussian smoothing, not a compressor delay.
    rms90=np.sqrt(np.maximum(_fast_gauss(processed**2,200),0)+1e-18)
    p90=float(np.percentile(rms90,90)+1e-10)
    for sigma in SMOOTH_SIGMAS:
        window=np.sqrt(np.maximum(_fast_gauss(processed**2,sigma),0)+1e-18)
        t=np.clip(window/p90,.05,8)
        f.extend((processed*np.log(t),processed/(1+t),processed*t/(1+t)))
    for power in POLY_POWERS:
        f.append(processed*np.clip(np.abs(processed)/p99,0,5)**power)
    F=np.stack(f,axis=1)
    if not np.isfinite(F).all():raise ValueError('Invalid input features')
    return F

def _safe_audition(y,sr,target_lufs=-20,ceiling_dbtp=-1.0):
    if not np.isfinite(y).all():raise ValueError('Non-finite DSP output')
    meter=pyln.Meter(sr)
    before=float(meter.integrated_loudness(y))
    if not np.isfinite(before):raise ValueError('Loudness cannot be determined')
    z=y*10**((target_lufs-before)/20)
    z,limit_info=_smooth_truepeak_guard(z,sr,ceiling_dbtp)
    return z, {'before_lufs':round(before,3),'after_lufs':round(float(meter.integrated_loudness(z)),3),'true_peak_dbtp':round(base.db(base.truepeak(z)),3),**limit_info}

def _smooth_truepeak_guard(y,sr,ceiling_dbtp=-1.0):
    """Offline peak protection: trim isolated peaks locally rather than lowering
    the entire waveform. Oversampled peaks are measured between PCM samples.
    A conservative -0.2 dB margin absorbs resampling reconstruction overshoot.
    """
    z=y.copy()
    target=10**((ceiling_dbtp-.2)/20)
    adjusted=0
    for _ in range(5):
        up=signal.resample_poly(z,4,1)
        peaks,_=signal.find_peaks(np.abs(up),height=target,distance=max(1,round(.004*sr*4)))
        if abs(up[0])>target:peaks=np.r_[0,peaks]
        if abs(up[-1])>target:peaks=np.r_[peaks,len(up)-1]
        if len(peaks)==0:break
        sig=sr*.004
        curve=np.ones(len(z))
        for index in peaks:
            center=index/4
            fraction=min(1.0,target/(abs(up[index])*1.01))
            span=round(sig*4)
            start=max(0,int(center)-span);end=min(len(z),int(center)+span+1)
            t=np.arange(start,end)
            adjustment=1-(1-fraction)*np.exp(-.5*((t-center)/sig)**2)
            curve[start:end]=np.minimum(curve[start:end],adjustment)
        z*=curve
        adjusted+=len(peaks)
    # Last-resort global attenuation only if an extreme input still violates
    # the ceiling; disclose it rather than pretending the result is still at
    # its target loudness.
    z,guard=base.peak_guard(z,ceiling_dbtp)
    return z, {'local_peak_events':int(adjusted),
               'fallback_global_attenuation_db':round(guard['attenuation_db'],4)}

def _v09_base(dry,sr,v09):
    z=prev.render(dry,sr,v09)
    z,_=_safe_audition(z,sr)
    return z

def _train_weights(dry,z,reference,sr,wins,regularization=100):
    from sklearn.ensemble import HistGradientBoostingRegressor
    lo,hi=(int(round(t*sr)) for t in wins['training'])
    # Train from *only* the first ~6 seconds: later phrases are not used for fit.
    ref=reference*base.rms(z[lo:hi])/base.rms(reference[lo:hi]);F=_features(dry,z,sr)
    idx=np.arange(lo,hi,7)
    ff=F[idx];std=np.maximum(np.std(ff,axis=0),1e-7)
    ff=ff/std
    co=np.linalg.solve(ff.T@ff+regularization*np.eye(ff.shape[1]),ff.T@ref[idx])
    pred=(F/std)@co
    # Train small, strongly regularized, dry-conditioned envelope correction.
    X,hop,L,k=prev._frame_features(dry,pred,sr)
    n=k*hop; tgt=10*np.log10(np.mean(ref[:n].reshape(k,hop)**2,axis=1)+1e-18)
    tt=(np.arange(k)+.5)*hop/sr
    ok=(tt>=wins['training'][0])&(tt<wins['training'][1])&(L>-65)&(tgt>-65)
    if ok.sum()<200:raise ValueError('Insufficient active training frames')
    hgb=HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=5,learning_rate=.035,
             min_samples_leaf=30,l2_regularization=10,random_state=0)
    hgb.fit(X[ok],np.clip(tgt-L,-10,10)[ok]); export=prev._tree_export(hgb)
    err=np.max(np.abs(hgb.predict(X)-prev._tree_predict(X,export)))
    if err>1e-7:raise RuntimeError('Tree export did not reproduce prediction')
    return {'feature_std':std.tolist(),'feature_coefficients':co.tolist(),
            'regularization':regularization,'contour_trees':export,
            'contour_limit_db':2.0,'contour_smoothing_frames':2.0,
            'input_sha256':base.sha(str(DRY_FILE)) if DRY_FILE else None,
            'target_sha256':base.sha(str(REF_FILE)) if REF_FILE else None}

DRY_FILE=None;REF_FILE=None

def render(dry,sr,m):
    if sr!=m['sample_rate']:raise ValueError('Sample rate differs from fitted model')
    if len(dry)>MAX_SECONDS*sr:raise ValueError('Audio exceeds 90-second offline limit')
    z=_v09_base(dry,sr,m['v09_model'])
    F=_features(dry,z,sr)
    weight=np.array(m['refinement']['feature_coefficients'],dtype=float)
    scale=np.array(m['refinement']['feature_std'],dtype=float)
    if F.shape[1]!=len(weight) or np.min(scale)<=0:raise ValueError('Invalid learned feature model')
    y=(F/scale)@weight
    if not np.isfinite(y).all():raise ValueError('Invalid residual-filter output')
    X,hop,_,k=prev._frame_features(dry,y,sr)
    gain=prev._tree_predict(X,m['refinement']['contour_trees'])
    gain=np.clip(ndimage.gaussian_filter1d(gain,m['refinement']['contour_smoothing_frames']),
                 -m['refinement']['contour_limit_db'],m['refinement']['contour_limit_db'])
    gain=np.interp(np.arange(len(y)),(np.arange(k)+.5)*hop,gain,left=gain[0],right=gain[-1])
    return y*10**(gain/20)

def fit(dry_path,ref_path,v09_path,out_path):
    global DRY_FILE,REF_FILE
    if Path(out_path).exists():raise FileExistsError('Refusing to overwrite model')
    DRY_FILE=Path(dry_path);REF_FILE=Path(ref_path)
    dry,sr=base.load(dry_path);ref,rs=base.load(ref_path)
    if sr!=rs or len(dry)!=len(ref):raise ValueError('Require equal sample rate and length')
    base.pair_check(dry,ref,sr)
    with open(v09_path) as fp:m9=json.load(fp)
    if sr!=m9['sample_rate']:raise ValueError('v09 model sample rate mismatch')
    windows=base.windows(len(dry),sr);z=_v09_base(dry,sr,m9)
    fitted=_train_weights(dry,z,ref,sr,windows)
    m={'version':'1.0','offline_only':True,'sample_rate':sr,
       'v09_model':m9,'refinement':fitted,'training_window_s':windows['training'],
       'heldout_windows_s':{k:v for k,v in windows.items() if k!='training'},
       'note':'Reference is required to FIT but never read while RENDERING. Model has lookahead. Not a native VST3.'}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(m,indent=1)+'\n')
    return m

def apply(dry_path,model_path,out_path,target_lufs=-20):
    if Path(out_path).exists():raise FileExistsError('Refusing to overwrite audio')
    dry,sr=base.load(dry_path)
    m=json.loads(Path(model_path).read_text())
    z=render(dry,sr,m)
    z,safety=_safe_audition(z,sr,target_lufs)
    sf.write(out_path,np.stack([z,z],axis=1),sr,subtype='PCM_24')
    return {'file':str(out_path),'safety':safety,'sample_rate':sr,'samples':len(z)}

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    f=s.add_parser('fit');f.add_argument('--dry',required=True);f.add_argument('--reference',required=True);f.add_argument('--v09-model',required=True);f.add_argument('--out',required=True)
    a=s.add_parser('apply');a.add_argument('--dry',required=True);a.add_argument('--model',required=True);a.add_argument('--out',required=True);a.add_argument('--lufs',type=float,default=-20)
    c=p.parse_args()
    try:
        if c.cmd=='fit':m=fit(c.dry,c.reference,c.v09_model,c.out);print(json.dumps({'model':c.out,'training_window_s':m['training_window_s']}))
        else:print(json.dumps(apply(c.dry,c.model,c.out,c.lufs),indent=2))
    except Exception as e:p.exit(1,'ERROR: '+str(e)+'\n')

if __name__=='__main__':main()
