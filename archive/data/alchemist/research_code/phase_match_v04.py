#!/usr/bin/env python3
"""Skelly audio-only *phase-transfer experiment* and honest validation report.

This does NOT reconstruct proprietary DSP. It estimates a noncausal offline FIR
transfer from a corresponding wet target and an existing good matching render.
It attempts to close waveform differences that spectral-EQ matching can miss.

Never overwrites the champion file. Fitted on one span, checked on two others.
Pure phase method requires a sufficiently coherent common performance; no
preset (.fst) or original plugin source code is required.

CLI:
  python phase_match_v04.py CHAMPION.wav REFERENCE.wav -o OUTPUT_FOLDER
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal, ndimage

BANDS = [(70,120),(120,250),(250,500),(500,1000),(1000,2000),(2000,4000),(4000,6000),(6000,10000),(10000,16000)]

def read_wav(path):
    a, sr = sf.read(str(path), always_2d=True, dtype='float64')
    if not np.isfinite(a).all(): raise ValueError(f'Nonfinite samples: {path}')
    if len(a) < sr*8: raise ValueError('Need at least 8 seconds')
    if np.max(np.abs(a)) < 1e-8: raise ValueError(f'Silent recording: {path}')
    return a, sr

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def db(v): return float(20*np.log10(max(float(v),1e-16)))
def rms(z): return float(np.sqrt(np.mean(z*z)+1e-24))
def mono(x): return x.mean(axis=1)

def true_peak(x):
    return float(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))))

def safety(x,sr,ceiling_db=-1.0):
    tp=true_peak(x)
    scale=min(1.0,10**(ceiling_db/20)/(tp+1e-12))
    return x*scale, {'input_peak_dbtp':round(db(tp),3),
                     'gain_change_db':round(db(scale),3),
                     'output_peak_dbtp':round(db(tp*scale),3),
                     'ceiling_dbtp':ceiling_db}

def transfer_filter(x,y,sr,train=(1,18),halfwidth=2048):
    """Estimate normalized complex transfer, positive and negative FIR lags.

    Coherence gate prevents false LTI identification for unrelated performances.
    Time-domain Hann truncation limits artifacts from unreliable transfer tails.
    The resulting FIR is centered/noncausal: needs lookahead if ported to VST3.
    """
    sl=slice(int(sr*train[0]),int(sr*train[1]))
    x,y=x[sl],y[sl]
    if len(x)<sr*3: raise ValueError('Training audio must be > 3 seconds')
    nfft=16384
    kw={'fs':sr,'nperseg':8192,'noverlap':4096,'nfft':nfft}
    f,P=signal.welch(x,**kw)
    _,Q=signal.welch(y,**kw)
    _,C=signal.csd(x,y,**kw)
    coh=(np.abs(C)**2)/(P*Q+1e-24)
    active=(f>=150)&(f<=8000)&(P>1e-5*P.max())&(Q>1e-5*Q.max())
    co=float(np.median(coh[active])) if active.any() else 0
    if co < .55: raise ValueError(f'Insufficient spectral coherence ({co:.3f}); cannot safely fit linear phase transfer')
    # Local regularization avoids the treble attenuation of global PSD floors.
    reg=0.02*ndimage.gaussian_filter1d(P,16)+1e-12*P.max()
    H=C/(P+reg)
    H=ndimage.gaussian_filter1d(H.real,1)+1j*ndimage.gaussian_filter1d(H.imag,1)
    # Phase ONLY; leave the successful frequency balance of the champion intact.
    H=H/np.maximum(np.abs(H),1e-9)
    impulse=np.fft.irfft(H,nfft)
    K=halfwidth
    if not (16<=K<=nfft//4): raise ValueError('FIR halfwidth out of range')
    taps=np.r_[impulse[-K:],impulse[:K+1]]*np.hanning(2*K+1)
    # DO NOT normalize taps: normalization could undo natural phase cancellations.
    diagnostics={'median_spectral_coherence':round(co,4),
        'train_window_s':list(train),'fir_taps':len(taps),
        'noncausal_halfwidth_ms':round(K*1000/sr,2),
        'filter_kind':'offline centered FIR, phase-only spectral transfer',
        'caution':'not a zero-latency real-time VST3 filter; requires lookahead or a causal design'}
    return taps,diagnostics

def waveform_metrics(a,b):
    a=np.asarray(a);b=np.asarray(b)
    na=np.linalg.norm(a);nb=np.linalg.norm(b)
    corr=float(np.dot(a,b)/(na*nb+1e-20))
    scale=float(np.dot(a,b)/(np.dot(b,b)+1e-20))
    res=a-scale*b
    null_db=db(rms(res)/(rms(a)+1e-20))
    return {'zero_lag_signed_waveform_correlation':round(corr,4),
            'polarity_agnostic_correlation':round(abs(corr),4),
            'best_single_gain_null_residual_db_relative_to_reference':round(null_db,3),
            'best_fit_gain':round(scale,4)}

def level_curve(z,sr,ms):
    hop=max(1,round(ms*sr/1000));k=len(z)//hop
    frames=z[:k*hop].reshape(k,hop)
    return 20*np.log10(np.sqrt(np.mean(frames*frames,axis=1))+1e-9)

def band_energy(x,sr):
    f,p=signal.welch(x,fs=sr,nperseg=8192,noverlap=4096)
    return np.array([10*np.log10(np.trapezoid(p[(f>=lo)&(f<hi)],f[(f>=lo)&(f<hi)])+1e-20)
                     for lo,hi in BANDS])

def segment_metrics(ref,cand,sr,start,end):
    sl=slice(round(start*sr),round(end*sr));r=ref[sl];c=cand[sl]
    if len(r)<sr:raise ValueError('Validation span too short')
    # Correct loudness only in the metric. Never allow louder to score better.
    r0=rms(r); c0=rms(c)
    ref_level=db(r0/c0)
    f=band_energy(r,sr);g=band_energy(c,sr)+ref_level
    bdiff=g-f
    em={}
    for ms in (10,20,200):
        a=level_curve(r,sr,ms);b=level_curve(c,sr,ms)+ref_level
        act=a>max(-54,float(np.percentile(a,90))-32)
        em[str(ms)+'ms']=round(float(np.mean(np.abs(a[act]-b[act]))) if np.any(act) else 0,3)
    n=max(1,round(sr*.01))
    def crest(z):
        fr=z[:len(z)//n*n].reshape(-1,n)
        return 20*np.log10((np.abs(fr).max(axis=1)+1e-12)/(np.sqrt((fr*fr).mean(axis=1))+1e-12))
    rr=crest(r);cc=crest(c)
    am=level_curve(r,sr,10)>-48
    ln=min(len(rr),len(cc),len(am))
    crest_err=float(np.mean(np.abs(rr[:ln][am[:ln]]-cc[:ln][am[:ln]]))) if np.any(am[:ln]) else 0
    out={**waveform_metrics(r,c),
         'level_difference_to_reference_db':round(ref_level,3),
         'spectral_bands_mae_db':round(float(np.mean(np.abs(bdiff))),3),
         'per_band_candidate_minus_reference_db':{f'{lo}-{hi}':round(float(v),2) for (lo,hi),v in zip(BANDS,bdiff)},
         'active_envelope_mae_db':em,
         'active_10ms_crest_mae_db':round(crest_err,3)}
    return out

def gentle_dynamics_trial(processed,reference,sr,train=(1,18)):
    """Very mild dynamics trial, estimated ONLY on training samples.

    No target envelope from holdout is ever used to construct the gain curve;
    future vocals will require separate listening verification.
    """
    hop=max(1,round(sr*.02))
    xdb=level_curve(processed,sr,20)
    rdb=level_curve(reference,sr,20)
    n=min(len(xdb),len(rdb));xdb=xdb[:n];rdb=rdb[:n]
    times=(np.arange(n)*hop+hop/2)/sr
    active=(times>=train[0])&(times<train[1])&(xdb>-44)&(rdb>-42)
    if active.sum()<120:raise ValueError('Insufficient voiced training frames for gentle dynamics fitting')
    # Robust-ish trimmed fit: only quiet/active 20 ms RMS frames, not silences.
    f=np.column_stack([xdb[active],np.ones(active.sum())])
    slope,intercept=np.linalg.lstsq(f,rdb[active],rcond=None)[0]
    # Limit compression slope and shape corrections; avoid crush+makeup exploits.
    slope=float(np.clip(slope,0.80,1.0))
    center=float(np.median(xdb[active]))
    curve_db=np.clip((slope-1)*(xdb-center),-2.5,2.5)
    curve_db*=np.clip((xdb+48)/12,0,1) # no noise pumping in quiet gaps
    curve_db=ndimage.gaussian_filter1d(curve_db,3)
    tpos=np.arange(n)*hop+hop/2
    interp_db=np.interp(np.arange(len(processed)),tpos,curve_db,left=curve_db[0],right=curve_db[-1])
    y=processed*10**(interp_db/20)
    return y,{'detected_dynamic_slope':round(float(slope),3),
              'estimated_training_intercept_db':round(float(intercept),2),
              'gain_curve_max_abs_db':round(float(np.max(np.abs(curve_db))),3),
              'gain_bound_db':2.5,'smoothing_ms':60,
              'note':'Nonlinear time-varying gain approximation, NOT CLA-76/CLA-2A cloning.'}

def assess(reference,original,experiment,sr,train=(1,18),validation=(19,35),late=(35,42)):
    sets={'fitting_section':train,'validation_section':validation,'late_section':late}
    return {name:{'time_s':list(bounds),
            'champion_v03':segment_metrics(reference,original,sr,*bounds),
            'phase_trial_v04':segment_metrics(reference,experiment,sr,*bounds)}
            for name,bounds in sets.items()}

def choose_windows(duration_s):
    """Fit and evaluate disjoint phrases, with meaningful windows even at 10 s."""
    if duration_s >= 42.5:
        return (1,18),(19,35),(35,min(42,duration_s-.1))
    if duration_s < 9.0:
        raise ValueError('At least 9 seconds required for 3 separate test sections')
    a=max(.3,duration_s*.035)
    train=(a,duration_s*.43)
    validation=(duration_s*.46,duration_s*.71)
    late=(duration_s*.74,duration_s-a)
    if min(train[1]-train[0],validation[1]-validation[0],late[1]-late[0])<1.0:
        raise ValueError('Need longer clip for train/validation/late test')
    return train,validation,late

def audio_profile(audio,sr):
    m=mono(audio)
    lv=level_curve(m,sr,200)
    active=lv>max(-60,float(np.percentile(lv,90))-35)
    spread=float(np.percentile(lv[active],90)-np.percentile(lv[active],10)) if active.any() else 0
    out={'rms_dbfs':round(db(rms(m)),3),
        'sample_peak_dbfs':round(db(np.max(np.abs(audio))),3),
        'true_peak_dbtp_4x_estimate':round(db(true_peak(audio)),3),
        'active_200ms_p90_minus_p10_spread_db':round(spread,3)}
    if audio.shape[1]>1:
        mid=(audio[:,0]+audio[:,1])/2
        side=(audio[:,0]-audio[:,1])/2
        out['side_to_mid_db']=round(db(rms(side)/rms(mid)),3)
    try:
        import pyloudnorm as pyln
        # LUFS is computed using the file's natural level, not matched test gain.
        out['integrated_loudness_lufs']=round(float(pyln.Meter(sr).integrated_loudness(audio)),3)
    except ImportError:
        out['integrated_loudness_lufs']=None
    return out

def main(champion,reference,outdir,train=None,validate=None,late=None,halfwidth=2048):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    c,sr=read_wav(champion);r,rr=read_wav(reference)
    if sr!=rr:raise ValueError('Sample rate mismatch: render both at same sample rate')
    if abs(len(c)-len(r))>sr//2:raise ValueError('Waveform comparison requires matching exported timelines')
    n=min(len(c),len(r));c=c[:n];r=r[:n]
    auto_train,auto_validate,auto_late=choose_windows(n/sr)
    train=train if train is not None else auto_train
    validate=validate if validate is not None else auto_validate
    late=late if late is not None else auto_late
    if max(late[1],validate[1],train[1])>n/sr:raise ValueError('Training/validation bounds exceed audio length')
    if r.shape[1]>=2:
        mid=(r[:,0]+r[:,1])/2;side=(r[:,0]-r[:,1])/2
        width=db(rms(side)/(rms(mid)+1e-20))
        if width>-30:
            raise ValueError(f'Target contains significant stereo ambience (side-to-mid {width:.1f} dB). Isolate its dry/center channel before using mono phase transfer.')
    cm=mono(c);rm=mono(r)
    taps,meta=transfer_filter(cm,rm,sr,train,halfwidth)
    corrected=signal.fftconvolve(cm,taps,mode='same')
    # Only apply a genuinely mono model to mono/dual-mono material.
    # Preserve experimental audio as a two-channel dual-mono preview.
    preview, guard = safety(np.repeat(corrected[:,None],2,axis=1),sr,-1.0)
    x=mono(preview)
    dyn, dyninfo = gentle_dynamics_trial(x,rm,sr,train)
    dyn_stereo,dyn_guard=safety(np.repeat(dyn[:,None],2,axis=1),sr,-1.0)
    dyn=mono(dyn_stereo)
    comparisons=assess(rm,cm,x,sr,train,validate,late)
    for name,(a0,b0) in [('fitting_section',train),('validation_section',validate),('late_section',late)]:
        comparisons[name]['phase_plus_dynamics_trial_v04B']=segment_metrics(rm,dyn,sr,a0,b0)
    val=comparisons['validation_section']; latev=comparisons['late_section']
    old,new=val['champion_v03'],val['phase_trial_v04']
    # Audio-only mathematical gate. LISTEN before choosing a new champion.
    passed=(new['polarity_agnostic_correlation'] > old['polarity_agnostic_correlation']+0.05 and
            new['spectral_bands_mae_db'] <= old['spectral_bands_mae_db'] + 0.08 and
            new['active_envelope_mae_db']['20ms'] <= old['active_envelope_mae_db']['20ms']+0.15 and
            latev['phase_trial_v04']['spectral_bands_mae_db'] <= latev['champion_v03']['spectral_bands_mae_db']+0.15)
    # Dynamics extension must improve held-out envelope without spoiling tone.
    dynval=val['phase_plus_dynamics_trial_v04B']
    dynlate=latev['phase_plus_dynamics_trial_v04B']
    dynpassed=(dynval['active_envelope_mae_db']['20ms'] < new['active_envelope_mae_db']['20ms']-0.05 and
        dynval['spectral_bands_mae_db'] <= new['spectral_bands_mae_db']+0.08 and
        dynlate['active_envelope_mae_db']['20ms'] <= latev['phase_trial_v04']['active_envelope_mae_db']['20ms']+0.04)
    # Target audition copy at same RMS as the preview (no peak maximizing).
    gain=rms(x)/(rms(rm)+1e-20)
    target_quiet=r*gain
    target_quiet, ref_guard=safety(target_quiet,sr,-1.0)
    prefix='Alchemist' if 'alchemist' in Path(reference).stem.lower() else 'Skelly_Match'
    a=out/f'{prefix}_PhaseMatched_v04_EXPERIMENT.wav'
    b=out/f'{prefix}_Reference_LevelMatched_For_v04.wav'
    sf.write(a,preview,sr,subtype='PCM_24')
    dyn_path=out/f'{prefix}_PhaseAndDynamics_v04B_EXPERIMENT.wav'
    sf.write(dyn_path,dyn_stereo,sr,subtype='PCM_24')
    sf.write(b,target_quiet,sr,subtype='PCM_24')
    report={'status':'experimental_candidate_champion_unchanged',
        'champion_name':Path(champion).name,'champion_sha256':sha256(champion),
        'reference_sha256':sha256(reference),
        'sample_rate_hz':sr,'duration_s':round(n/sr,3),
        'audio_profiles':{'reference':audio_profile(r,sr),'champion_v03':audio_profile(c,sr),
                          'phase_trial_v04':audio_profile(preview,sr),
                          'phase_plus_dynamics_v04B':audio_profile(dyn_stereo,sr)},
        'reported_by_listener':'about 90% similarity (subjective; not derived from metrics)',
        'filter':meta,'preview_true_peak_guard':guard,'reference_audition_true_peak_guard':ref_guard,
        'gentle_dynamics_fit':dyninfo,'dynamics_preview_true_peak_guard':dyn_guard,
        'sections':comparisons,
        'objective_quality_gate_passed':bool(passed),
        'dynamics_trial_quality_gate_passed':bool(dynpassed),
        'replacement_authorized':False,
        'artifacts':{'phase_only_wav':a.name,'phase_and_dynamics_wav':dyn_path.name,'level_matched_reference_wav':b.name},
        'warnings':['Objective waveform correlation is not a percentage of audible similarity.',
                    'Phase or polarity changes may be inaudible in solo playback, but affect null tests and parallel mixing.',
                    'A fitted linear transfer cannot replicate nonlinear compressor dynamics, harmonics or performance-dependent effects.',
                    'The phase correction is offline and noncausal; not suitable for low-latency VST3 without redesign.',
                    'Validation and late sections are distinct from training, but all are from the same vocal take.',
                    'The reference audition file is level-adjusted for comparison; it is not the unaltered reference.']}
    rp=out/f'{prefix}_v04_Waveform_Dynamics_Audit.json'
    rp.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report,cm,rm,x,sr,out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('champion');ap.add_argument('reference');ap.add_argument('-o','--outdir',default='phase_trial_output')
    ap.add_argument('--taps-halfwidth',type=int,default=2048)
    a=ap.parse_args()
    rep,*_=main(a.champion,a.reference,a.outdir,halfwidth=a.taps_halfwidth)
    val=rep['sections']['validation_section']
    print(json.dumps({'status':rep['status'],'quality_gate':rep['objective_quality_gate_passed'],
        'validation':val,'preview_peak':rep['preview_true_peak_guard']},indent=2))
