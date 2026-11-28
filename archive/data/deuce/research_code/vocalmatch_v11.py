#!/usr/bin/env python3
"""Skelly VocalMatch v1.1: selective vocal tone shaping + input-driven gate.

This offline research stage applies to a fitted v1.0 model. It uses reference audio
at model-fitting time ONLY. Apply uses the dry recording and saved JSON.

Commands:
  python vocalmatch_v11.py fit --dry DRY --reference REF --prior MODEL_v10 --out MODEL_v11
       [--tone-1-hz 1712 --tone-1-db -2 --tone-2-hz 6000 --tone-2-db -1]
  python vocalmatch_v11.py apply --dry DRY --model MODEL_v11 --out OUTPUT --lufs -20

The Deuce tone correction was tuned while inspecting all three sections of the
same recording. Those sections must NOT be described as independently held-out.
This process does not recreate any specific proprietary plugin or provide live DSP.
"""
import argparse, json, hashlib
from pathlib import Path
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy import ndimage as ndi, signal
import skelly_soundmatch_v08 as base
import vocalmatch_residual_v10 as v10

GATE_HOP_MS=10
MAX_LENGTH_SECONDS=90

def _filehash(p):
    d=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):d.update(chunk)
    return d.hexdigest()

def frame_levels(x,sr):
    hop=max(1,round(sr*GATE_HOP_MS/1000));n=len(x)//hop
    if n<2:raise ValueError('Audio too short')
    frames=x[:n*hop].reshape(n,hop)
    return 20*np.log10(np.sqrt(np.mean(frames*frames,axis=1)+1e-22)+1e-12),hop

def fit_gate(dry,reference,sr,train):
    x,hop=frame_levels(dry,sr);r,_=frame_levels(reference,sr)
    k=min(len(x),len(r));x=x[:k];r=r[:k]
    t=(np.arange(k)+.5)*hop/sr
    tr=(t>=train[0])&(t<train[1]);on=(r>-70)
    if np.sum(tr&on)<150 or np.sum(tr&~on)<30:
        return {'enabled':False,'reason':'Insufficient isolated silence and voiced training frames'}
    # Hold and smooth values are conservative on purpose: avoid consonant chops.
    smooth=4.;hold=10
    level=ndi.gaussian_filter1d(x,smooth)
    candidates=[]
    for thresh in (-70,-65,-60,-55,-50,-45,-40):
        m=ndi.maximum_filter1d((level>thresh).astype(float),size=hold)>.5
        miss=int(np.sum((~m)&on&tr));leak=int(np.sum(m&(~on)&tr))
        candidates.append((3*miss+leak,thresh,miss,leak))
    score,threshold,miss,leak=min(candidates)
    return {'enabled':True,'threshold_dbfs':threshold,'smoothing_frames':smooth,
            'hold_frames':hold,'fade_frames':1.1,'floor_gain_db':-35,
            'training_missed_active_frames':miss,'training_extra_open_frames':leak,
            'training_frames':int(np.sum(tr))}

def apply_gate(y,dry,sr,p):
    if not p.get('enabled'):return y.copy()
    levels,hop=frame_levels(dry,sr)
    z=ndi.gaussian_filter1d(levels,float(p['smoothing_frames']))
    is_open=ndi.maximum_filter1d((z>float(p['threshold_dbfs'])).astype(float),size=int(p['hold_frames']))
    envelope=ndi.gaussian_filter1d(is_open,float(p['fade_frames']))
    envelope=np.clip(envelope,0,1)
    n=len(y);sample_env=np.interp(np.arange(n),(np.arange(len(levels))+.5)*hop,envelope,
                                    left=envelope[0],right=envelope[-1])
    floor=10**(float(p['floor_gain_db'])/20)
    return y*(floor+(1-floor)*sample_env)

def eq_peak(y,sr,freq,gain_db,q):
    if abs(gain_db)<1e-6:return y
    if not (50<freq<.45*sr and .5<=q<=8 and -6<=gain_db<=6):
        raise ValueError('EQ settings out of safe bounds')
    # RBJ biquad. Applied with filtfilt for offline zero phase; half dB per pass.
    A=10**(gain_db/80)
    w=2*np.pi*freq/sr; c=np.cos(w);alpha=np.sin(w)/(2*q)
    b=np.array([1+alpha*A,-2*c,1-alpha*A]);a=np.array([1+alpha/A,-2*c,1-alpha/A])
    sec=np.r_[b/a[0],1.0,a[1:]/a[0]][None,:]
    return signal.sosfiltfilt(sec,y)

def render(dry,sr,model,variant='precise'):
    if sr!=model['sample_rate']:raise ValueError('Sample rate differs from model')
    if len(dry)>MAX_LENGTH_SECONDS*sr:raise ValueError('Input exceeds 90 seconds')
    y=v10.render(dry,sr,model['prior_v10_model'])
    if variant=='precise':
        for p in model['eq']:
            y=eq_peak(y,sr,p['hz'],p['db'],p['q'])
    elif variant!='gate_only':
        raise ValueError('Unknown variant')
    y=apply_gate(y,dry,sr,model['gate'])
    if not np.isfinite(y).all():raise ValueError('Invalid processing output')
    return y

