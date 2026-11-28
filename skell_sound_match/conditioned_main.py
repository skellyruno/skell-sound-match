"""Independent main-vocal matching conditioned on coarse periodicity groups.
No phoneme recognition, source preset, or reference waveform in rendering.
"""
from dataclasses import replace
from math import gcd
import numpy as np
from scipy import signal
from .reference_transfer import _audio, Recipe, Prepared, profile, distance, BANDS


def frames(x,rate):
    x=_audio(x,rate)
    if rate!=44100:
        g=gcd(int(rate),44100);x=signal.resample_poly(x,44100//g,int(rate)//g,axis=0)
    n=2048
    f=x[:len(x)//n*n].reshape(-1,n,2)
    p=np.mean(f*f,axis=(1,2),dtype=np.float64)
    return f,p


def labels(x,rate):
    f,p=frames(x,rate)
    active=p>max(float(p.max())*1e-4,1e-12)
    w=np.hanning(2048);m=f.mean(2);m=(m-m.mean(1,keepdims=True))*w
    a=np.fft.irfft(abs(np.fft.rfft(m,n=4096,axis=1))**2,axis=1)
    wa=np.fft.irfft(abs(np.fft.rfft(w,n=4096))**2)
    r=a[:,98:552]/np.maximum(a[:,:1],1e-15)*wa[0]/wa[None,98:552]
    voiced=np.max(r,axis=1)>.55
    out=np.full(len(p),-1,dtype=np.int8);out[active]=voiced[active].astype(np.int8)
    return out


def conditional(x,rate,mask=None):
    f,p=frames(x,rate)
    if mask is None:mask=labels(x,rate)
    if len(mask)!=len(f):raise ValueError('frame mask geometry differs')
    rows={};counts={};hz=np.fft.rfftfreq(2048,1/44100)
    for k in (0,1):
        a=np.flatnonzero(mask==k);counts[k]=len(a)
        if len(a)<8:continue
        a=a[np.linspace(0,len(a)-1,min(96,len(a)),dtype=int)]
        spec=abs(np.fft.rfft(f[a]*np.hanning(2048)[None,:,None],axis=1))**2
        b=np.stack([spec[:,(hz>=l)&(hz<h),:].sum((1,2)) for l,h in zip(BANDS,BANDS[1:])],axis=1)
        shape=10*np.log10(np.maximum(b/np.maximum(b.sum(1,keepdims=True),1e-15),1e-7))
        rows[k]=np.percentile(shape,[25,50,75],axis=0)
    return rows,counts


def compare(x,rate,target,target_groups,mask=None):
    d=distance(profile(x,rate),target);rows,counts=conditional(x,rate,mask)
    common=sorted(set(rows)&set(target_groups))
    if not common:raise ValueError('no shared periodicity group')
    d['conditioned_db']=float(np.mean([np.mean(abs(rows[k]-target_groups[k])) for k in common]))
    d['groups']=len(common);d['main_score']=.6*d['tone_db']+.6*d['conditioned_db']+.5*d['dynamics_db']+.1*d['width_db']
    return d


def fit(sources,reference,ref_rate):
    """Two or more source performances; no inferred echo or reverb in this fit."""
    if len(sources)<2:raise ValueError('need two source performances')
    p=profile(reference,ref_rate);g,_=conditional(reference,ref_rate)
    bases=[(Prepared(x,sr),labels(x,sr)) for x,sr in sources]
    def assess(r):return [compare(b.render(r),b.rate,p,g,m) for b,m in bases]
    def score(rows):
        a=[r['main_score'] for r in rows];return .75*np.mean(a)+.25*max(a)
    r=Recipe();base=assess(r);best=score(base);count=1
    grids={'low':[-12,-6,0,6,12],'body':[-12,-6,0,6,12],'presence':[-12,-6,0,6,12],
           'air':[-12,-6,0,6,12],'compression':[0,.25,.5,.75],'gate':[0,.25,.5]}
    for _ in range(2):
        for key,vals in grids.items():
            for v in vals:
                q=replace(r,**{key:float(v)});count+=1
                try:rr=assess(q)
                except ValueError:continue
                if any(a['dynamics_db']>b['dynamics_db']+.5 or a['conditioned_db']>b['conditioned_db']+.25 for a,b in zip(rr,base)):continue
                if score(rr)<best-1e-7:r,best=q,score(rr)
    level=np.median([profile(b.render(r),b.rate)['level'] for b,_ in bases]);r=replace(r,gain_db=float(np.clip(p['level']-level,-36,36)))
    return r,{'evaluations':count,'before':base,'after':assess(r),'reference_groups':len(g)}
