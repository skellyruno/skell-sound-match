"""Bounded convex spectral branch fusion, fitted on prefix only."""
import numpy as np
from scipy import optimize
from . import context_energy86 as c

def fit(Z,T,st,stop,reg):
    ix=np.arange(Z.shape[1])*c.H;mask=(ix>=st+c.N)&(ix<stop-c.N)
    if mask.sum()<8:raise ValueError('insufficient guarded train frames')
    # Z[0] is protected anchor; all others are deterministic dry-input models.
    K=Z.shape[0]-1;W=np.zeros((2,c.NB,K),'f')
    for j in range(2):
        for k in range(c.NB):
            b=c.BAND==k
            if not b.any():continue
            anchor=Z[0,mask,j,:][:,b].reshape(-1);A=(Z[1:,mask,j,:][:,:,b].reshape(K,-1)-anchor).T;v=T[mask,j,:][:,b].reshape(-1)-anchor
            G=(A.conj().T@A).real;R=(A.conj().T@v).real;pen=max(float(np.trace(G))/K,1e-8)*reg;G+=pen*np.eye(K)
            f=lambda w: .5*w@G@w-R@w;g=lambda w:G@w-R
            sol=optimize.minimize(f,np.zeros(K),jac=g,bounds=[(0,1)]*K,constraints=[{'type':'ineq','fun':lambda w:1-w.sum(),'jac':lambda w:-np.ones(K)}],method='SLSQP',options={'maxiter':50,'ftol':1e-9})
            W[j,k]=sol.x if sol.success else 0
    return W

def apply(Z,W,n,amount=1.):
    if not 0<=amount<=1:raise ValueError('invalid amount')
    i=np.clip(np.searchsorted(c.CENTERS,c.FREQ)-1,0,c.NB-2);f=np.clip((np.log(np.maximum(c.FREQ,1))-np.log(c.CENTERS[i]))/(np.log(c.CENTERS[i+1])-np.log(c.CENTERS[i])),0,1).astype('f');w=(W[:,i,:]*(1-f)[None,:,None]+W[:,i+1,:]*f[None,:,None])*amount
    z=Z[0].copy()
    for k in range(len(Z)-1):z+=(Z[k+1]-Z[0])*w[:,:,k][None,:,:]
    return c.synth(z,n)
