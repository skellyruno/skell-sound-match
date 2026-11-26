"""Stage-by-stage PCM comparison; no automatic gain/lag fitting for pass/fail.
Usage: python compare.py expected.wav actual.wav --lag 0 --output result.json
Positive lag means actual is delayed by that many samples. Use the same declared
latency on both performances, not a newly optimized shift per file.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def rms(x):return float(np.sqrt(np.mean(np.square(x,dtype=np.float64))))
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def peak(x):return db(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))))
def compare(ref,actual,sr,lag=0):
    a,b=np.asarray(ref,dtype=np.float64),np.asarray(actual,dtype=np.float64)
    if a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=2 or not 32000<=sr<=192000 or not sr<=len(a)<=120*sr or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('same bounded finite stereo geometry required')
    if type(lag)!=int or abs(lag)>min(sr//2,len(a)//10):raise ValueError('invalid declared lag')
    if rms(a)<1e-7:raise ValueError('silent reference')
    full_null=db(rms(b-a)/rms(a)); pk=peak(b)
    # Align only with declared fixed latency; report removed edges separately.
    if lag>0:x,y=a[:-lag],b[lag:]
    elif lag<0:x,y=a[-lag:],b[:lag]
    else:x,y=a,b
    e=y-x;err=rms(e);rel=db(err/max(rms(x),1e-15));maxerr=float(np.max(abs(e)))
    gain=float(np.sum(x*y)/max(np.sum(y*y),1e-30));gain_res=db(rms(y*gain-x)/max(rms(x),1e-15));corr=float(np.sum(x*y)/max(np.sqrt(np.sum(x*x)*np.sum(y*y)),1e-30))
    f,P=signal.welch(x,sr,nperseg=min(4096,len(x)),axis=0);_,Q=signal.welch(y,sr,nperseg=min(4096,len(y)),axis=0)
    bands=[]
    for lo,hi in zip([40,100,250,500,1000,2000,4000,8000],[100,250,500,1000,2000,4000,8000,min(16000,sr/2)]):
        i=(f>=lo)&(f<hi)
        if not np.any(i):continue
        pa=float(P[i].sum());pb=float(Q[i].sum());bands.append({'hz':[lo,hi],'difference_db':None if pa<1e-15 else db(np.sqrt(pb/max(pa,1e-30)))})
    edge_rms=rms(np.concatenate((a[-lag:],b[:lag]),axis=0)) if lag>0 else rms(np.concatenate((a[:-lag],b[lag:]),axis=0)) if lag<0 else 0.
    # Diagnostic engineering thresholds, not psychoacoustic proof. PCM tolerance 2 LSB.
    return dict(frames=len(a),sample_rate=sr,declared_lag_samples=lag,compared_frames=len(x),excluded_edge_rms=edge_rms,raw_null_db=full_null,aligned_null_db=rel,peak_abs_difference=maxerr,rms_difference=err,correlation=corr,diagnostic_optimal_gain=gain,gain_corrected_null_db=gain_res,actual_estimated_dbtp=pk,band_differences=bands,bit_identical=bool(lag==0 and np.array_equal(a,b)),within_two_pcm24_lsb=bool(lag==0 and maxerr<=2/8388608),near_null_gate=bool(rel<=-60 and maxerr<=.001 and pk<=0 and edge_rms<=1e-6))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference');p.add_argument('candidate');p.add_argument('--lag',type=int,default=0);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
    if out.exists():raise FileExistsError(out)
    x,s=sf.read(a.reference,always_2d=True,dtype='float64');y,t=sf.read(a.candidate,always_2d=True,dtype='float64')
    if s!=t:raise ValueError('different sample rates')
    r=compare(x,y,s,a.lag);r.update(reference_sha256=sha(a.reference),candidate_sha256=sha(a.candidate));out.write_text(json.dumps(r,indent=2,allow_nan=False));print(json.dumps({k:r[k] for k in ['raw_null_db','aligned_null_db','near_null_gate','bit_identical','actual_estimated_dbtp']}))
if __name__=='__main__':main()
