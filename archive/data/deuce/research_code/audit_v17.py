#!/usr/bin/env python3
"""v1.7 integrity, safety and stage calibration audit. No vendor plugin loading."""
import sys,hashlib,json,tempfile
from pathlib import Path
import numpy as np,soundfile as sf,pyloudnorm as pyln
from scipy import signal
import dual_input_main_calibrator as multi
import deuce_v17_voicing as voicing

ROOT=Path(__file__).parents[1]
DATA=Path('/mnt/data')
SR=44100
FILES={'dry':DATA/'deuce test dry vocals.wav','rec':DATA/'deuce test record preset vocals.wav',
       'main':DATA/'deuce test main preset no rec preset.wav','reference':DATA/'deuce test main preset vocals.wav',
       'champion':DATA/'Skelly_Deuce_SoundMatch_v1_4/audio/Deuce_v14_Contour_Trial.wav',
       'v16':DATA/'Skelly_Deuce_Chain_Assisted_v1_6/audio/Deuce_v16_Experimental_HighBand.wav',
       'v17':ROOT/'audio/Deuce_v17_ConditionalPresence_EXPERIMENT.wav'}
MODEL=ROOT/'models/Deuce_MainStage_TwoInput.json'

checks=[]
def check(name,ok):
    checks.append({'check':name,'passed':bool(ok)})
    if not ok:raise AssertionError(name)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def band(x,l,h):return voicing.band(x,SR,l,h)
def dbrms(x):
    w=220;n=len(x)//w
    return 20*np.log10(np.maximum(1e-10,np.sqrt((x[:n*w].reshape(-1,w)**2).mean(axis=1))))

def stage_metrics(pair):
    mm=json.loads(MODEL.read_text())
    x,y=pair
    fir=multi.fir_apply(x,np.asarray(mm['fir']))
    learned=multi.render(x,mm)
    out={}
    for label,st,ed in [('middle',7.31,12.09),('late',13.125,18.45)]:
        a,b=int(st*SR),int(ed*SR)
        re=y[a:b]
        results={}
        for key,q in [('FIR_only',fir[a:b]),('FIR_plus_dynamic_gain',learned[a:b])]:
            q=q*np.sqrt(np.mean(re**2))/(np.sqrt(np.mean(q**2))+1e-15)
            corr=float(np.corrcoef(re,q)[0,1]);er,eq=dbrms(re),dbrms(q)
            active=(er>-40)&(eq>-40)
            results[key]={'waveform_corr':round(corr,6),'active_envelope_mae_db':round(float(np.mean(abs(er[active]-eq[active]))),4)}
        out[label]=results
        check(f'{label} stage nonlinearity improves waveform corr',results['FIR_plus_dynamic_gain']['waveform_corr']>results['FIR_only']['waveform_corr']+.03)
        check(f'{label} stage nonlinearity improves envelope',results['FIR_plus_dynamic_gain']['active_envelope_mae_db']<results['FIR_only']['active_envelope_mae_db']-.5)
    return out

