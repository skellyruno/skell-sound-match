"""Explicit offline latency ownership. Do not compensate an already aligned bridge twice."""
import numpy as np

def render_bridge(source, render, *, mode, max_latency):
    x=np.asarray(source,dtype=np.float32)
    if x.ndim!=2 or x.shape[1]!=2 or not 1<=len(x)<=12000000 or not np.isfinite(x).all():
        raise ValueError('bounded finite stereo source required')
    if mode not in ('raw','aligned') or type(max_latency) is not int or not 0<=max_latency<=192000:
        raise ValueError('explicit latency contract required')
    inp=np.pad(x,((0,max_latency),(0,0))) if mode=='raw' else np.array(x,copy=True,order='C')
    audio,latency=render(inp)
    y=np.asarray(audio,dtype=np.float32)
    if type(latency) is not int or not 0<=latency<=max_latency or y.shape!=inp.shape or not np.isfinite(y).all():
        raise ValueError('bridge violated latency or geometry contract')
    start=latency if mode=='raw' else 0
    return np.ascontiguousarray(y[start:start+len(x)]).copy(),latency
