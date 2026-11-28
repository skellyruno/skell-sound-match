#!/usr/bin/env python3
"""Conservative offline reference-EQ diagnostic; not an automatic VST3 preset.

Only derives *static EQ* from a SAME-TAKE named source/processed pair.
Fits on a training window and evaluates on a disjoint holdout. Never edits
source WAVs; render is optional, uses a safe estimated true-peak ceiling.
"""
from __future__ import annotations
import argparse, json, math, hashlib
from pathlib import Path
import numpy as np
from scipy import signal, optimize
import soundfile as sf
import pyloudnorm as pyln

CENTERS=(100,220,470,1000,2100,4300,8000,13000)
BANDS=((80,160),(160,350),(350,700),(700,1600),(1600,4000),(4000,8000),(8000,14000))

def db(x):return 20*np.log10(np.maximum(x,1e-12))

def peaking(sr, hz, q, gain_db):
    if hz>=0.49*sr:raise ValueError('Peaking band beyond Nyquist')
    w=2*np.pi*hz/sr; a=10**(gain_db/40); alpha=np.sin(w)/(2*q); c=np.cos(w)
    coeff=np.array([1+alpha*a,-2*c,1-alpha*a,1+alpha/a,-2*c,1-alpha/a],dtype='float64')
    return coeff/coeff[3]

def psd(x,sr):
    # Same stereo aggregation for source and target (not destructive mid collapse).
    f,p=signal.welch(x,fs=sr,axis=0,nperseg=4096,noverlap=2048)
    return f,p.mean(axis=1)

def weighted_fit(x,y,sr,max_abs_db=8.):
    f, px=psd(x,sr); _,py=psd(y,sr)
    ix=(f>=80)&(f<=min(14000,sr/2-100))
    # Exclude frequency bins that are very close to silence in the original or target.
    power_floor=max(float(px.max())*1e-6,1e-16)
    reference_floor=max(float(py.max())*1e-6,1e-16)
    ix &= (px>power_floor)&(py>reference_floor)
    if ix.sum()<100:raise ValueError('Not enough active frequency bins')
    target_db=10*np.log10(np.maximum(py[ix],1e-18)/np.maximum(px[ix],1e-18))
    basis=[]
    for hz in CENTERS:
        _,resp=signal.freqz(peaking(sr,hz,1.0,1.0)[:3],peaking(sr,hz,1.0,1.0)[3:],worN=2*np.pi*f[ix]/sr)
        basis.append(db(np.abs(resp)))
    A=np.stack(basis,axis=1)
    weights=np.minimum(1.,np.sqrt(px[ix]/np.percentile(px[ix],65)))
    # log-frequency balance: equal emphasis across octaves, not per linear FFT bin
    octave=1/np.sqrt(np.maximum(f[ix],80))
    weights*=octave/np.max(octave)
    weights=np.sqrt(np.maximum(weights,.03))
    # Penalize extreme or oscillating boosts; do not fit song-specific spectral notches.
    ridge=.04 * math.sqrt(len(target_db))
    rows=[A*weights[:,None],ridge*np.eye(len(CENTERS)),ridge*np.diff(np.eye(len(CENTERS)),axis=0)]
    rhs=[target_db*weights,np.zeros(len(CENTERS)),np.zeros(len(CENTERS)-1)]
    lo=np.full(len(CENTERS),-max_abs_db);hi=np.full(len(CENTERS),max_abs_db)
    # Caps in sibilance/air protect against blindly boosting noise floor.
    hi[-2:]=5.0
    fit=optimize.lsq_linear(np.vstack(rows),np.concatenate(rhs),bounds=(lo,hi),tol=1e-9,max_iter=250)
    return [float(v) for v in fit.x]

def apply_eq(x,sr,gains):
    if len(gains)!=len(CENTERS):raise ValueError('Unexpected EQ gain count')
    if not np.all(np.isfinite(x)):raise ValueError('Nonfinite input')
    sos=np.array([peaking(sr,hz,1.0,g) for hz,g in zip(CENTERS,gains)])
    return signal.sosfilt(sos,x.astype(np.float64),axis=0)


