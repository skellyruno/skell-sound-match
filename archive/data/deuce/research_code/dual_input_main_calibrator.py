#!/usr/bin/env python3
"""Read-only Deuce MAIN stage identification from two input-output pairs.

DRY -> MAIN ONLY and RECORDING-ONLY -> FULL CHAIN are two tests of the
same saved MAIN effects. Train on only the first phrase and inspect later
passages. Uses regularized causal/noncausal offline FIR and a 5ms smooth
input-dependent gain model; no proprietary plugin code execution.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np,soundfile as sf,pyloudnorm as pyln
from scipy import signal,ndimage
from sklearn.ensemble import HistGradientBoostingRegressor
import deuce_contour_v09 as trees

SR=44100
TRAIN=(.94,6.84)
TAPS=1201
NFFT=8192

def audio(path):
    x,sr=sf.read(path,always_2d=True)
    if sr!=SR or x.shape[1] not in (1,2) or not np.isfinite(x).all() or not(SR*3<=len(x)<=SR*90):raise ValueError('unsupported audio')
    if x.shape[1]==2:
        mid=x.mean(axis=1)
        if np.sqrt(np.mean((x[:,0]-x[:,1])**2)) > .03*np.sqrt(np.mean(mid*mid)+1e-20):
            raise ValueError('meaningful stereo difference requires stereo processing')
    return x.mean(axis=1)

def linear_fit(pairs, reg=.02):
    num=np.zeros(NFFT//2+1,np.complex128);den=np.zeros(NFFT//2+1)
    w=np.hanning(NFFT)
    lo,hi=(int(v*SR) for v in TRAIN)
    for x,y in pairs:
        if len(x)!=len(y):raise ValueError('unaligned pair')
        for p in range(lo,hi-NFFT,NFFT//4):
            X=np.fft.rfft(x[p:p+NFFT]*w);Y=np.fft.rfft(y[p:p+NFFT]*w)
            num+=np.conj(X)*Y;den+=np.abs(X)**2
    fir=np.fft.irfft(num/(den+reg*np.mean(den)))
    half=TAPS//2
    return np.r_[fir[-half:],fir[:half+1]]

def fir_apply(x,h):
    n=len(h)//2
    return signal.fftconvolve(x,h,'full')[n:n+len(x)]

def frame_feature(x,z):
    w=220;k=len(z)//w
    ff=lambda a:20*np.log10(np.maximum(np.sqrt((a[:k*w].reshape(-1,w)**2).mean(axis=1)),1e-10))
    ix=ff(x);iz=ff(z)
    F=np.column_stack([ix,iz,ndimage.gaussian_filter1d(ix,4),ndimage.gaussian_filter1d(iz,4),
        ndimage.gaussian_filter1d(iz,20),ndimage.gaussian_filter1d(iz,60),
        iz-ndimage.gaussian_filter1d(iz,3),np.gradient(ndimage.gaussian_filter1d(iz,2))])
    return F,iz,w,k

def gain_fit(pairs,h):
    xs,ts=[],[]
    for inp,target in pairs:
        z=fir_apply(inp,h);F,lvl,w,k=frame_feature(inp,z)
        trg=20*np.log10(np.maximum(np.sqrt((target[:k*w].reshape(-1,w)**2).mean(axis=1)),1e-10))
        t=(np.arange(k)+.5)*w/SR
        allowed=(t>=TRAIN[0])&(t<TRAIN[1])&(lvl>-45)&(trg>-45)
        xs.append(F[allowed]);ts.append(np.clip(trg[allowed]-lvl[allowed],-8,8))
    X=np.concatenate(xs);T=np.concatenate(ts)
    model=HistGradientBoostingRegressor(max_iter=60,max_leaf_nodes=9,min_samples_leaf=35,
                l2_regularization=60,learning_rate=.035,random_state=4)
    model.fit(X,T)
    saved=trees._tree_export(model)
    if np.max(abs(trees._tree_predict(X,saved)-model.predict(X)))>1e-8:raise RuntimeError('model export error')
    return saved

def render(x,m):
    h=np.asarray(m['fir'],dtype=float)
    if h.shape!=(TAPS,) or not np.isfinite(h).all() or np.max(abs(h))>10 or not (0<=m['max_gain_change_db']<=6):
        raise ValueError('invalid model data')
    z=fir_apply(x,h)
    F,lev,w,k=frame_feature(x,z)
    gr=trees._tree_predict(F,m['gain_trees'])
    gr=np.clip(ndimage.gaussian_filter1d(gr,3),-m['max_gain_change_db'],m['max_gain_change_db'])
    gr=np.interp(np.arange(len(x)),(np.arange(k)+.5)*w,gr,left=gr[0],right=gr[-1])
    return z*10**(gr/20)

def fit(dry,mainonly,reconly,full,output):
    p=Path(output)
    if p.exists():raise FileExistsError(p)
    d,m,r,f=[audio(a) for a in (dry,mainonly,reconly,full)]
    if len({len(d),len(m),len(r),len(f)})>1:raise ValueError('input mismatch')
    pair=[(d,m),(r,f)]
    fir=linear_fit(pair,reg=.02)
    saved={'version':'1.7-main-stage-calibration','sample_rate':SR,'fir':fir.tolist(),
           'gain_trees':gain_fit(pair,fir),'max_gain_change_db':5.0,
           'training_window_s':TRAIN,'offline_only':True,'fir_lookahead_samples':TAPS//2,
           'training_inputs':['dry->main-only','recording-only->full'],
           'sources_sha256':{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in [('dry',dry),('main_only',mainonly),('record_only',reconly),('combined',full)]},
           'note':'A calibration experiment, NOT a recreation of the 8 proprietary/main plugin slots.'}
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(saved)+'\n');return saved

def main():
    parser=argparse.ArgumentParser();a=parser.add_subparsers(dest='cmd',required=True)
    train=a.add_parser('fit')
    for z in ('dry','mainonly','reconly','full','out'):train.add_argument('--'+z,required=True)
    pred=a.add_parser('apply');pred.add_argument('--input',required=True);pred.add_argument('--model',required=True);pred.add_argument('--out',required=True)
    args=parser.parse_args()
    if args.cmd=='fit':
        m=fit(args.dry,args.mainonly,args.reconly,args.full,args.out)
        print(json.dumps({'model':args.out,'lookahead_samples':m['fir_lookahead_samples'],'training':m['training_inputs']},indent=2))
    else:
        p=Path(args.out)
        if p.exists():raise FileExistsError(p)
        inp=audio(args.input);m=json.loads(Path(args.model).read_text());z=render(inp,m)
        if not np.isfinite(z).all():raise ValueError('invalid output')
        loud=float(pyln.Meter(SR).integrated_loudness(np.column_stack((z,z))))
        z=z*10**((-20-loud)/20)
        tp=20*np.log10(np.max(np.abs(signal.resample_poly(z,4,1)))+1e-12)
        if tp>-1:raise ValueError('unsafe true peak; reject')
        p.parent.mkdir(parents=True,exist_ok=True);sf.write(p,np.column_stack([z,z]),SR,subtype='PCM_24')
        print(json.dumps({'file':str(p),'sample_peak':float(max(abs(z))),'true_peak_dbtp':float(tp)}))
if __name__=='__main__':main()
