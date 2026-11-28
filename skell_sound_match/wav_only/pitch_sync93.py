"""Independent pitch-synchronous source/filter research via optional Praat. No target at replay."""
import numpy as np
import parselmouth as pm
from parselmouth.praat import call

def pitch_transform(x,sr,pitch_ratio,formant_ratio,range_ratio=1.):
    if not 0.35<=pitch_ratio<=2 or not .35<=formant_ratio<=2 or not .5<=range_ratio<=1.5:raise ValueError('invalid pitch/formant ratio')
    x=np.asarray(x,dtype=np.float32)
    if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.isfinite(x).all():raise ValueError('invalid stereo input')
    if np.max(abs(x))<1e-7:return np.zeros_like(x)
    # Preserve stereo differences outside the shared pitch core, to be modeled separately.
    u=pm.Sound(x.mean(1).astype(float),sampling_frequency=sr);p=u.to_pitch(time_step=.005,pitch_floor=60,pitch_ceiling=600);median=call(p,'Get quantile',0,0,.5,'Hertz')
    if not np.isfinite(median):return x.copy()
    # Praat RNG is global; use only in this isolated offline research process.
    pm.praat.run("random_initializeWithSeedUnsafelyButPredictably (9301)")
    try:
        v=call([u,p],'Change gender',float(formant_ratio),float(median*pitch_ratio),float(range_ratio),1.)
    finally:
        pm.praat.run("random_initializeSafelyAndUnpredictably ()")
    z=np.zeros(len(x),dtype='f');n=min(len(z),v.values.shape[1]);z[:n]=v.values[0,:n];return np.repeat(z[:,None],2,axis=1)
