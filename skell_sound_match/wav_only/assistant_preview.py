"""Offline bounded causal FIR audition. Caller verifies take/stage/alignment."""
import numpy as np
from scipy import signal, linalg


def fit(source, reference, rate, taps=64, strength=.5):
    x,t=map(lambda a:np.asarray(a,dtype=np.float64),(source,reference))
    if x.shape!=t.shape or x.ndim!=2 or x.shape[1] not in (1,2) or not 32000<=rate<=192000 or not rate<=len(x)<=min(60*rate,1920000) or not np.isfinite(x).all() or not np.isfinite(t).all() or np.max(np.abs(x))>4 or np.max(np.abs(t))>4:
        raise ValueError('invalid aligned audio')
    if taps not in (16,64,256) or strength not in (.25,.5,1.): raise ValueError('invalid preview budget')
    w=np.lib.stride_tricks.sliding_window_view(x,taps,axis=0)[::8]
    target=t[taps-1::8]-x[taps-1::8]
    gram=np.zeros((taps,taps)); rhs=np.zeros(taps); rows=0
    for start in range(0,len(w),4096):
        a=w[start:start+4096].reshape(-1,taps)[:,::-1].copy()
        b=target[start:start+4096].reshape(-1)
        gram+=a.T@a;rhs+=a.T@b;rows+=len(a)
    power=np.trace(gram)/(rows*taps)
    if power<1e-10 or np.mean(t*t)<1e-10: raise ValueError('silent enrollment')
    reg=power*rows*.12
    h=linalg.solve(gram+reg*np.eye(taps),rhs,assume_a='pos')*strength
    h*=min(1.,.35/max(np.sum(np.abs(h)),1e-12)); h[0]+=1
    return h


def render(source, coefficients):
    x=np.asarray(source,dtype=np.float64); h=np.asarray(coefficients,dtype=np.float64)
    if x.ndim!=2 or x.shape[1] not in (1,2) or not 0<len(x)<=1920000 or not np.isfinite(x).all() or np.max(np.abs(x))>4 or h.shape not in ((16,),(64,),(256,)) or not np.isfinite(h).all(): raise ValueError('invalid preview')
    residual=h.copy();residual[0]-=1
    if np.sum(np.abs(residual))>.35000001: raise ValueError('unsafe coefficients')
    return signal.lfilter(h,[1.],x,axis=0).astype(np.float32)


def _bands(x, rate, multiband):
    if not multiband: return x[:,None,:]
    lo=signal.sosfilt(signal.butter(2,550,fs=rate,output='sos'),x,axis=0)
    hi=signal.sosfilt(signal.butter(2,4500,fs=rate,output='sos'),x,axis=0)
    return np.stack((lo,hi-lo,x-hi),axis=1)


def _level(x,rate,ms):
    a=np.exp(-1/(rate*ms*.001));p=np.mean(x*x,axis=-1)
    return 10*np.log10(np.maximum(signal.lfilter([1-a],[1,-a],p,axis=0),1e-12))


def _controls(x,rate):
    fast=_level(x,rate,5);slow=_level(x,rate,80)
    return slow,np.clip(fast-slow,-18,18),_level(x,rate,20)


def fit_motion(source,reference,rate,multiband=False,cap=2.):
    x,t=map(lambda a:np.asarray(a,dtype=np.float64),(source,reference))
    if x.shape!=t.shape or x.ndim!=2 or x.shape[1] not in (1,2) or not 32000<=rate<=192000 or not rate<=len(x)<=min(60*rate,1920000) or not np.isfinite(x).all() or not np.isfinite(t).all() or np.max(np.abs(x))>4 or np.max(np.abs(t))>4 or cap not in (1.,2.,3.) or not isinstance(multiband,bool): raise ValueError('invalid aligned audio or budget')
    b=_bands(x,rate,multiband);z=_bands(t,rate,multiband);slow,onset,lev=_controls(b,rate);ref=_level(z,rate,20);p=[]
    for k in range(b.shape[1]):
        ix=np.arange(round(.1*rate),len(x),max(1,round(.01*rate)));a=slow[ix,k];c=onset[ix,k];d=ref[ix,k];v=lev[ix,k]
        ok=(v>-65)&(d>max(-65,np.percentile(d,90)-35))
        if ok.sum()<20:p.append([0.,0.,0.,-24.]);continue
        center=float(np.median(a[ok]));A=np.column_stack((np.ones(ok.sum()),np.clip(a[ok]-center,-18,18),c[ok]));y=np.clip(d[ok]-v[ok],-cap,cap)
        from scipy.optimize import lsq_linear
        h=lsq_linear(np.vstack((A,np.diag([4.,20.,20.]))),np.r_[y,0.,0.,0.],bounds=([-cap,-.25,-.25],[cap,.25,.25])).x
        p.append([*map(float,h),center])
    return {'multiband':multiband,'cap':cap,'coefficients':p}


