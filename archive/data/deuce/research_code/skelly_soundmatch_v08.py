#!/usr/bin/env python3
"""Skelly SoundMatch v0.8 -- experimental, reference-driven audio-only vocal matcher.

No preset required. Fit an offline, centered FIR from a paired dry/wet performance,
learn bounded input-derived level/gating behavior, and offer restrained EQ and
harmonic variations. Hold-out sections are reported, never used to fit parameters.
Preserves original inputs, and never auto-promotes a candidate.

python skelly_soundmatch_v08.py fit --dry dry.wav --reference wet.wav --out Deuce_Result
python skelly_soundmatch_v08.py apply --dry another_dry.wav --model Deuce_Result/model.json --out replay.wav

Dependencies: numpy, scipy, soundfile. All estimated audio processing here is
for offline experimentation and is not a reverse-engineering of the proprietary
preset or a directly real-time/VST3-ready solution.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal,ndimage

BANDS = [(70,120),(120,250),(250,500),(500,1000),(1000,2000),
         (2000,4000),(4000,6000),(6000,10000),(10000,16000)]

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as fp:
  for c in iter(lambda:fp.read(1<<20),b''):h.update(c)
 return h.hexdigest()

def db(v):return float(20*np.log10(max(float(v),1e-14)))
def rms(x):return float(np.sqrt(np.mean(np.asarray(x)**2)+1e-24))
def truepeak(y):return float(np.max(np.abs(signal.resample_poly(y,4,1))))
def peak_guard(y,ceiling_db=-1.0):
 tp=truepeak(y);g=min(1,10**(ceiling_db/20)/(tp+1e-20))
 return y*g,{'before_dbtp':db(tp),'after_dbtp':db(tp*g),'attenuation_db':db(g),'ceiling_dbtp':ceiling_db}

def load(path):
 x,sr=sf.read(path,always_2d=True,dtype='float64')
 if x.shape[1]>2 or x.shape[1]<1:raise ValueError('Only mono and dual-mono WAV are supported; stereo ambience must be handled separately')
 if not np.isfinite(x).all():raise ValueError('Input has NaN/Inf samples')
 if len(x)==0 or np.max(np.abs(x))<1e-8:raise ValueError('Input audio is silent')
 if x.shape[1]==2:
  m=x.mean(axis=1);s=(x[:,0]-x[:,1])/2
  if rms(s)/max(rms(m),1e-15)>.03:raise ValueError('Detected a stereo effect; main-vocal matcher expects dual-mono or mono')
 return x.mean(axis=1),sr

def windows(n,sr):
 d=n/sr
 if d<10:raise ValueError('At least 10 seconds required for separate training and hold-out tests')
 return {'training':(max(.25,.05*d),.365*d),'validation':(.39*d,.645*d),'late':(.70*d,.985*d)}

def _spectral_same_take_score(x,y,sr):
    """Phase/gain-insensitive check for a heavily compressed/EQ'd *same* take.
    Uses changes in the spectral shape across time, not absolute loudness.
    This is a fallback: it does not bypass the timeline alignment requirement.
    """
    n=min(len(x),len(y),int(40*sr))
    centers=[];fc=200.
    while fc<=8000:
        centers.append(fc);fc*=2**(1/3)
    features=[]
    for a in (x[:n],y[:n]):
        f,_,Z=signal.stft(a,fs=sr,nperseg=2048,noverlap=1024)
        p=np.abs(Z)**2
        features.append(np.array([10*np.log10(np.mean(p[(f>=c/1.122)&(f<c*1.122)],axis=0)+1e-12) for c in centers]))
    A,B=features
    active=(A.mean(axis=0)>A.mean(axis=0).max()-30)&(B.mean(axis=0)>B.mean(axis=0).max()-30)
    if np.sum(active)<20:return 0.
    A,B=A[:,active],B[:,active]
    A=A-A.mean(axis=0)-A.mean(axis=1,keepdims=True)+A.mean()
    B=B-B.mean(axis=0)-B.mean(axis=1,keepdims=True)+B.mean()
    return float(max(np.corrcoef(A.ravel(),B.ravel())[0,1],0))

def pair_check(x,y,sr):
 if abs(len(x)-len(y))>round(sr*.05):raise ValueError('Input lengths differ >50ms; re-export the same take')
 n=min(len(x),len(y));b=max(1,round(sr*.005));k=min(n,sr*18)//b
 a=np.abs(x[:k*b]).reshape(k,b).mean(axis=1);c=np.abs(y[:k*b]).reshape(k,b).mean(axis=1)
 a=a-a.mean();c=c-c.mean()
 cc=signal.correlate(c,a,mode='full',method='fft');lags=signal.correlation_lags(len(c),len(a),'full')
 sel=np.abs(lags)<=round(.25*sr/b);i=np.argmax(cc[sel]);lag=lags[sel][i]
 corr=float(cc[sel][i]/(np.linalg.norm(a)*np.linalg.norm(c)+1e-20))
 if corr<.58:
  spectral=_spectral_same_take_score(x,y,sr)
  if spectral<.82:raise ValueError(f'Unable to verify same take (envelope correlation {corr:.2f}, spectral score {spectral:.2f})')
 if abs(lag*b/sr)>.0051:raise ValueError(f'Timeline shift {lag*b/sr*1000:.1f}ms; align dry and processed exports before matching')
 return {'approximate_envelope_lag_ms':round(float(lag*b/sr*1000),2),'same_take_envelope_correlation':round(corr,4),'sample_count':n}

def _welch_transfer(x,y,sr,span):
 a,b=(int(t*sr) for t in span);kw={'fs':sr,'nperseg':4096,'noverlap':3072,'nfft':16384}
 f,px=signal.welch(x[a:b],**kw);_,py=signal.welch(y[a:b],**kw)
 _,cxy=signal.csd(x[a:b],y[a:b],**kw)
 coh=np.abs(cxy)**2/(px*py+1e-24)
 use=(f>=200)&(f<=8000)&(px>px.max()*1e-6)
 score=float(np.median(coh[use])) if use.any() else 0
 if score<.55:raise ValueError(f'Phase transfer is insufficiently coherent ({score:.2f}). Do not infer it from this pair.')
 reg=.02*ndimage.gaussian_filter1d(px,8)+1e-14*px.max()
 H=cxy/(px+reg)
 H=ndimage.gaussian_filter1d(H.real,1.5)+1j*ndimage.gaussian_filter1d(H.imag,1.5)
 h=np.fft.irfft(H,16384);K=1024
 taps=np.r_[h[-K:],h[:K+1]]*np.hanning(2*K+1)
 return taps,{'median_coherence_200_8000Hz':round(score,4),'noncausal_halfwidth_ms':round(K*1000/sr,2),'taps':len(taps)}

def _build_gain_map(x,y,sr,train):
 hop=max(1,round(sr*.01));k=len(x)//hop
 xx=x[:k*hop].reshape(k,hop);rr=y[:k*hop].reshape(k,hop)
 p=np.mean(xx**2,axis=1)+1e-20
 inp=10*np.log10(ndimage.gaussian_filter1d(p,2)+1e-20)
 out=20*np.log10(np.sqrt(np.mean(rr**2,axis=1))+1e-10)
 fast=10*np.log10(p)
 target=np.clip(out-fast,-50,15)
 t=(np.arange(k)+.5)*hop/sr
 sel=(t>=train[0])&(t<train[1]);bins=np.linspace(-115,0,80)
 curves=[]
 for b in bins:
  ok=sel&(abs(inp-b)<5)
  curves.append(float(np.median(target[ok])) if ok.sum()>=5 else np.nan)
 curves=np.array(curves);valid=np.isfinite(curves)
 if valid.sum()<8:raise ValueError('Too few voiced training frames to fit dynamics')
 curves=np.interp(bins,bins[valid],curves[valid]);curves=ndimage.gaussian_filter1d(curves,1.2)
 return {'hop_samples':hop,'bin_db':bins.tolist(),'gain_db':curves.tolist(),
         'dynamic_gain_min_db':-42,'dynamic_gain_max_db':12,'smoothing_sigma_frames':1.2}

def _apply_gain(z,sr,p):
 hop=p['hop_samples'];k=len(z)//hop
 frames=z[:k*hop].reshape(k,hop);pw=np.mean(frames**2,axis=1)+1e-20
 inp=10*np.log10(ndimage.gaussian_filter1d(pw,2)+1e-20)
 gain=np.interp(inp,p['bin_db'],p['gain_db'])
 gain=np.clip(ndimage.gaussian_filter1d(gain,p['smoothing_sigma_frames']),p['dynamic_gain_min_db'],p['dynamic_gain_max_db'])
 pos=(np.arange(k)+.5)*hop
 g=np.interp(np.arange(len(z)),pos,gain,left=gain[0],right=gain[-1])
 return z*10**(g/20)

def _band_db(y,sr):
 f,p=signal.welch(y,fs=sr,nperseg=8192,noverlap=4096)
 return np.array([10*np.log10(np.trapezoid(p[(f>=a)&(f<b)],f[(f>=a)&(f<b)])+1e-20) for a,b in BANDS])

def _fit_tone(z,y,sr,train,amount=.8):
 a,b=(round(t*sr) for t in train)
 # Remove overall gain from curve fitting: don't turn EQ into excessive makeup.
 ref=y[a:b]*rms(z[a:b])/rms(y[a:b])
 err=_band_db(ref,sr)-_band_db(z[a:b],sr)
 err=ndimage.gaussian_filter1d(err,.55)
 err=np.clip(err,-2.5,6)*amount
 freq=np.array([math.sqrt(lo*hi) for lo,hi in BANDS])
 # Hold the correction inside the vocal region, gently return to 0 at DC/Nyquist.
 grid=np.r_[0,25,45,freq,19000,sr/2]
 gains=np.r_[0,0,0,err,0,0]
 taps=signal.firwin2(1025,grid,10**(gains/20),fs=sr)
 return taps,{'band_centres_hz':freq.round(1).tolist(),'correction_db':err.round(3).tolist(),'mix_strength':amount}

def _color(y,blend=.20,drive=1.2):
 if blend<=0:return y
 p99=np.percentile(abs(y),99)+1e-10
 soft=np.tanh(drive*y/p99)*p99/drive
 soft*=rms(y)/rms(soft)
 z=(1-blend)*y+blend*soft
 return z*(rms(y)/rms(z))

def save_wav(path,x,sr):
 if Path(path).exists():raise FileExistsError('Refusing to overwrite: '+str(path))
 sf.write(str(path),x,sr,subtype='PCM_24')

def frame_db(x,sr,ms):
 w=max(1,round(sr*ms*.001));k=len(x)//w
 return 20*np.log10(np.sqrt(np.mean(x[:k*w].reshape(k,w)**2,axis=1))+1e-9)

def metrics(ref,z,sr,sp):
 a,b=(round(t*sr) for t in sp);ref=ref[a:b];z=z[a:b]
 g=rms(ref)/rms(z);z=z*g
 cor=float(np.dot(ref,z)/(np.linalg.norm(ref)*np.linalg.norm(z)+1e-20))
 null=np.sqrt(max(1-cor*cor,1e-20))
 spec=float(np.mean(abs(_band_db(ref,sr)-_band_db(z,sr))))
 env={}
 for ms in [20,200]:
  r=frame_db(ref,sr,ms);v=frame_db(z,sr,ms);active=r>max(-54,np.percentile(r,90)-32)
  env[f'{ms}ms']=round(float(np.mean(abs(r[active]-v[active]))),3) if active.any() else None
 return {'waveform_correlation':round(cor,4),'gain_adjusted_residual_db':round(db(null),2),
         'spectral_error_9band_db':round(spec,3),'envelope_error_db':env,
         'candidate_level_difference_db':round(db(g),3)}

def fit(dry,reference,outdir):
 outdir=Path(outdir)
 if outdir.exists() and any(outdir.iterdir()):raise FileExistsError('Destination is not empty')
 x,sr=load(dry);r,rs=load(reference)
 if sr<36000:raise ValueError('Sample rate below 36 kHz: resample both files to 44.1 or 48 kHz first')
 if sr!=rs:raise ValueError('Sample-rate mismatch')
 checks=pair_check(x,r,sr);n=min(len(x),len(r));x=x[:n];r=r[:n];wins=windows(n,sr)
 outdir.mkdir(parents=True,exist_ok=True)
 taps,phase=_welch_transfer(x,r,sr,wins['training'])
 filtered=signal.fftconvolve(x,taps,'same')
 gainmodel=_build_gain_map(filtered,r,sr,wins['training'])
 base=_apply_gain(filtered,sr,gainmodel);base,guard1=peak_guard(base)
 tonefir,eq=_fit_tone(base,r,sr,wins['training'])
 tone=signal.fftconvolve(base,tonefir,'same');tone*=rms(base)/rms(tone)
 conservative=_color(tone,.20,1.2);conservative,guard2=peak_guard(conservative)
 # A restrained tonal variant to test; preserve the more conservative render.
 tone2=signal.fftconvolve(base,tonefir,'same');tone2*=rms(base)/rms(tone2)
 variant=_color(tone2,.35,1.2);variant,guard3=peak_guard(variant)
 paths={'Conservative':'Deuce_Conservative_v08.wav','Tonal_Alternative':'Deuce_Tonal_Alternative_v08.wav',
        'Base_Only':'Deuce_Base_Only_v08.wav'}
 for name,z in [('Conservative',conservative),('Tonal_Alternative',variant),('Base_Only',base)]:
  save_wav(outdir/paths[name],np.stack([z,z],axis=1),sr)
 measurements={name:{win:metrics(r,z,sr,span) for win,span in wins.items()}
               for name,z in [('Dry',x),('Conservative',conservative),('Tonal_Alternative',variant),('Base_Only',base)]}
 model={'version':'v0.8','sample_rate':sr,'offline_only':True,'fit_reference_sha256':sha(reference),
        'fit_dry_sha256':sha(dry),'coherence':phase,'gain':gainmodel,
        'phase_fir_taps':taps.tolist(),'residual_tone_fir_taps':tonefir.tolist(),
        'tone':eq,'color_blend':.2,'color_drive':1.2,'truepeak_ceiling_db':-1.0,
        'note':'Learned from paired audio. It does not expose original plugin knobs or guarantee transfer to another take.'}
 (outdir/'model.json').write_text(json.dumps(model,indent=1)+'\n')
 report={'status':'LISTENING CANDIDATES ONLY; not approved','checks':checks,
         'sample_rate':sr,'duration_s':round(n/sr,3),'windows_s':wins,
         'phase_model':phase,'tone_model':eq,'safety':{'base':guard1,'conservative':guard2,'tonal_alternative':guard3},
         'input_hashes':{'dry':sha(dry),'reference':sha(reference)},'metrics':measurements,
         'warning':['Same-take held-out sections do not guarantee transfer to unrelated recordings.',
                    'The centered 2049-tap transfer filter is noncausal, with ~23ms lookahead.',
                    'Objective metrics do not establish a perceived percentage match.',
                    'No pitch correction or stereo ambience is included.',
                    'Reference may contain sample clipping; our preview is attenuated to true peak <= -1 dBTP.',
                    'Never blindly promote a candidate without listening.']}
 (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 return report

def apply(dry,model,out):
 if Path(out).exists():raise FileExistsError('Refusing to overwrite existing audio')
 x,sr=load(dry);m=json.loads(Path(model).read_text())
 if sr!=m['sample_rate']:raise ValueError('Model sample rate differs from audio')
 z=signal.fftconvolve(x,np.array(m['phase_fir_taps']),'same')
 z=_apply_gain(z,sr,m['gain']);z,g=peak_guard(z)
 t=signal.fftconvolve(z,np.array(m['residual_tone_fir_taps']),'same');t*=rms(z)/rms(t)
 t=_color(t,m['color_blend'],m['color_drive']);t,g=peak_guard(t,m['truepeak_ceiling_db'])
 save_wav(out,np.stack([t,t],axis=1),sr)
 return {'output':str(out),'safety':g,'sample_rate':sr}

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 a=sub.add_parser('fit');a.add_argument('--dry',required=True);a.add_argument('--reference',required=True);a.add_argument('--out',required=True)
 b=sub.add_parser('apply');b.add_argument('--dry',required=True);b.add_argument('--model',required=True);b.add_argument('--out',required=True)
 args=p.parse_args()
 try:print(json.dumps(fit(args.dry,args.reference,args.out) if args.command=='fit' else apply(args.dry,args.model,args.out),indent=2))
 except Exception as e:p.exit(1,'ERROR: '+str(e)+'\n')
if __name__=='__main__':main()