def linked_leveler(x, sr, slope=-0.4, tau_s=0.025, level_db=-26.0, state=None):
    """Original causal stereo-linked, gently smoothed offline dynamics trial.

    A negative slope compresses envelope contrast, not a proprietary compressor
    emulation. Silence/noise below -55 dBFS does not receive positive makeup.
    State is a pair of scipy lfilter memories; pass it across blocks for parity.
    """
    if slope>0 or slope < -0.9 or not(0.005<=tau_s<=0.5):
        raise ValueError('Unsafe leveler trial settings')
    x=np.asarray(x,dtype='float64')
    if x.ndim!=2 or x.shape[1] not in (1,2) or not np.isfinite(x).all():
        raise ValueError('Expected finite mono/stereo [frames,channels]')
    a=np.exp(-1/(sr*tau_s)); b=np.exp(-1/(sr*.025))
    prev=(np.zeros(1),np.zeros(1)) if state is None else state
    e,mem1=signal.lfilter([1-a],[1,-a],np.mean(x*x,axis=1),zi=prev[0])
    level=10*np.log10(np.maximum(e,1e-10))
    control_db=np.clip(slope*(level-level_db),-7.,7.)
    # Taper positive makeup when the source is too quiet: don't boost floor/tails.
    control_db *= np.clip((level+55.)/10.,0.,1.)
    smooth,mem2=signal.lfilter([1-b],[1,-b],10**(control_db/20),zi=prev[1])
    return x*smooth[:,None],(mem1,mem2)


def choose_leveler(source_eq, target, sr, train_s):
    """Choose exclusively using training samples; no holdout or target render leakage."""
    l=int(round(train_s[0]*sr));r=int(round(train_s[1]*sr))
    original=env_mae(target[l:r],source_eq[l:r],sr)
    best=(float(original),0.,0.025)
    # Optimize a small conservative, fixed offline search instead of a
    # time-varying gain curve trained to specific lyrics or the target waveform.
    for tau in (0.025,0.07,0.15):
        for slope in (-0.8,-0.6,-0.4,-0.2):
            y,_=linked_leveler(source_eq[:r],sr,slope,tau)
            score=env_mae(target[l:r],y[l:r],sr)
            if score<best[0]-0.005:
                best=(score,slope,tau)
    return {'slope':best[1], 'envelope_tau_s':best[2],
            'train_eq_only_env_mae_db':float(original),
            'train_selected_env_mae_db':float(best[0])}

def env_mae(ref,cand,sr,ms=200):
    # RMS match before envelope comparison; no time-shift optimization on holdout.
    a=np.mean(ref,axis=1); b=np.mean(cand,axis=1)
    b=b*float(np.sqrt(np.mean(a*a))/max(np.sqrt(np.mean(b*b)),1e-12))
    win=int(round(sr*ms/1000));hop=max(1,int(round(sr*.01)))
    def env(q):
        z=np.concatenate((np.zeros(1),np.cumsum(q*q)))
        starts=np.arange(0,len(q)-win+1,hop)
        return np.sqrt(np.maximum((z[starts+win]-z[starts])/win,1e-18))
    ar=env(a);br=env(b);active=ar>max(ar.max()*.025,1e-7)
    return float(np.mean(np.abs(db(br[active]/ar[active]))))

def band_mae(ref,cand,sr):
    mid1=ref.mean(axis=1);mid2=cand.mean(axis=1)
    ratio=float(np.sqrt(np.mean(mid1*mid1))/max(np.sqrt(np.mean(mid2*mid2)),1e-12))
    f,p1=signal.welch(mid1,fs=sr,nperseg=4096,noverlap=2048)
    _,p2=signal.welch(mid2*ratio,fs=sr,nperseg=4096,noverlap=2048)
    residuals={}
    for low,high in BANDS:
        m=(f>=low)&(f<high)
        x=np.sqrt((np.trapezoid(p1[m],f[m]) if hasattr(np,'trapezoid') else np.trapz(p1[m],f[m])));y=np.sqrt((np.trapezoid(p2[m],f[m]) if hasattr(np,'trapezoid') else np.trapz(p2[m],f[m])))
        residuals[f'{low}-{high}']=float(db(y/max(x,1e-12)))
    return float(np.mean(np.abs(list(residuals.values())))),residuals

def truepeak(x):
    # Finite segments with padding for 4x interpolation; estimated only, not certified.
    peak=0.0;span=220500;extra=256
    for i in range(0,len(x),span):
        l=max(0,i-extra);r=min(len(x),i+span+extra)
        hi=signal.resample_poly(x[l:r],4,1,axis=0)
        low=(i-l)*4;up=(min(len(x),i+span)-l)*4
        peak=max(peak,float(np.max(np.abs(hi[low:up]))))
    return 20*math.log10(max(peak,1e-12))