def render_motion(source,rate,recipe):
    x=np.asarray(source,dtype=np.float64);mb=recipe['multiband'];cap=recipe['cap'];p=np.asarray(recipe['coefficients'],dtype=float)
    if x.ndim!=2 or x.shape[1] not in (1,2) or not 0<len(x)<=1920000 or not np.isfinite(x).all() or np.max(np.abs(x))>4 or not 32000<=rate<=192000 or not isinstance(mb,bool) or cap not in (1.,2.,3.) or p.shape!=((3 if mb else 1),4) or not np.isfinite(p).all() or np.any(abs(p[:,0])>cap+1e-8) or np.any(abs(p[:,1:3])>.25000001): raise ValueError('invalid motion recipe')
    b=_bands(x,rate,mb);slow,onset,_=_controls(b,rate);g=np.clip(p[:,0]+p[:,1]*np.clip(slow-p[:,3],-18,18)+p[:,2]*onset,-cap,cap)
    a=np.exp(-1/(.012*rate));g=signal.lfilter([1-a],[1,-a],g,axis=0)
    return (x+np.sum(b*(10**(g[:,:,None]/20)-1),axis=1)).astype(np.float32)


def metrics(candidate,reference,rate):
    """Composite offline distance. Lower is better; not similarity percent."""
    def db(x):return 20*np.log10(np.maximum(x,1e-9))
    def rms(x):return np.sqrt(np.mean(x*x,dtype=np.float64))
    def features(x):
        x=np.asarray(x,dtype=np.float64)
        if x.shape[1]==1:x=np.repeat(x,2,axis=1)
        n=2048;z=x[:len(x)//n*n].reshape(-1,n,2);p=np.mean(abs(np.fft.rfft(z*np.hanning(n)[None,:,None],axis=1))**2,axis=0);hz=np.fft.rfftfreq(n,1/rate)
        edges=[45,100,180,320,560,1000,1800,3200,5600,10000,min(18000,rate/2)]
        tone=[10*np.log10(max(np.mean(p[(hz>=a)&(hz<b)]) if np.any((hz>=a)&(hz<b)) else 0,1e-12)) for a,b in zip(edges[:-1],edges[1:])]
        n=round(.02*rate);v=x[:len(x)//n*n].reshape(-1,n,2);env=db(np.sqrt(np.mean(v*v,axis=(1,2))))
        mid=x.mean(1);side=(x[:,0]-x[:,1])*.5
        norm=np.sqrt(np.dot(x[:,0],x[:,0])*np.dot(x[:,1],x[:,1]));corr=np.dot(x[:,0],x[:,1])/max(norm,1e-12)
        return np.asarray(tone),env,float(db(rms(side)/max(rms(mid),1e-9))),float(corr)
    x,t=map(np.asarray,(candidate,reference));a,e,s,c=features(x);b,f,r,d=features(t);active=f>max(np.percentile(f,90)-45,-75)
    tone=float(np.mean(abs(a-b)));env=float(np.mean(abs(e[active]-f[active]))) if active.any() else float(np.mean(abs(e-f)));wave=float(rms(x-t)/max(rms(t),1e-9));side=abs(s-r);corr=abs(c-d);level=float(abs(db(rms(x)/max(rms(t),1e-9))))
    return dict(score=tone+.4*env+.65*wave+.18*min(side,30)+1.5*corr,tone=tone,env=env,wave=wave,side=side,corr=corr,level=level)


def passes(m,b,fraction):
    return m['score']<b['score']*(1-fraction) and m['env']<=b['env']+.30 and m['wave']<=b['wave']+.06 and m['side']<=b['side']+.7 and m['corr']<=b['corr']+.04 and m['tone']<=b['tone']+.2 and m['level']<=max(b['level']+.3,1.5)


def estimated_peak(x):
    return float(20*np.log10(max(1e-12,np.max(np.abs(signal.resample_poly(x,4,1,axis=0))))))


def preview(source,reference,rate,*,pair_confirmed=False):
    """Fit first 45%, select next 25%, measure last 30%; return report, optional render.
    Pair confirmation is an explicit caller assertion, never inferred from similarity.
    No audio or parameter changes outside the returned preview.
    """
    x,t=map(lambda a:np.asarray(a,dtype=np.float32),(source,reference))
    if pair_confirmed is not True or not np.isfinite(rate) or int(rate)!=rate or not 32000<=rate<=192000 or x.shape!=t.shape or x.ndim!=2 or x.shape[1] not in (1,2) or not 5*rate<=len(x)<=min(60*rate,1920000) or not np.isfinite(x).all() or not np.isfinite(t).all() or max(np.max(abs(x)),np.max(abs(t)))>4:
        raise ValueError('explicit same-take stage confirmation and aligned finite 5–60s audio required')
    rate=int(rate);a=int(.45*len(x));b=int(.70*len(x));windows=(slice(0,a),slice(a,b),slice(b,None))
    if any(np.mean(v[w]**2)<1e-10 for v in (x,t) for w in windows):raise ValueError('silent evaluation window')
    gain=float(np.clip(np.sqrt(np.mean(t[:a]**2)/np.mean(x[:a]**2)),.5,2))
    bases=[min((metrics(x[w],t[w],rate),metrics(x[w]*gain,t[w],rate)),key=lambda m:m['score']) for w in windows]
    trials=[]
    for taps in (16,64,256):
        for strength in (.25,.5,1.):
            h=fit(x[:a],t[:a],rate,taps,strength);trials.append(('fir',h.tolist()))
    for mb in (False,True):
        for cap in (1.,2.,3.):trials.append(('motion',fit_motion(x[:a],t[:a],rate,mb,cap)))
    def apply(z,kind,r):return render(z,r) if kind=='fir' else render_motion(z,rate,r)
    records=[]
    for kind,r in trials:
        y=apply(x[:b],kind,r);m=[metrics(y[w],t[w],rate) for w in windows[:2]]
        records.append(dict(kind=kind,recipe=r,train=m[0],validation=m[1],eligible=bool(passes(m[0],bases[0],.01) and passes(m[1],bases[1],.02))))
    report=dict(status='NO_IMPROVEMENT',baseline=bases,training_gain=gain,trial_count=len(records),trials=records)
    valid=[r for r in records if r['eligible']]
    if not valid:return report,None
    selected=min(valid,key=lambda r:r['validation']['score']);y=apply(x,selected['kind'],selected['recipe']);m=metrics(y[b:],t[b:],rate);pk=estimated_peak(y)
    report.update(selected=selected,final=m,estimated_dbtp=pk)
    if not passes(m,bases[2],.05) or pk>-1 or not np.isfinite(y).all():return report,None
    report['status']='AUDITION_ONLY';return report,y


def preview_files(source_path,reference_path,output_dir,*,source_sha256,reference_sha256,take,stage,pair_confirmed=False):
    """Explicit private export; never writes over a prior directory or preset."""
    from pathlib import Path
    import hashlib,json
    import soundfile as sf
    paths=[Path(source_path),Path(reference_path)];hashes=[source_sha256,reference_sha256]
    if pair_confirmed is not True or not isinstance(take,str) or not take.strip() or not isinstance(stage,str) or not stage.strip():raise ValueError('explicit confirmed take/stage required')
    def sha(p):
        with p.open('rb') as f:
            digest=hashlib.sha256()
            for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
        return digest.hexdigest()
    if any(not isinstance(h,str) or len(h)!=64 or sha(p)!=h for p,h in zip(paths,hashes)):raise ValueError('source/reference hash mismatch')
    for p in paths:
        info=sf.info(p)
        if info.channels not in (1,2) or not 32000<=info.samplerate<=192000 or not 5*info.samplerate<=info.frames<=min(60*info.samplerate,1920000):raise ValueError('unsupported clip geometry')
    out=Path(output_dir)
    if out.exists():raise FileExistsError(out)
    x,s=sf.read(paths[0],dtype='float32',always_2d=True);t,sr=sf.read(paths[1],dtype='float32',always_2d=True)
    if sr!=s or any(sha(p)!=h for p,h in zip(paths,hashes)):raise ValueError('changed input or different rate')
    report,y=preview(x,t,s,pair_confirmed=True)
    report.update(source_sha256=source_sha256,reference_sha256=reference_sha256,take=take,stage=stage,pair_confirmation='caller-asserted; not inferred',sample_rate=s,frames=len(x))
    # Verify exact quantized audition data before creating any output file.
    if y is not None:
        import io
        buf=io.BytesIO();sf.write(buf,y,s,format='FLAC',subtype='PCM_24');raw=buf.getvalue();z,zsr=sf.read(io.BytesIO(raw),dtype='float32',always_2d=True);b=int(.70*len(t));m=metrics(z[b:],t[b:],s);pk=estimated_peak(z)
        if zsr!=s or z.shape!=x.shape or not passes(m,report['baseline'][2],.05) or pk>-1:
            report['status']='EXPORT_REJECTED';y=None
        else:report.update(export_final=m,export_estimated_dbtp=pk,export_sha256=hashlib.sha256(raw).hexdigest())
    out.mkdir(parents=True,exist_ok=False)
    if y is not None:(out/'AUDITION_ONLY.flac').write_bytes(raw)
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    return report


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('reference');p.add_argument('output_dir')
    p.add_argument('--source-sha256',required=True);p.add_argument('--reference-sha256',required=True)
    p.add_argument('--take',required=True);p.add_argument('--stage',required=True);p.add_argument('--confirm-aligned',action='store_true')
    a=p.parse_args();r=preview_files(a.source,a.reference,a.output_dir,source_sha256=a.source_sha256,reference_sha256=a.reference_sha256,take=a.take,stage=a.stage,pair_confirmed=a.confirm_aligned);print(r['status'])