def output_metrics(candidate,ref):
    rm=voicing.normalize(ref,SR)
    z,sr=sf.read(candidate,always_2d=True);mono=z.mean(axis=1)
    check(f'{Path(candidate).stem} sample rate',sr==SR)
    check(f'{Path(candidate).stem} dual mono',z.shape[1]==2 and np.all(z[:,0]==z[:,1]))
    check(f'{Path(candidate).stem} all samples finite',np.isfinite(z).all())
    lufs=float(pyln.Meter(SR).integrated_loudness(z))
    tp=float(20*np.log10(np.max(abs(signal.resample_poly(mono,4,1)))+1e-12))
    check(f'{Path(candidate).stem} correct loudness',abs(lufs+20)<.05)
    check(f'{Path(candidate).stem} peak below -1 dBTP',tp<=-1.0)
    w=220;t=(np.arange(len(mono)//w)+.5)*w/SR
    pr,py=dbrms(rm),dbrms(mono)
    spec={}
    for label,a,b in [('opening',.94,6.84),('middle',7.31,12.09),('late',13.125,18.45)]:
        active=(t>=a)&(t<b)&(pr>-37)&(py>-37)
        refhigh,candhigh=band(rm,6500,11000),band(mono,6500,11000)
        rh,yh=dbrms(refhigh),dbrms(candhigh)
        spec[label]={'broadband_5ms_mae_db':round(float(np.mean(abs(pr[active]-py[active]))),3),
            'highband_5ms_mae_db':round(float(np.mean(abs(rh[active]-yh[active]))),3)}
    return {'lufs':round(lufs,4),'true_peak_dbtp':round(tp,4),'passages':spec}

def run():
    start_hash={k:sha(p) for k,p in FILES.items()}
    x,r,m,f=[multi.audio(FILES[k]) for k in ('dry','rec','main','reference')]
    check('all four renders are same sample length',len(set(map(len,[x,r,m,f])))==1)
    check('FST recording source intact',sha(ROOT/'sources/rec deuce.fst')==sha(DATA/'rec deuce.fst'))
    check('FST main source intact',sha(ROOT/'sources/main deuce.fst')==sha(DATA/'main deuce.fst'))
    saved=json.loads(MODEL.read_text())
    check('main-stage model uses two pair types',len(saved['training_inputs'])==2)
    check('training window restricted to opening',saved['training_window_s']==[.94,6.84])
    check('stage input checksums verified',saved['sources_sha256']=={
        'dry':sha(FILES['dry']),'main_only':sha(FILES['main']),
        'record_only':sha(FILES['rec']),'combined':sha(FILES['reference'])})
    report={'reference':'Deuce full combined recording + main-only and recording-only isolated exports',
        'training_window_s':saved['training_window_s'],
        'all_evaluation_passages_previously_consulted':True,
        'main_stage_calibration':{
            'dry_to_main_only':stage_metrics((x,m)),
            'record_only_to_full':stage_metrics((r,f))},
        'reference_vs_v17':output_metrics(FILES['v17'],f),
        'reference_vs_v14':output_metrics(FILES['champion'],f),
        'reference_vs_v16':output_metrics(FILES['v16'],f)}
    with tempfile.TemporaryDirectory() as td:
        pp=Path(td)/'replay.wav'
        voicing.apply(str(FILES['dry']),str(ROOT/'models/Deuce_v14_Contour_Model.json'),
            str(ROOT/'models/Deuce_v17_ConditionalPresence.json'),str(pp))
        check('model replays byte-identical WAV',sha(pp)==sha(FILES['v17']))
        try:
            voicing.apply(str(FILES['dry']),str(ROOT/'models/Deuce_v14_Contour_Model.json'),
                str(ROOT/'models/Deuce_v17_ConditionalPresence.json'),str(pp))
        except FileExistsError:check('no-overwrite guard',True)
        else:check('no-overwrite guard',False)
        stereo=np.column_stack((x,x+.07*np.sin(np.arange(len(x))*2*np.pi*700/SR)))
        q=Path(td)/'stereo.wav';sf.write(q,stereo,SR)
        try:voicing.aud_mono(q)
        except ValueError:check('reject materially stereo audio',True)
        else:check('reject materially stereo audio',False)
        q=Path(td)/'bad_model.json';b=json.loads((ROOT/'models/Deuce_v17_ConditionalPresence.json').read_text());b['strength']=200;q.write_text(json.dumps(b))
        try:voicing.render_from_v14(x,SR,b)
        except ValueError:check('reject unsafe stage strength',True)
        else:check('reject unsafe stage strength',False)
        altered=Path(td)/'altered_prior.json'
        altered.write_bytes((ROOT/'models/Deuce_v14_Contour_Model.json').read_bytes()+b'\n')
        try:voicing.apply(str(FILES['dry']),str(altered),
             str(ROOT/'models/Deuce_v17_ConditionalPresence.json'),str(Path(td)/'bad.wav'))
        except ValueError:check('reject mismatched prior v1.4 model',True)
        else:check('reject mismatched prior v1.4 model',False)
    check('all inputs and protected renders byte unchanged',all(sha(p)==start_hash[k] for k,p in FILES.items()))
    report['quality_gate']={'champion':'v1.4','v17_status':'experiment: high-band improvement but not proven perceptual improvement',
        'main_stage_status':'useful calibration model but full vocal render performs worse than v1.4',
        'not_true_blind_test':True}
    report['checks']=checks;report['tests_passed']=sum(v['passed'] for v in checks)
    (ROOT/'reports/v17_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'tests_passed':report['tests_passed'], 'stage_middle':report['main_stage_calibration']['record_only_to_full']['middle'],
     'v14_high_middle':report['reference_vs_v14']['passages']['middle']['highband_5ms_mae_db'],
     'v17_high_middle':report['reference_vs_v17']['passages']['middle']['highband_5ms_mae_db']},indent=2))
if __name__=='__main__':run()
