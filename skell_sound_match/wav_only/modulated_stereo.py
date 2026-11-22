"""Bounded causal moving-delay stereo research; fit only on a training span.

This is an offline hypothesis, not an inferred proprietary chorus setting.
Fitted coefficients and reports derived from owner audio must remain private.
"""
from __future__ import annotations

import numpy as np


def _mono(audio):
    x=np.asarray(audio,dtype=np.float64)
    if x.ndim!=2 or x.shape[1] not in (1,2) or not np.isfinite(x).all():
        raise ValueError('Expected finite mono/stereo audio')
    return x.mean(axis=1)


def _features(mono,sr,index,base,depth,rate,phase):
    movement=depth*np.sin(2*np.pi*rate*index/sr+phase)
    grid=np.arange(len(mono))
    left=np.interp(index-sr*(base+movement),grid,mono,left=0,right=0)
    right=np.interp(index-sr*(base-movement),grid,mono,left=0,right=0)
    return np.column_stack((mono[index],left,right))


def render(audio,sr,model):
    mono=_mono(audio)
    if model['sample_rate']!=sr:raise ValueError('Model sample rate mismatch')
    p=model['parameters']
    if not 0<=p['depth_s']<=p['base_s']<=.05 or not 0<=p['rate_hz']<=2 or not np.isfinite(p['phase_rad']):
        raise ValueError('Noncausal or invalid delay')
    coefficients=np.asarray(model['coefficients'],dtype=np.float64)
    if coefficients.shape!=(3,2) or not np.isfinite(coefficients).all() or np.max(np.abs(coefficients))>4:
        raise ValueError('Invalid stereo coefficients')
    return _features(mono,sr,np.arange(len(mono)),p['base_s'],p['depth_s'],p['rate_hz'],p['phase_rad'])@coefficients


def errors(candidate,target):
    def relative(a,b):return float(np.sqrt(np.mean((a-b)**2)/max(np.mean(b*b),1e-16)))
    side=lambda a:(a[:,0]-a[:,1])*.5
    mid=lambda a:a.mean(axis=1)
    return {'relative_stereo_rms':relative(candidate,target),
            'relative_side_rms':relative(side(candidate),side(target)),
            'relative_mid_rms':relative(mid(candidate),mid(target)),
            'side_mid_db':float(10*np.log10(max(np.mean(side(candidate)**2),1e-16)/max(np.mean(mid(candidate)**2),1e-16)))}


def fit(audio,target,sr,train,holdout,*,rates=(.15,.25,.4,.6,.9),
        bases=(.002,.006,.012,.02),depths=(.001,.003,.006),phases=(0.,np.pi/2,np.pi,3*np.pi/2)):
    mono=_mono(audio);y=np.asarray(target,dtype=np.float64)
    if y.shape!=(len(mono),2) or not np.isfinite(y).all():raise ValueError('Target must be aligned stereo')
    if not 0<=train[0]<train[1]<holdout[0]<holdout[1]<=len(mono)/sr:
        raise ValueError('Require disjoint chronological train/holdout spans')
    if sr<32000:raise ValueError('Unsupported sample rate')
    # Uniform decimation of fit samples only; delayed samples use full-rate audio.
    index=np.arange(round(train[0]*sr),round(train[1]*sr),8)
    best=None;static=None
    for base in bases:
        for depth in (0.,*depths):
            if depth>base:continue
            for rate in ((0.,) if depth==0 else rates):
                for phase in ((0.,) if depth==0 else phases):
                    design=_features(mono,sr,index,base,depth,rate,phase)
                    gram=design.T@design
                    ridge=max(float(np.trace(gram))*1e-7,1e-12)
                    weights=np.linalg.solve(gram+ridge*np.eye(3),design.T@y[index])
                    if np.max(np.abs(weights))>4:continue
                    error=float(np.mean((design@weights-y[index])**2))
                    model={'schema':'skelly.private.moving-delay.v1','sample_rate':sr,
                           'parameters':{'base_s':float(base),'depth_s':float(depth),
                                         'rate_hz':float(rate),'phase_rad':float(phase)},
                           'coefficients':weights.tolist()}
                    item=(error,model)
                    if depth==0 and (static is None or error<static[0]):static=item
                    if depth>0 and (best is None or error<best[0]):best=item
    if best is None or static is None:raise ValueError('No bounded stereo hypothesis')
    candidate=render(audio,sr,best[1]);baseline=render(audio,sr,static[1])
    scores={}
    for name,span in [('train',train),('holdout',holdout)]:
        sl=slice(round(span[0]*sr),round(span[1]*sr))
        scores[name]={'moving':errors(candidate[sl],y[sl]),'static':errors(baseline[sl],y[sl])}
    h=scores['holdout']
    passed=all(h['moving'][key]<.95*h['static'][key] for key in ('relative_stereo_rms','relative_side_rms'))
    return best[1],{'train_seconds':train,'holdout_seconds':holdout,'scores':scores,
                    'status':'HELDOUT_RESEARCH_PASS' if passed else 'REJECTED_ON_HOLDOUT',
                    'independent_performance':'UNVERIFIED','owner_listening':'UNVERIFIED'}
