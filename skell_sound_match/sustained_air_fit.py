"""Repeatable, non-overwriting offline fit/apply for SustainedAir research.

Only the caller-specified fitting interval determines parameters. Later
sections are reported separately. Do not present these reports as a fresh-vocal
holdout, nor as evidence that a commercial plugin's DSP was cloned.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
from .sustained_air import AirSettings,render


class AirFitError(ValueError):
    pass


def _load(path):
    x,rate=sf.read(path,always_2d=True,dtype='float64')
    if (rate<32000 or rate>192000 or x.shape[1] not in (1,2) or
        len(x)<rate or not np.isfinite(x).all()):
        raise AirFitError('Unsupported or nonfinite input audio')
    return x,int(rate)


def _highband_error(target, candidate,rate,window):
    lo,hi=window
    a=target[round(lo*rate):round(hi*rate)].mean(axis=1)
    b=candidate[round(lo*rate):round(hi*rate)].mean(axis=1)
    if len(a)<4096:raise AirFitError('Window too short')
    freq,_,A=signal.stft(a,fs=rate,nperseg=2048,noverlap=1024,boundary=None)
    _,_,B=signal.stft(b,fs=rate,nperseg=2048,noverlap=1024,boundary=None)
    band=(freq>=9000)&(freq<=14000)
    ref=np.sqrt(np.mean(np.abs(A[band])**2,axis=0)+1e-18)
    other=np.sqrt(np.mean(np.abs(B[band])**2,axis=0)+1e-18)
    mask=ref>max(float(ref.max())*.01,1e-9)
    if mask.sum()<10:raise AirFitError('No active high-band reference frames')
    signed=20*np.log10((other[mask]+1e-10)/(ref[mask]+1e-10))
    return {'mean_abs_db':float(np.mean(np.abs(signed))),
            'median_signed_db':float(np.median(signed)),
            'active_frames':int(mask.sum())}


def fit(source,reference,rate:int, *, train_window=(0.0,4.8)):
    """Fit two parameters only on train_window; report others after selection."""
    AirSettings().validate(rate)
    if (source.shape!=reference.shape or len(source.shape)!=2 or
        source.shape[1] not in (1,2) or not np.isfinite(source).all() or
        not np.isfinite(reference).all()):
        raise AirFitError('Same-length, same-channel, finite audio required')
    if not (0<=train_window[0]<train_window[1]<=len(source)/rate):
        raise AirFitError('Invalid training window')
    b=_highband_error(reference,source,rate,train_window)
    trials=[(b['mean_abs_db'],0.,-16.)]  # Identity/bypass must be an option.
    for threshold in (-20.,-16.,-12.):
        for amount in (.25,.35,.45):
            settings=AirSettings(amount=amount,threshold_db=threshold)
            y=render(source,rate,settings)
            score=_highband_error(reference,y,rate,train_window)['mean_abs_db']+.06*amount
            trials.append((score,amount,threshold))
    score,amount,threshold=min(trials)
    settings=AirSettings(amount=amount,threshold_db=threshold)
    trial=render(source,rate,settings)
    report={'schema':'skell.sustained-air.fit-report','version':1,
            'training_window_seconds':list(train_window),
            'training_error_baseline_db':b['mean_abs_db'],
            'training_error_trial_db':_highband_error(reference,trial,rate,train_window)['mean_abs_db'],
            'trained_settings':asdict(settings),
            'evaluation_is_same_take':True,
            'candidate_only_processing':True,
            'note':'Audio-only research. No native VST3 has been verified.'}
    return settings,report


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safety(audio,rate):
    if not np.isfinite(audio).all():raise AirFitError('Nonfinite processed audio')
    true_peak=np.max(np.abs(signal.resample_poly(audio,4,1,axis=0)))
    db=20*math.log10(max(float(true_peak),1e-12))
    if db>-1:
        raise AirFitError(f'Output true peak estimate {db:.2f} dBTP exceeds -1 dBTP')
    return db


def fit_files(source_path, reference_path, model_path, trial_path, report_path):
    paths=[Path(x).resolve() for x in (source_path,reference_path,model_path,trial_path,report_path)]
    if len(set(paths))!=len(paths):raise AirFitError('Input/output path collision')
    if any(p.exists() for p in paths[2:]):raise FileExistsError('Refusing to overwrite an existing result')
    x,rate=_load(str(paths[0]));ref,rr=_load(str(paths[1]))
    if rr!=rate or x.shape!=ref.shape:raise AirFitError('Same-take rate/length/channels required')
    duration=len(x)/rate
    window=(0., min(4.8, duration*.5))
    settings,report=fit(x,ref,rate,train_window=window)
    trial=render(x,rate,settings)
    tp=_safety(trial,rate)
    model={'schema':'skell.sustained-air.model','version':1,'sample_rate':rate,
           'source_sha256':_sha(paths[0]),'reference_sha256':_sha(paths[1]),
           'settings':asdict(settings), 'approval':'EXPERIMENT_ONLY'}
    report['estimated_true_peak_dbtp_4x']=tp
    report['training_improvement_db']=report['training_error_baseline_db']-report['training_error_trial_db']
    report['selected_bypass']=settings.amount==0
    for p in paths[2:]:p.parent.mkdir(parents=True,exist_ok=True)
    # Preflight passed; write on different output paths, no modification to input.
    paths[2].write_text(json.dumps(model,indent=2)+'\n',encoding='utf-8')
    sf.write(paths[3],trial,rate,subtype='PCM_24')
    paths[4].write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def apply_files(source_path,model_path,out_path):
    src,model,out=map(lambda p:Path(p).resolve(),(source_path,model_path,out_path))
    if len({src,model,out})!=3:raise AirFitError('Input/output path collision')
    if out.exists():raise FileExistsError('Refusing to overwrite an existing result')
    x,rate=_load(str(src));data=json.loads(model.read_text(encoding='utf-8'))
    if data.get('schema')!='skell.sustained-air.model' or data.get('version')!=1:
        raise AirFitError('Unsupported model schema')
    if data.get('sample_rate')!=rate:raise AirFitError('Model sample rate differs')
    settings=AirSettings(**data['settings'])
    y=render(x,rate,settings)
    tp=_safety(y,rate)
    out.parent.mkdir(parents=True,exist_ok=True)
    sf.write(out,y,rate,subtype='PCM_24')
    return {'output':str(out),'estimated_true_peak_dbtp_4x':tp,'approval':'EXPERIMENT_ONLY'}


def main():
    p=argparse.ArgumentParser(description='Skell Sustained Air - offline fit/apply, experimental')
    sub=p.add_subparsers(dest='mode',required=True)
    f=sub.add_parser('fit')
    f.add_argument('source');f.add_argument('reference')
    for arg in ('model','trial','report'):f.add_argument('--'+arg,required=True)
    a=sub.add_parser('apply');a.add_argument('source');a.add_argument('model');a.add_argument('output')
    args=p.parse_args()
    if args.mode=='fit':out=fit_files(args.source,args.reference,args.model,args.trial,args.report)
    else:out=apply_files(args.source,args.model,args.output)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
