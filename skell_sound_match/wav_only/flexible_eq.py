"""Fit editable Studio Parametric EQ controls, using exact causal response.
Only earlier-region spectra influence controls; no target waveform in replay.
"""
import numpy as np
from scipy import signal, optimize

# Exact StudioNativeDSP ParametricEQ law: 0 bell, 1 HP, 2 LP, 3 low shelf, 4 high shelf.
def response(f,sr,params,widths,kinds):
    f=np.asarray(f,float); z=np.exp(-2j*np.pi*f/sr);z2=z*z;h=np.ones(len(f),complex)
    for (fn,gn),width,kind in zip(np.asarray(params).reshape(-1,2),widths,kinds):
        freq=np.clip(20.*1000.**fn,20.,sr*.46);gain=36.*(gn-.5);w=min(freq*2*np.pi/sr,2.1991147994995117 if kind==0 else 3.138451099395752);sn,cs=np.sin(w),np.cos(w);A=10**(gain/40)
        if kind in [1,2]:
            q=.35*12**width;a=sn/(2*q);b=np.array([(1+cs)/2,-(1+cs),(1+cs)/2]) if kind==1 else np.array([(1-cs)/2,1-cs,(1-cs)/2]);den=np.array([1+a,-2*cs,1-a])
        elif kind==0:
            a=sn*np.sinh(np.log(2)*.5*(width*4.9+.1)*w/max(sn,1e-6));b=np.array([1+a*A,-2*cs,1-a*A]);den=np.array([1+a/A,-2*cs,1-a/A])
        else:
            slope=(1-width)*1.7192982456140353+1/3;beta=np.sqrt(A)*np.sqrt(max(0.,(A+1/A)*(1/slope-1)+2))*sn;d=(A-1)*cs
            if kind==3:
                den=np.array([A+1+d+beta,-2*((A-1)+(A+1)*cs),A+1+d-beta]);b=A*np.array([A+1-d+beta,2*((A-1)-(A+1)*cs),A+1-d-beta])
            else:
                den=np.array([A+1-d+beta,2*((A-1)-(A+1)*cs),A+1-d-beta]);b=A*np.array([A+1+d+beta,-2*((A-1)+(A+1)*cs),A+1+d+beta])
        h*=(b[0]+b[1]*z+b[2]*z2)/(den[0]+den[1]*z+den[2]*z2)
    return h

def fit_studio_eq(x,t,sr=44100,topology='shelves',phase_weight=.3,max_nfev=30):
    x=np.asarray(x,dtype=float);t=np.asarray(t,dtype=float)
    if x.shape!=t.shape or x.ndim!=2 or x.shape[1]!=2 or len(x)<4096 or not np.isfinite(x).all() or not np.isfinite(t).all() or not 32000<=sr<=192000:raise ValueError('invalid paired audio')
    f,p=signal.welch(x,sr,nperseg=2048,axis=0);_,q=signal.welch(t,sr,nperseg=2048,axis=0);_,cross=signal.csd(x,t,sr,nperseg=2048,axis=0);p=p.sum(1);q=q.sum(1);cross=cross.sum(1);m=(f>=70)&(f<min(18000,sr*.45));f,p,q,cross=f[m],p[m],q[m],cross[m]
    if p.sum()<1e-12 or q.sum()<1e-12:raise ValueError('silent spectral input')
    floor=max(q.sum()*1e-7,1e-16);edges=[70,150,300,600,1200,2400,4800,9600,18000];M=np.array([(f>=l)&(f<h) for l,h in zip(edges[:-1],edges[1:])],float);wanted=M@q
    coherence=np.clip(abs(cross)**2/np.maximum(p*q,1e-30),0,1);norm=np.sqrt(np.maximum(p*q,floor**2));wt=np.sqrt(coherence)*np.sqrt(q/max(q.max(),1e-30));wt/=max(np.sqrt(np.mean(wt*wt)),1e-8)
    kinds=[3,0,0,0,0,4] if topology=='shelves' else [1,0,0,0,0,2]
    centers=np.array([100,260,650,1500,4200,10500]);center=np.log(centers/20)/np.log(1000);lo=np.maximum(0,center-.14);hi=np.minimum(1,center+.14)
    if topology=='cuts':lo[0]=0;hi[0]=np.log(400/20)/np.log(1000);lo[-1]=np.log(1800/20)/np.log(1000);hi[-1]=1
    n=len(kinds);init=np.r_[center,[.5]*n,[.35]*n,np.clip(20*np.log10(np.sqrt(q.sum()/p.sum())),-12,12)]
    lower=np.r_[lo,[.08]*n,[0.]*n,-18.];upper=np.r_[hi,[.92]*n,[1.]*n,18.]
    def model(v):return response(f,sr,np.column_stack((v[:n],v[n:2*n])).ravel(),v[2*n:3*n],kinds)*10**(v[-1]/20)
    def err(v):
        h=model(v);en=10*np.log10((M@(p*abs(h)**2)+floor)/(wanted+floor));e=wt*(h*p-cross)/norm
        return np.r_[en,2*(v[n:2*n]-.5),.35*(v[:n]-center),phase_weight*e.real,phase_weight*e.imag,.03*v[-1]]
    v=optimize.least_squares(err,init,bounds=(lower,upper),max_nfev=max_nfev,ftol=1e-4,xtol=1e-4).x
    return {'params':np.column_stack((v[:n],v[n:2*n])).ravel().tolist()+[.5]*4,'q':v[2*n:3*n].tolist()+[.5]*2,'kinds':kinds+[0,0],'enabled':[True]*n+[False,False],'gain':float(v[-1]),'training_error':float(np.mean(abs(err(v)[:8])))}
