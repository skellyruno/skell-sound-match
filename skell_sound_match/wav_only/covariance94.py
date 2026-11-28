"""Offline regularized stereo covariance transport with complementary FIR bands.
No reference at replay. Centered filtering is not realtime DSP.
"""
import numpy as np
from scipy import signal
SR=44100
N=1025
EDGES=np.array([70,150,300,600,1200,2400,4800,9600,18000])
F=np.linspace(0,SR/2,(N+1)//2)
B=np.zeros((len(F),8));B[:,0]=1
for k,e in enumerate(EDGES[1:-1],1):
    v=np.clip((F-e*.75)/(e*.5),0,1);v=v*v*(3-2*v);B[:,k-1]-=v;B[:,k]+=v
FILTERS=np.stack([signal.firwin2(N,F,B[:,k],fs=SR).astype('f') for k in range(8)])
def ms(x):return np.stack([x.mean(-1),(x[...,0]-x[...,1])*.5],axis=-1).astype('f')
def lr(x):return np.stack([x[...,0]+x[...,1],x[...,0]-x[...,1]],axis=-1).astype('f')
def bands(x):
    v=ms(x);return np.stack([signal.oaconvolve(v,h[:,None],mode='same',axes=0) for h in FILTERS],axis=2).astype('f')

def _root(a,power):
    d,v=np.linalg.eigh(a);d=np.maximum(d,max(float(d.max())*1e-5,1e-12));return (v*d**power)@v.T

def fit(A,T,start,stop,reg=.1,mode=0):
    if not (0<=start<stop<=len(A)) or stop-start<4096 or reg<0:raise ValueError('invalid fit interval')
    a=A[start+512:stop-512];b=T[start+512:stop-512];out=[]
    for k in range(A.shape[2]):
        x=a[:,:,k].astype('d');y=b[:,:,k].astype('d');X=x.T@x/len(x);Y=y.T@y/len(y);floor=max(np.trace(X+Y)*.0001,1e-12)
        X+=floor*np.eye(2);Y+=floor*np.eye(2)
        if mode==0:
            M=np.diag(np.sqrt(np.diag(Y)/np.diag(X)))
        elif mode==1:
            u=_root(X,.5);v=_root(X,-.5);M=v@_root(u@Y@u,.5)@v
        elif mode==2:
            u=_root(X,.5);v=_root(X,-.5);q=_root(Y,.5);cross=q@(y.T@x/len(x))@v
            l,_,r=np.linalg.svd(cross);M=q@l@r@v
        else:raise ValueError('invalid mode')
        u,s,v=np.linalg.svd(M);M=(u*np.clip(s,.35,3.0))@v
        out.append((M+reg*np.eye(2))/(1+reg))
    return np.asarray(out,dtype='f')

def apply(A,M,amount=1.):
    if not 0<=amount<=1:raise ValueError('invalid amount')
    v=np.einsum('kij,tjk->ti',M,A,optimize=True);return lr((1-amount)*A.sum(2)+amount*v)
