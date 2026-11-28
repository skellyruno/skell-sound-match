"""Offline cross-band, multi-timescale log-power prediction. No reference at replay."""
import numpy as np
from scipy import ndimage
from . import context_energy86 as c

def design(p,q,mode):
    log=lambda v: np.clip(.5*np.log(np.maximum(v,1e-8)),-9,9)
    d=p.sum(1); u=q.sum(1); a=log(d); b=log(u)
    parts=[a,b,log(q[:,0]),log(q[:,1]),log(d.sum(1))[:,None],log(u.sum(1))[:,None]]
    if mode:
        for ms in (30,120,450,1000):
            parts += [log(c.smooth(d,ms)),log(c.smooth(u,ms))]
        for ms in (90,220,435,870):
            lag=round(ms*.001*c.SR/c.H)
            parts.append(np.pad(a,((lag,0),(0,0)),constant_values=-9)[:len(a)])
    return np.column_stack(parts).astype('f')

def fit(p,q,r,st,stop,reg,mode,objective):
    A=design(p,q,mode);ix=np.arange(len(A))*c.H;mask=(ix>=st+c.N)&(ix<stop-c.N)
    if mask.sum()<30:raise ValueError('not enough train frames')
    raw=A[mask];mu=raw.mean(0);sd=np.maximum(raw.std(0),.75);X=np.clip((raw-mu)/sd,-4,4);X=np.column_stack([np.ones(len(X)),X]);a=q[mask];b=r[mask];floor=np.maximum(b.mean(0)*1e-4,1e-8)
    target=np.clip(.5*np.log((b+floor)/(a+floor)),-2.5,2.5) if objective==0 else .5*np.log(b+floor)
    w=np.clip(np.sqrt(b/(b+floor*25)),.04,1);coef=[]
    for j in range(2):
        for k in range(c.NB):
            ww=w[:,j,k];G=X.T@(X*ww[:,None]);pen=np.maximum(np.diag(G),1)*reg;pen[0]=.001
            coef.append(np.linalg.solve(G+np.diag(pen),X.T@(target[:,j,k]*ww)))
    return dict(mu=mu,sd=sd,coef=np.array(coef,dtype='f').reshape(2,c.NB,-1),mode=mode,objective=objective,floor=floor.astype('f'))

def apply(x,y,p,amt,prepared=None):
    if not amt:return y.copy()
    P,Q,Z=prepared if prepared is not None else prepare(x,y)
    A=np.clip((design(P,Q,int(p['mode']))-p['mu'])/p['sd'],-4,4)
    g=np.einsum('fi,cbi->fcb',A,p['coef'][:,:,1:])+p['coef'][:,:,0]
    if int(p['objective']):g-=.5*np.log(Q+p['floor'])
    g=np.exp(ndimage.gaussian_filter1d(np.clip(g*amt,-2,2),1.5,axis=0));i=np.clip(np.searchsorted(c.CENTERS,c.FREQ)-1,0,c.NB-2);w=np.clip((np.log(np.maximum(c.FREQ,1))-np.log(c.CENTERS[i]))/(np.log(c.CENTERS[i+1])-np.log(c.CENTERS[i])),0,1).astype('f');z=Z.copy()
    for j in range(2):z[:,j,:]*=g[:,j,i]*(1-w)+g[:,j,i+1]*w
    return c.synth(z,len(y))

def prepare(x,y):
    z=c.spec(y);return c.power(c.spec(x)),c.power(z),z
