#!/usr/bin/env python3
"""Skelly VocalMatch v0.7: conservative, testable, same-take vocal finishing.

REFINE: takes a previously good, same-take audio match and a reference. Fits a
bounded polynomial harmonic correction and causal-envelope-driven dynamic gain
on TRAIN audio only. Validates on disjoint timeline windows. NEVER overwrites
an input or promotes a new candidate without listener approval.

AUDIT: reports aligned, gain-adjusted spectral, envelope, transient and null
metrics without editing audio. No original .fst required. This is *not* a
proprietary-plugin clone or a real-time VST3 implementation. DSP learned here
cannot be assumed to generalize to a new singer without revalidation.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,pathlib,re,sys
import numpy as np
import soundfile as sf
from scipy import signal,ndimage,optimize
from phase_match_v04 import (read_wav,mono,sha256,db,rms,segment_metrics,
                              audio_profile,true_peak,safety,choose_windows)

MAX_CTRL_DB=.60
MAX_HARMONIC_COEFF=.018
HOP_SEC=.01


def check_pair(reference,prior,sr,min_seconds=9):
    """Reject common A/B pitfalls rather than silently testing wrong takes."""
    if reference.shape[1] not in (1,2) or prior.shape[1] not in (1,2):
        raise ValueError('Use mono or dual-mono WAV: stereo ambience requires a separate stage')
    n=min(len(reference),len(prior))
    if n < int(sr*min_seconds): raise ValueError('Need at least 9 seconds')
    if abs(len(reference)-len(prior))>int(.05*sr):
        raise ValueError('Files differ in length by more than 50 ms; align/export the same performance')
    for label,x in [('reference',reference),('previous',prior)]:
        if not np.isfinite(x).all(): raise ValueError(f'{label}: NaN/Inf present')
        if np.max(np.abs(x))<1e-7: raise ValueError(f'{label} is silent')
        if x.shape[1]==2:
            mid=(x[:,0]+x[:,1])/2;side=(x[:,0]-x[:,1])/2
            if rms(side)/max(rms(mid),1e-12)>.03:
                raise ValueError(f'{label} has significant stereo side signal; process ambience separately')
    b=max(1,round(sr*.005))
    nn=min(n,sr*17)//b*b
    def env(x):
        return np.mean(np.abs(mono(x[:nn]).reshape(-1,b)),axis=1)
    a=env(reference);c=env(prior)
    a-=a.mean();c-=c.mean()
    l=signal.correlation_lags(len(a),len(c),'full');cc=signal.correlate(a,c,'full',method='fft')
    mask=np.abs(l)<=round(.25*sr/b)
    ix=np.argmax(cc[mask]);lag=int(l[mask][ix]);corr=float(cc[mask][ix]/(np.linalg.norm(a)*np.linalg.norm(c)+1e-14))
    if corr<.60: raise ValueError(f'Time-varying envelopes do not resemble same take (correlation={corr:.3f})')
    if abs(lag*b/sr)>.0051:
        raise ValueError(f'Files are displaced by {lag*b/sr*1000:.1f} ms; align before refinement')
    return {'envelope_alignment_5ms_blocks':lag,'envelope_alignment_correlation':round(corr,4),
            'aligned_within_ms':5,'length_difference_samples':len(reference)-len(prior)}


def fit_harmonics(prior,reference,sr,train):
    """One small, input-derived nonlinear curve. Explicitly preserve prior RMS."""
    sl=slice(int(train[0]*sr),int(train[1]*sr))
    x=prior[sl];r=reference[sl]
    p99=float(np.percentile(np.abs(x),99))
    if p99<1e-4: raise ValueError('Too little source level for harmonic fitting')
    refscale=rms(r)/rms(x)
    xx=x[::7];rr=r[::7]/refscale
    def objective(c):
        y=xx+c*xx**3/p99**2
        y*=rms(xx)/rms(y)
        # mild penalty for inventing distortion to match one recording
        return float(np.mean((y-rr)**2)+3e-5*c*c)
    fit=optimize.minimize_scalar(objective,bounds=(-MAX_HARMONIC_COEFF,MAX_HARMONIC_COEFF),method='bounded',
                                 options={'xatol':1e-5})
    coef=float(fit.x)
    shaped=prior+coef*prior**3/p99**2
    norm=float(rms(x)/rms(shaped[sl]))
    shaped*=norm
    return shaped,{'cubic_coefficient':round(coef,6),'coefficient_at_limit':abs(coef)>MAX_HARMONIC_COEFF-.002,
                   'training_p99':round(p99,7),'training_gain_normalization_db':round(db(norm),5),
                   'algorithm':'gentle bounded cubic waveshaper, no uncontrolled makeup gain'}


def frame_level(x,sr,hop):
    n=len(x)//hop
    p=np.mean(x[:n*hop].reshape(n,hop)**2,axis=1)+1e-14
    return p,10*np.log10(p)


def dynamic_features(x,sr,train):
    hop=max(1,round(sr*HOP_SEC))
    p,level=frame_level(x,sr,hop)
    timeline=(np.arange(len(level))+.5)*hop/sr
    active=(timeline>=train[0])&(timeline<train[1])&(level>-43)
    if active.sum()<100:raise ValueError('Too little voiced training audio')
    def detector(ms):
        a=np.exp(-(hop/sr)/(ms/1000))
        return 10*np.log10(signal.lfilter([1-a],[1,-a],p)+1e-14)
    f20=detector(20);s120=detector(120);s280=detector(280)
    center=float(np.median(s280[active]))
    feats=np.column_stack(((s280-center)/10,(f20-s280)/10))
    gate=np.clip((s120+49)/11,0,1)
    return {'hop':hop,'features':feats,'gate':gate,'level':level,
            'time':timeline,'active':active,'samples':len(x)}


def control(f,params):
    g=np.clip(f['features'] @ np.asarray(params),-MAX_CTRL_DB,MAX_CTRL_DB)*f['gate']
    # Smooth the gain signal, NOT the waveform; offline interpolation adds <= 10ms lookahead.
    return ndimage.gaussian_filter1d(g,1.5,mode='nearest')


def fit_dynamics(x,ref,sr,train):
    feat=dynamic_features(x,sr,train)
    hop=feat['hop'];rpow,rdb=frame_level(ref,sr,hop)
    xpow,xdb=frame_level(x,sr,hop)
    mask=feat['active']&(rdb>-43)
    if mask.sum()<100: raise ValueError('Too little matched reference signal')
    # Only differential gain shape, not absolute loudness. True-peak guard at output.
    global_gain=10*np.log10(rpow[mask].sum()/xpow[mask].sum())
    wanted=rdb-xdb-global_gain
    def objective(p):
        diff=wanted[mask]-control(feat,p)[mask]
        return float(np.mean(np.sqrt(diff*diff+.4**2))+.025*np.sum(np.asarray(p)**2))
    opt=optimize.minimize(objective,np.zeros(2),method='L-BFGS-B',
                          bounds=[(-.35,.35),(-.35,.35)],options={'maxiter':110})
    g=control(feat,opt.x)
    pos=(np.arange(len(g))+.5)*hop
    # Noncausal <= one analysis block. Must be adapted before low-latency VST3 use.
    samples=np.interp(np.arange(len(x)),pos,g,left=0,right=g[-1])
    output=x*10**(samples/20)
    return output,{'slow_level_coefficient':round(float(opt.x[0]),6),
                   'fast_minus_slow_coefficient':round(float(opt.x[1]),6),
                   'training_reference_level_offset_db_excluded_from_processing':round(global_gain,3),
                   'max_control_db':MAX_CTRL_DB,'control_max_abs_db':round(float(np.max(np.abs(g))),3),
                   'detectors_ms':[20,120,280],'block_ms':round(hop/sr*1000,3),
                   'smoothing_sigma_frames':1.5,'training_loss':round(float(opt.fun),5),
                   'runtime_uses_reference_audio':False}


def safe_stereo(x,sr):
    y=np.column_stack((x,x))
    return safety(y,sr,-1.)


def metrics_for(reference,prev,trial,sr):
    windows=choose_windows(len(trial)/sr)
    result={}
    for name,win in zip(('training','validation','late'),windows):
        result[name]={'start_end_s':list(win), 'previous':segment_metrics(reference,prev,sr,*win),
                      'trial':segment_metrics(reference,trial,sr,*win)}
    old=result['validation']['previous'];n=result['validation']['trial']
    lold=result['late']['previous'];ln=result['late']['trial']
    # Require both heldouts to improve transient dynamics with tolerable spectral drift.
    gate=(n['active_envelope_mae_db']['20ms']<=old['active_envelope_mae_db']['20ms']-.015 and
          ln['active_envelope_mae_db']['20ms']<=lold['active_envelope_mae_db']['20ms'] and
          n['spectral_bands_mae_db']<=old['spectral_bands_mae_db']+.035 and
          ln['spectral_bands_mae_db']<=lold['spectral_bands_mae_db']+.055 and
          n['zero_lag_signed_waveform_correlation']>=old['zero_lag_signed_waveform_correlation']-.001)
    return result,bool(gate)


def refine(reference_path,previous_path,outdir,label='Skelly'):
    outdir=pathlib.Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    label=re.sub(r'[^a-zA-Z0-9_-]','_',label)[:40] or 'Skelly'
    ref,sr=read_wav(reference_path);before,ps=read_wav(previous_path)
    if sr!=ps:raise ValueError(f'Sample-rate mismatch: {sr} vs {ps} Hz')
    # Handle different duration within 50ms by truncating, with explicit report.
    align=check_pair(ref,before,sr)
    n=min(len(ref),len(before));r=mono(ref[:n]);x=mono(before[:n])
    train,valid,late=choose_windows(n/sr)
    shaped,h=fit_harmonics(x,r,sr,train)
    trial,d=fit_dynamics(shaped,r,sr,train)
    stereo,guard=safe_stereo(trial,sr)
    y=mono(stereo)
    measurements,gate=metrics_for(r,x,y,sr)
    previous_tp=db(true_peak(before[:n]))
    new_tp=guard['output_peak_dbtp']
    peak_change_db=round(new_tp-previous_tp,3)
    gate=bool(gate and abs(peak_change_db)<=1.5 and new_tp<=-0.999)
    filename=f'{label}_v07_EXPERIMENT.wav'
    output=outdir/filename
    resolved_inputs={pathlib.Path(reference_path).resolve(),pathlib.Path(previous_path).resolve()}
    if output.resolve() in resolved_inputs or output.exists() or (outdir/f'{label}_v07_report.json').exists():
        raise FileExistsError(f'Will not overwrite input or existing trial: {output}')
    sf.write(output,stereo,sr,subtype='PCM_24')
    report={'status':'EXPERIMENTAL - listening approval required',
       'quality_gate_passed':gate,'promoted_to_champion':False,
       'reference_sha256':sha256(reference_path),'previous_sha256':sha256(previous_path),
       'output_sha256':sha256(output),'sample_rate':sr,'samples':n,
       'alignment':align,'harmonic_model':h,'dynamic_model':d,
       'safety':{**guard,'previous_peak_dbtp':round(previous_tp,3),'peak_change_from_previous_db':peak_change_db, 'max_permitted_abs_peak_change_db':1.5},'metrics':measurements,
       'audio_profiles':{'reference':audio_profile(ref[:n],sr),'prior':audio_profile(before[:n],sr),
                         'trial':audio_profile(stereo,sr)},
       'warnings':['Same-take heldout test sections have been inspected during model development: not a blind external validation.',
                   'Matching a waveform does not identify the original proprietary processing.',
                   'Offline fitted phase filter in v0.4-v0.6 ancestry does not port directly to low latency VST3.',
                   'This is a post-processing stage: start with audio-only or guided original VocalMatch to make a good initial match.',
                   'Do not confuse a tiny objective gain with perceptible improvement.']}
    (outdir/f'{label}_v07_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return output,report


def audit(reference_path,candidate_path):
    a,sr=read_wav(reference_path);b,bs=read_wav(candidate_path)
    if sr!=bs:raise ValueError('Sample-rate mismatch')
    alignment=check_pair(a,b,sr)
    n=min(len(a),len(b));r=mono(a[:n]);x=mono(b[:n])
    wins=choose_windows(n/sr)
    return {'reference_sha256':sha256(reference_path),'candidate_sha256':sha256(candidate_path),
            'alignment':alignment,'profiles':{'reference':audio_profile(a[:n],sr),'candidate':audio_profile(b[:n],sr)},
            'sections':{name:segment_metrics(r,x,sr,*win) for name,win in zip(('train','validation','late'),wins)}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    a=sub.add_parser('refine',help='fit conservative refinement on training passage')
    a.add_argument('--reference',required=True);a.add_argument('--previous',required=True)
    a.add_argument('--output',required=True);a.add_argument('--name',default='NewVocal')
    b=sub.add_parser('audit',help='inspect waveform, envelope and spectrum with no DSP')
    b.add_argument('--reference',required=True);b.add_argument('--candidate',required=True);b.add_argument('--report')
    z=parser.parse_args()
    try:
        if z.command=='refine':
            path,r=refine(z.reference,z.previous,z.output,z.name)
            print(json.dumps({'output':str(path),'quality_gate_passed':r['quality_gate_passed'],
                              'validation':r['metrics']['validation'],'late':r['metrics']['late'],
                              'safety':r['safety']},indent=2))
        else:
            r=audit(z.reference,z.candidate)
            if z.report:pathlib.Path(z.report).write_text(json.dumps(r,indent=2)+'\n')
            print(json.dumps(r,indent=2))
    except Exception as exc:
        parser.exit(1,'ERROR: '+str(exc)+'\n')

if __name__=='__main__':main()