def loudness_safe_stereo(y,sr,target_lufs=-20,ceiling_dbtp=-1):
    # FIX v1.0: normalizing mono to -20 and subsequently copying to dual-mono
    # makes the delivered stereo WAV +3.01 LUFS louder than the claimed target.
    meter=pyln.Meter(sr)
    stereo=np.column_stack([y,y]);current=float(meter.integrated_loudness(stereo))
    if not np.isfinite(current):raise ValueError('Unable to measure loudness')
    gain=10**((target_lufs-current)/20)
    z=y*gain
    z,peak_info=v10._smooth_truepeak_guard(z,sr,ceiling_dbtp)
    two=np.column_stack([z,z]);actual=float(meter.integrated_loudness(two))
    tpeak=base.db(base.truepeak(z))
    if tpeak>ceiling_dbtp+.015:raise RuntimeError('True-peak safety check failed')
    return two,{'input_dualmono_lufs':round(current,3),'requested_dualmono_lufs':target_lufs,
                'actual_dualmono_lufs':round(actual,3),'measured_truepeak_dbtp':round(tpeak,3),
                'sample_peak_dbfs':round(base.db(np.max(abs(z))),3),**peak_info}

def fit(dry_path,ref_path,prior_model_path,out_path,eq_config):
    if Path(out_path).exists():raise FileExistsError('Refusing to overwrite model')
    dry,sr=base.load(dry_path);ref,rr=base.load(ref_path)
    if sr!=rr or len(dry)!=len(ref):raise ValueError('Same-length and sample rate dry/reference required')
    check=base.pair_check(dry,ref,sr)
    prior=json.loads(Path(prior_model_path).read_text())
    if sr!=prior['sample_rate']:raise ValueError('Prior model sample rate mismatch')
    wins=base.windows(len(dry),sr)
    for p in eq_config:
        if not (50 < p['hz'] < .45*sr and -6 <= p['db'] <= 6 and .5 <= p['q'] <= 8):
            raise ValueError('Unsafe EQ parameters')
    gate=fit_gate(dry,ref,sr,wins['training'])
    model={'version':'1.1','offline_only':True,'sample_rate':sr,'prior_v10_model':prior,
           'gate':gate,'eq':eq_config,'train_window_s':wins['training'],
           'audited_windows_s':{'validation':wins['validation'],'late':wins['late']},
           'dry_sha256':_filehash(dry_path),'reference_sha256':_filehash(ref_path),
           'pair_check':check,
           'caveat':'EQ values were chosen after inspecting the Deuce reference and multiple sections; NOT blind validation. Reference is used only to fit, not render.'}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(model,indent=2)+'\n')
    return model

def apply(dry_path,model_path,out_path,variant='precise',target_lufs=-20):
    if Path(out_path).exists():raise FileExistsError('Refusing to overwrite audio')
    dry,sr=base.load(dry_path);model=json.loads(Path(model_path).read_text())
    y=render(dry,sr,model,variant)
    stereo,safety=loudness_safe_stereo(y,sr,target_lufs)
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    sf.write(out_path,stereo,sr,subtype='PCM_24')
    written,rr=sf.read(out_path,always_2d=True)
    if rr!=sr or len(written)!=len(dry):raise RuntimeError('Export differs in duration or sample rate')
    actual=float(pyln.Meter(sr).integrated_loudness(written))
    if abs(actual-safety['actual_dualmono_lufs'])>.03:raise RuntimeError('Output loudness verification failed')
    if base.db(base.truepeak(written[:,0]))>-1+.02:raise RuntimeError('Export true peak violation')
    return {'out':str(out_path),'variant':variant,'safety':safety,'samples':len(dry),'sample_rate':sr}

def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='cmd',required=True)
    f=subs.add_parser('fit')
    for arg in ('dry','reference','prior','out'):f.add_argument('--'+arg,required=True)
    f.add_argument('--tone-1-hz',type=float,default=1712);f.add_argument('--tone-1-db',type=float,default=0)
    f.add_argument('--tone-2-hz',type=float,default=6000);f.add_argument('--tone-2-db',type=float,default=0)
    a=subs.add_parser('apply')
    for arg in ('dry','model','out'):a.add_argument('--'+arg,required=True)
    a.add_argument('--variant',choices=['precise','gate_only'],default='precise')
    a.add_argument('--lufs',type=float,default=-20)
    q=p.parse_args()
    if q.cmd=='fit':
        eq=[{'hz':q.tone_1_hz,'db':q.tone_1_db,'q':1.8},
            {'hz':q.tone_2_hz,'db':q.tone_2_db,'q':1.8}]
        result=fit(q.dry,q.reference,q.prior,q.out,eq)
        print(json.dumps({'model':q.out,'gate':result['gate'],'eq':eq},indent=2))
    else:print(json.dumps(apply(q.dry,q.model,q.out,q.variant,q.lufs),indent=2))

if __name__=='__main__':main()
