"""Train-only nonlinear, periodically varying causal filter research.

The frozen model uses only new input and a clock at replay. All learned
coefficients and private reports remain outside Git. Not native plugin DSP.
"""
from __future__ import annotations
import numpy as np
from scipy import linalg


def features(source,sr,index,rate,scale):
    mono=source.mean(axis=1);lags=np.unique(np.r_[np.arange(0,132,4),np.round(sr*np.array([.004,.006,.009,.012,.018,.025,.04,.08,.15,.25,.4,.6,.8]))]).astype(int)
    at=index[:,None]-lags[None,:];linear=mono[np.clip(at,0,len(mono)-1)]*(at>=0)
    nonlinear=np.tanh(linear[:,:20]/scale)*scale
    t=index/sr
    if rate:
        moving=linear[:,:33]
        return np.column_stack((linear,nonlinear,moving*np.sin(2*np.pi*rate*t)[:,None],moving*np.cos(2*np.pi*rate*t)[:,None]))
    return np.column_stack((linear,nonlinear))


def fit(source,target,sr,train_end,rates=(0.,.15,.25,.4,.6,.9,1.3,2.)):
    if source.shape!=target.shape or source.ndim!=2 or not np.isfinite(source).all() or not np.isfinite(target).all():raise ValueError('Expected finite same-format pair')
    if not 3*sr<=train_end<=len(source):raise ValueError('Need three seconds of training')
    scale=max(float(np.sqrt(np.mean(source[:train_end]**2))),1e-5)
    train=np.arange(round(sr*.1),round(train_end*.7),8);valid=np.arange(round(train_end*.76),train_end,8)
    best=None;decisions=[]
    for rate in rates:
        a=features(source,sr,train,rate,scale);b=features(source,sr,valid,rate,scale)
        gram=a.T@a;rhs=a.T@target[train]
        for ridge in (.001,.01,.1):
            weights=linalg.solve(gram+max(float(np.trace(gram))/len(gram)*ridge,1e-12)*np.eye(len(gram)),rhs,assume_a='pos')
            score=float(np.mean((b@weights-target[valid])**2))
            decisions.append({'rate_hz':rate,'ridge':ridge,'inner_validation_mse':score})
            if best is None or score<best[0]:best=(score,rate,ridge)
    _,rate,ridge=best;index=np.arange(round(sr*.1),train_end,8);a=features(source,sr,index,rate,scale);gram=a.T@a
    weights=linalg.solve(gram+max(float(np.trace(gram))/len(gram)*ridge,1e-12)*np.eye(len(gram)),a.T@target[index],assume_a='pos')
    model={'sample_rate':sr,'rate_hz':rate,'scale':scale,'weights':weights}
    return model,{'selected_rate_hz':rate,'ridge':ridge,'inner_validation':decisions,'selection':'train-only nested validation','independent_performance':'UNVERIFIED'}


def render(source,sr,model):
    if sr!=model['sample_rate'] or not np.isfinite(source).all():raise ValueError('Invalid replay format')
    result=np.empty((len(source),model['weights'].shape[1]))
    for start in range(0,len(source),32768):
        idx=np.arange(start,min(len(source),start+32768))
        result[start:start+len(idx)]=features(source,sr,idx,model['rate_hz'],model['scale'])@model['weights']
    if not np.isfinite(result).all():raise ValueError('Nonfinite periodic replay')
    return result
