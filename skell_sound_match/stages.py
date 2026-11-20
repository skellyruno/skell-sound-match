"""Read-only frequency- and source-conditioned measurements for two serial vocal chains."""
from __future__ import annotations
import numpy as np
from scipy import signal
from .core import Audio

BANDS=((80,250,"body"),(250,800,"low_mid"),(800,2200,"mid"),
       (2200,5000,"presence"),(5000,11000,"consonants"))

def _check(*clips: Audio):
    if len(clips)!=4:
        raise ValueError("Expected dry, recording-only, main-only, and combined clips")
    shape,sr=clips[0].samples.shape,clips[0].rate
    if len(shape)!=2 or shape[1] not in (1,2) or shape[0]<sr:
        raise ValueError("Inputs must contain at least 1 second of mono/stereo audio")
    if not 16000<=sr<=192000:
        raise ValueError("Unsupported sample rate")
    for audio in clips:
        if audio.rate!=sr or audio.samples.shape!=shape:
            raise ValueError("All four renders must be sample-aligned with identical rate and channels")
        if not np.isfinite(audio.samples).all():
            raise ValueError("Non-finite audio detected")

def _frame_db(x, sr, frame_ms=20):
    width=max(1,round(sr*frame_ms/1000))
    frames=len(x)//width
    z=x[:frames*width].reshape(frames,width)
    return 20*np.log10(np.sqrt(np.mean(z*z,axis=1))+1e-10)

def _transfer(inp,out,sr,window):
    x,y=inp[window],out[window]
    full=_frame_db(x,sr)
    activity=full>max(-55,np.max(full)-36)
    if activity.sum()<12:
        raise ValueError("Too few active frames in analysis window")
    vals={}
    for lo,hi,name in BANDS:
        high=min(hi,sr*.47)
        if lo>=high:
            continue
        sos=signal.butter(3,[lo,high],btype="bandpass",fs=sr,output="sos")
        xi,yi=_frame_db(signal.sosfilt(sos,x),sr),_frame_db(signal.sosfilt(sos,y),sr)
        mask=activity & (xi>max(-75,np.max(xi)-50))
        if mask.sum()<8:
            continue
        ratios=yi[mask]-xi[mask]
        vals[name]={"median_gain_db":round(float(np.median(ratios)),3),
                    "gain_spread_p90_p10_db":round(float(np.percentile(ratios,90)-np.percentile(ratios,10)),3),
                    "active_frames":int(mask.sum())}
    return vals

def _window(n,sr,bounds):
    if bounds[0]<0 or bounds[1]<=bounds[0] or bounds[1]>n/sr:
        raise ValueError("Invalid stage-analysis window")
    return slice(round(bounds[0]*sr),round(bounds[1]*sr))

def analyze_stages(dry: Audio, recording: Audio, main: Audio, combined: Audio,
                   windows: dict[str,tuple[float,float]]|None=None)->dict:
    """All files must come from exactly the same take and start time. Never edits audio."""
    _check(dry,recording,main,combined)
    sr=dry.rate
    windows=windows or {"early":(.5,min(6.5,len(dry.samples)/sr))}
    if not windows:
        raise ValueError("Provide at least one window")
    # Channel-aware inputs; use mid for diagnostic comparison, not stereo scoring.
    clips=[a.samples.mean(axis=1) for a in (dry,recording,main,combined)]
    results={}
    for label,bounds in windows.items():
        w=_window(len(clips[0]),sr,bounds)
        rec=_transfer(clips[0],clips[1],sr,w)
        direct=_transfer(clips[0],clips[2],sr,w)
        after=_transfer(clips[1],clips[3],sr,w)
        delta={band:round(after[band]["median_gain_db"]-direct[band]["median_gain_db"],3)
               for band in direct.keys()&after.keys()}
        results[label]={"recording_stage":rec,"main_on_dry":direct,
                        "main_after_recording":after,"main_input_condition_delta_db":delta}
    return {"sample_rate":sr,"channels":dry.samples.shape[1],"frames":len(dry.samples),
            "window_metrics":results,
            "interpretation":"Measured stage transfer, NOT original plugin settings; no audio modified."}
