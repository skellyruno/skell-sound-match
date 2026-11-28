#!/usr/bin/env python3
"""Deuce / Skelly SoundMatch v0.9 — reference-trained, dry-input dynamics contour.

This is an offline EXPERIMENTAL enhancement to the previous v0.8 tonal model.
Training uses aligned dry, v0.8 baseline and original reference only in a designated
training span. Playback never reads the reference. The v0.8 model is stored in the
v0.9 JSON so the complete audio can be re-rendered from a dry WAV.

Training requires: numpy, scipy, soundfile, scikit-learn
Applying requires: numpy, scipy, soundfile (no sklearn/pickle necessary).
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import ndimage, signal
import skelly_soundmatch_v08 as base8

FREQ_BANDS=[(150,700),(700,2500),(2500,8000)]

def _hash(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()

def _frame_features(x,z,sr):
 # 10 ms control rate, using input-derived features only; no reference at render.
 hop=round(sr*.01)
 k=len(z)//hop
 def pow10(a):return np.mean(a[:k*hop].reshape(k,hop)**2,axis=1)
 def level(p):return 10*np.log10(p+1e-18)
 Z,D=level(pow10(z)),level(pow10(x))
 features=[]
 for a in (Z,D):
  features.extend((a,*(ndimage.gaussian_filter1d(a,s) for s in (1,4,12,35)),
                   a-ndimage.gaussian_filter1d(a,5),
                   ndimage.gaussian_filter1d(a,3)-ndimage.gaussian_filter1d(a,18),
                   np.gradient(ndimage.gaussian_filter1d(a,3))))
 for lo,hi in FREQ_BANDS:
  filtered=signal.sosfilt(signal.butter(2,(lo,hi),fs=sr,btype='bandpass',output='sos'),z)
  features.append(level(pow10(filtered))-Z)
 return np.stack(features,axis=1),hop,Z,k

def _tree_export(model):
 # Export sklearn's learned regression trees as DATA, not pickle/executable code.
 trees=[]
 for layer in model._predictors:
  nodes=layer[0].nodes
  trees.append([{'leaf':bool(v['is_leaf']), 'value':float(v['value']),
                 'feature':int(v['feature_idx']), 'threshold':float(v['num_threshold']),
                 'left':int(v['left']), 'right':int(v['right']),
                 'missing_left':bool(v['missing_go_to_left'])} for v in nodes])
 return {'baseline':float(model._baseline_prediction.ravel()[0]), 'trees':trees}

def _tree_predict(X,stored):
 n=len(X);pr=np.full(n,stored['baseline'],dtype=np.float64)
 for tree in stored['trees']:
  indices=np.zeros(n,dtype=np.int32)
  for _ in range(64):
   unfinished=np.array([not tree[int(i)]['leaf'] for i in indices])
   if not unfinished.any():break
   ix=np.where(unfinished)[0]
   parents=indices[ix]
   # group by node for vectorized threshold comparisons
   for node_id in np.unique(parents):
    rows=ix[parents==node_id]
    node=tree[int(node_id)]
    v=X[rows,node['feature']]
    take_left=np.where(np.isnan(v),node['missing_left'],v<=node['threshold'])
    indices[rows]=np.where(take_left,node['left'],node['right'])
  else:raise ValueError('Tree prediction exceeded depth limit')
  pr+=np.array([tree[int(i)]['value'] for i in indices],dtype=float)
 return pr

def _render_v08(x,sr,m):
 if sr!=m['sample_rate']:raise ValueError('Sample rate incompatible with model')
 y=signal.fftconvolve(x,np.asarray(m['phase_fir_taps']),'same')
 y=base8._apply_gain(y,sr,m['gain']);y,_=base8.peak_guard(y)
 z=signal.fftconvolve(y,np.asarray(m['residual_tone_fir_taps']),'same')
 z*=base8.rms(y)/base8.rms(z)
 z=base8._color(z,blend=.35,drive=float(m.get('color_drive',1.2)))
 z,_=base8.peak_guard(z,float(m.get('truepeak_ceiling_db',-1)))
 return z

def predict_gain(dry,base,sr,model):
 X,hop,_,k=_frame_features(dry,base,sr)
 gains=_tree_predict(X,model['trees'])
 gains=np.clip(ndimage.gaussian_filter1d(gains,1.5),-7,7)
 sample_gains=np.interp(np.arange(len(base)),(np.arange(k)+.5)*hop,gains,
                        left=gains[0],right=gains[-1])
 return sample_gains

def render(dry,sr,m,strength=1.0):
 base=_render_v08(dry,sr,m['v08_model'])
 base*=10**(m['v08_calibration_db']/20)
 g=predict_gain(dry,base,sr,m)
 return base*10**(np.clip(strength,0,1)*g/20)

def fit(dry_path,reference_path,baseline_path,prior_json,out_json):
 from sklearn.ensemble import HistGradientBoostingRegressor
 x,sr=base8.load(dry_path);r,rs=base8.load(reference_path)
 z,zs=base8.load(baseline_path)
 if sr!=rs or sr!=zs or len(x)!=len(r) or len(z)!=len(x):
  raise ValueError('All files must have matching sample rates and sample counts')
 check=base8.pair_check(x,r,sr)
 wins=base8.windows(len(x),sr)
 m8=json.loads(Path(prior_json).read_text())
 rerender=_render_v08(x,sr,m8)
 tr=slice(int(wins['training'][0]*sr),int(wins['training'][1]*sr))
 calibration=20*np.log10(base8.rms(z[tr])/base8.rms(rerender[tr]))
 rerender*=10**(calibration/20)
 # Catch model mismatches instead of fitting a model around the wrong prior.
 rel=base8.rms(z-rerender)/(base8.rms(z)+1e-15)
 if rel>.005:raise ValueError(f'v0.8 baseline did not reproduce from saved model (relative error {rel:.4f})')
 r=r*base8.rms(z[tr])/base8.rms(r[tr])
 features,hop,level,k=_frame_features(x,z,sr)
 def pow10(a):return np.mean(a[:k*hop].reshape(k,hop)**2,axis=1)
 target=10*np.log10(pow10(r)+1e-18)
 t=np.arange(k)*hop/sr
 eligible=(t>=wins['training'][0])&(t<wins['training'][1])&(level>-55)&(target>-55)
 if eligible.sum()<200:raise ValueError('Too few active, aligned training frames')
 values=np.clip(target-level,-16,16)
 model=HistGradientBoostingRegressor(max_iter=120,max_leaf_nodes=10,learning_rate=.04,
                                      l2_regularization=15,min_samples_leaf=25,
                                      random_state=0)
 model.fit(features[eligible],values[eligible]); saved=_tree_export(model)
 maxdiff=np.max(np.abs(model.predict(features)-_tree_predict(features,saved)))
 if maxdiff>1e-7:raise RuntimeError(f'Serialized model mismatch {maxdiff}')
 result={'version':'v0.9','offline_only':True,'sample_rate':sr,'v08_model':m8,
         'v08_calibration_db':float(calibration),'trees':saved,
         'features':'10ms dry+processed levels; 1/4/12/35 frame smoothed envelopes; slopes; three band ratios',
         'max_abs_gain_db':7.0,'training_window_s':wins['training'],
         'input_sha256':_hash(dry_path),'reference_sha256':_hash(reference_path),
         'held_out_windows_s':{'validation':wins['validation'],'late':wins['late']},
         'note':'Predictions use dry and prior-output only, not reference; source v08 phase FIR is noncausal.'}
 Path(out_json).parent.mkdir(parents=True,exist_ok=True)
 if Path(out_json).exists():raise FileExistsError(out_json)
 Path(out_json).write_text(json.dumps(result,indent=2)+'\n')
 return result

def apply(dry_path,model_path,out_path,strength=1.0):
 if Path(out_path).exists():raise FileExistsError('Refusing to overwrite output file: '+out_path)
 x,sr=base8.load(dry_path);m=json.loads(Path(model_path).read_text())
 if sr!=m['sample_rate']:raise ValueError('Sample rate mismatch')
 y=render(x,sr,m,strength)
 y,guard=base8.peak_guard(y,-1.0)
 if not np.isfinite(y).all():raise ValueError('Invalid output samples')
 base8.save_wav(out_path,y,sr)
 return {'out':out_path,'guard':guard,'sample_rate':sr,'input_samples':len(x)}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='mode',required=True)
 a=subs.add_parser('fit');a.add_argument('--dry',required=True);a.add_argument('--reference',required=True);a.add_argument('--baseline',required=True);a.add_argument('--v08-model',required=True);a.add_argument('--out',required=True)
 a=subs.add_parser('apply');a.add_argument('--dry',required=True);a.add_argument('--model',required=True);a.add_argument('--out',required=True);a.add_argument('--strength',type=float,default=1.0)
 q=p.parse_args()
 try:
  if q.mode=='fit':z=fit(q.dry,q.reference,q.baseline,q.v08_model,q.out);z={'model':q.out,'training_window_s':z['training_window_s']}
  else:z=apply(q.dry,q.model,q.out,q.strength)
  print(json.dumps(z,indent=2))
 except Exception as e:p.exit(1,'ERROR: '+str(e)+'\n')
