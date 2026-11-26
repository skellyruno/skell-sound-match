"""Explicit opt-in offline adapter for locally built, trusted private research engines.
No plugin binaries, recordings or fitted states are shipped by Sound Match.
"""
import ctypes as C
import hashlib
from pathlib import Path
import sys
import numpy as np

F=C.POINTER(C.c_float); I=C.c_int; D=C.c_double
ABI={
    'doubler':('gemini','render_dub',[F,I]),
    'rverb':('reverb','render_verb',[D,D,I]),
    'waves_eq':('facet','render_eq',[I,D,D,D]),
    'facet_eq':('facet','render_facet',[F,I]),
    'c6':('c6','render_c6_full',[F,F,F,D,I,I]),
    'wet_return':('return','render_return',[F,F,D,D,D,D,D,D,I]),
}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def _array(value,shape):
    a=np.ascontiguousarray(value,dtype=np.float32)
    if a.shape!=shape or not np.isfinite(a).all():raise ValueError('invalid recipe shape or values')
    return a

def _audio(audio):
    a=np.asarray(audio,dtype=np.float32)
    if a.ndim!=2 or a.shape[1]!=2 or not 1<=len(a)<=1920000 or not np.isfinite(a).all() or np.max(abs(a))>4:raise ValueError('bounded finite stereo excerpt required')
    return np.ascontiguousarray(a.T).copy()

class PrivateVocalStudy:
    """Only load binaries you built and trust; hashes bind identity, not safety."""
    def __init__(self,root,hashes,*,trusted_local_build=False):
        if trusted_local_build is not True:raise ValueError('explicit trusted local build required')
        self.root=Path(root).resolve();self.functions={};self.libraries={};self.hashes=dict(hashes)
        self.suffix='.dll' if sys.platform=='win32' else '.dylib' if sys.platform=='darwin' else '.so'

    def _fn(self,name):
        stem,symbol,types=ABI[name];filename='skv_'+stem+self.suffix
        if name not in self.functions:
            p=(self.root/filename).resolve()
            if p.parent!=self.root or not p.is_file() or digest(p)!=self.hashes.get(filename):raise ValueError('missing or mismatched trusted adapter')
            if stem not in self.libraries:self.libraries[stem]=C.CDLL(str(p))
            f=getattr(self.libraries[stem],symbol);f.argtypes=[F,F,I,I,*types];f.restype=I;self.functions[name]=f
        return self.functions[name]

    def render(self,name,audio,rate,recipe,*,block=512,key=None):
        """Return (new stereo audio, declared latency). Never changes the input."""
        if name not in ABI or type(rate)!=int or not 32000<=rate<=192000 or type(block)!=int or not 1<=block<=4096:raise ValueError('unsupported adapter or render geometry')
        x=_audio(audio);n=x.shape[1];ptr=lambda a:a.ctypes.data_as(F);r=recipe;lat=0
        if name=='doubler':
            p=_array(r,(57,))
            if np.any(p<0) or np.any(p>1) or any(p[13+10*k+4]>.85 for k in range(4)):raise ValueError('unsafe normalized doubler recipe')
            args=[ptr(p),block]
        elif name=='rverb':
            args=[float(r['decay_s']),float(r['predelay_ms']),block]
        elif name=='waves_eq':
            args=[int(r['code']),float(r['hz']),float(r['gain_db']),float(r['q'])]
            if args[0]!=r['code']:raise ValueError('invalid code')
        elif name=='facet_eq':
            a=np.asarray(r,dtype=np.float32)
            if a.ndim!=2 or not 1<=len(a)<=8:raise ValueError('invalid static bands')
            p=_array(a,(len(a),5));args=[ptr(p),len(p)]
        elif name=='c6':
            cross=_array(r['crossovers'],(3,));fixed=_array(r['fixed'],(4,8));floating=_array(r['floating'],(2,8))
            if type(r['opto'])!=bool:raise ValueError('invalid C6 mode')
            args=[ptr(cross),ptr(fixed),ptr(floating),float(r['q']),int(r['opto']),block]
        else:
            if type(r['duck'])!=bool:raise ValueError('invalid duck mode')
            if key is None and r['duck']:raise ValueError('explicit detector key required')
            k=np.zeros_like(x) if key is None else _audio(key)
            if k.shape!=x.shape:raise ValueError('key geometry mismatch')
            args=[ptr(k[0]),ptr(k[1]),*[float(r[v]) for v in ('threshold_db','ratio','attack_ms','release_ms','range_db','return_db')],int(r['duck'])]
        ret=self._fn(name)(ptr(x[0]),ptr(x[1]),n,rate,*args)
        if ret<=0 or not np.isfinite(x).all() or np.max(abs(x))>16:raise ValueError('native render rejected or unsafe output')
        if name=='c6':lat=ret
        return x.T.copy(),lat