def match(source_path,target_path,train_s,holdout_s,output=None):
    a,sr=sf.read(source_path,always_2d=True,dtype='float64'); b,sr2=sf.read(target_path,always_2d=True,dtype='float64')
    if sr!=sr2 or a.shape!=b.shape or a.shape[1] not in (1,2):raise ValueError('Same-take references must have identical sample rate, shape and start offset')
    if not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Nonfinite audio')
    if not 32000<=sr<=192000:raise ValueError('Unsupported sample rate')
    def segment(z,win):
        l,r=(int(round(v*sr)) for v in win)
        if l<0 or r>len(z) or r-l<sr:raise ValueError('Window out of range or under 1 second')
        return z[l:r]
    if train_s[0]>=train_s[1] or holdout_s[0]>=holdout_s[1] or not(train_s[1]<=holdout_s[0] or holdout_s[1]<=train_s[0]):raise ValueError('Train and holdout must not overlap')
    source_train,target_train=segment(a,train_s),segment(b,train_s)
    source_test,target_test=segment(a,holdout_s),segment(b,holdout_s)
    gains=weighted_fit(source_train,target_train,sr)
    eq_full=apply_eq(a,sr,gains)
    leveler=choose_leveler(eq_full,b,sr,train_s)
    combined,_=linked_leveler(eq_full,sr,leveler['slope'],leveler['envelope_tau_s'])
    scores={}
    for name,ref,src in [('train',target_train,source_train),('holdout',target_test,source_test)]:
        sl=slice(int(round((train_s if name=='train' else holdout_s)[0]*sr)),int(round((train_s if name=='train' else holdout_s)[1]*sr)))
        corrected=eq_full[sl]
        completed=combined[sl]
        v0,res0=band_mae(ref,src,sr)
        v1,res1=band_mae(ref,corrected,sr)
        v2,res2=band_mae(ref,completed,sr)
        scores[name]={'baseline_mean_abs_band_db':v0,'eq_mean_abs_band_db':v1,
                      'combined_mean_abs_band_db':v2,
                      'band_improvement_db':v0-v2,'baseline_envelope_200ms_mae_db':env_mae(ref,src,sr),
                      'eq_envelope_200ms_mae_db':env_mae(ref,corrected,sr),
                      'combined_envelope_200ms_mae_db':env_mae(ref,completed,sr),
                      'baseline_band_residual_db':res0,'eq_band_residual_db':res1,'combined_band_residual_db':res2}
    result={'schema':'skelly.offline.eq-linked-leveler-trial.v2','status':'experimental_not_preset','source':source_path.name,'target':target_path.name,
            'source_sha256':hashlib.sha256(Path(source_path).read_bytes()).hexdigest(),
            'target_sha256':hashlib.sha256(Path(target_path).read_bytes()).hexdigest(),
            'sample_rate':sr,'train_seconds':train_s,'holdout_seconds':holdout_s,
            'centers_hz':list(CENTERS),'gain_db':gains,'training_selected_linked_leveler':leveler,'scores':scores,
            'limits':['Same take only; source/target chain provenance not independently verified','Static EQ + leveler trial is not an exact compressor, de-esser, saturation, spatial FX, or plugin chain match',
                      'Holdout is another section of the same take, not another performance','Estimated 4x true peak is not a certified limiter or BS.1770 meter','Not a native VST3 render or owner-approved preset']}
    if output is not None:
        output=Path(output)
        if output.exists():raise FileExistsError(output)
        rendered=combined
        # Safe preview output: match target integrated level as closely as possible without exceeding TP limit.
        target_lufs=float(pyln.Meter(sr).integrated_loudness(b));trial_lufs=float(pyln.Meter(sr).integrated_loudness(rendered))
        requested_db=target_lufs-trial_lufs
        proposed=rendered*10**(requested_db/20)
        tp=truepeak(proposed)
        limited_db=min(0.,-1.2-tp)
        preview=proposed*10**(limited_db/20)
        if float(np.max(np.abs(preview)))>=1 or not np.isfinite(preview).all():raise ValueError('Unsafe preview output')
        output.parent.mkdir(parents=True,exist_ok=True)
        sf.write(output,preview,sr,subtype='PCM_24')
        result['preview']={'filename':output.name,'loudness_gain_requested_db':requested_db,'safety_trim_db':limited_db,
                           'estimated_true_peak_dbtp_4x':truepeak(preview),'sample_peak_dbfs':float(db(np.max(np.abs(preview))))}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('target',type=Path)
    p.add_argument('--train',nargs=2,type=float,required=True);p.add_argument('--holdout',nargs=2,type=float,required=True)
    p.add_argument('--output',type=Path);p.add_argument('--report',type=Path,required=True)
    ns=p.parse_args()
    paths=[ns.source.resolve(),ns.target.resolve(),ns.report.resolve()]+([ns.output.resolve()] if ns.output else [])
    if len(set(paths))!=len(paths):raise ValueError('All input/output paths must be distinct')
    if ns.report.exists() or (ns.output and ns.output.exists()):raise FileExistsError('Refusing to overwrite a report or preview')
    res=match(ns.source,ns.target,tuple(ns.train),tuple(ns.holdout),ns.output)
    ns.report.parent.mkdir(parents=True,exist_ok=True);ns.report.write_text(json.dumps(res,indent=2)+'\n')
    print(json.dumps({'source':res['source'],'target':res['target'],'eq_gain_db':res['gain_db'],'scores':res['scores'],'preview':res.get('preview')},indent=2))
if __name__=='__main__':main()
