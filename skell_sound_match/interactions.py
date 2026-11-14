"""Measure level- and attack-conditioned response of the main FX stage.
Input: four sample-aligned WAVs (dry, record-only, main-only, full).
No attempt is made to decode proprietary DSP or modify an input recording.
"""
import numpy as np
from scipy import signal
from .core import Audio
from .stages import _check

BANDS=((250,800,"low_mid"),(800,2200,"mid"),(2200,5000,"presence"),(5000,11000,"consonants"))
LEVEL_BINS=((-60,-35),(-35,-25),(-25,-15),(-15,0))

def _db_frames(x,sr):
    width=max(1,round(sr*.01))
    n=len(x)//width
    if n<3: raise ValueError("Audio window too short")
    return 20*np.log10(np.sqrt(np.mean(x[:n*width].reshape(n,width)**2,axis=1))+1e-10)

def _measure(x,y,sr,lo,hi,min_frames):
    hi=min(hi,sr*.47)
    if lo>=hi: return {"status":"out_of_band"}
    sos=signal.butter(3,[lo,hi],btype="bandpass",fs=sr,output="sos")
    a=_db_frames(signal.sosfilt(sos,x),sr)
    b=_db_frames(signal.sosfilt(sos,y),sr)
    full=_db_frames(x,sr)
    gain=b-a
    good=(a>-65)&(full>-55)&np.isfinite(gain)
    if good.sum()<min_frames: return {"status":"insufficient_signal","active_frames":int(good.sum())}
    smooth=np.convolve(full,np.ones(5)/5,mode="same")
    slope=np.r_[0,np.diff(smooth)]
    def med(mask):
        return round(float(np.median(gain[mask])),3) if int(mask.sum())>=min_frames else None
    rising=med(good&(slope>.3))
    falling=med(good&(slope<-.3))
    bins={}
    for left,right in LEVEL_BINS:
        mask=good&(full>=left)&(full<right)
        bins[f"{left}:{right}"]={"frames":int(mask.sum()),"gain_db":med(mask)}
    return {"status":"ok","active_frames":int(good.sum()),"gain_median_db":med(good),
            "gain_spread_p90_p10_db":round(float(np.percentile(gain[good],90)-np.percentile(gain[good],10)),3),
            "rising_gain_db":rising,"falling_gain_db":falling,
            "rise_minus_fall_db":round(rising-falling,3) if rising is not None and falling is not None else None,
            "input_level_bins":bins}

def analyze_interactions(dry:Audio,recording:Audio,main:Audio,combined:Audio,
                         *,window:tuple[float,float]=(.9,6.8),min_frames:int=12)->dict:
    _check(dry,recording,main,combined)
    if min_frames<3:raise ValueError("min_frames must be >= 3")
    sr=dry.rate
    if not 0<=window[0]<window[1]<=len(dry.samples)/sr:
        raise ValueError("Invalid analysis window")
    left,right=(round(t*sr) for t in window)
    a,b,c,d=[z.samples[left:right].mean(axis=1) for z in (dry,recording,main,combined)]
    rows={}
    for lo,hi,name in BANDS:
        on_dry=_measure(a,c,sr,lo,hi,min_frames)
        after_recording=_measure(b,d,sr,lo,hi,min_frames)
        matched=[]
        if on_dry["status"]=="ok" and after_recording["status"]=="ok":
            for level in on_dry["input_level_bins"]:
                g1=on_dry["input_level_bins"][level]["gain_db"]
                g2=after_recording["input_level_bins"][level]["gain_db"]
                if g1 is not None and g2 is not None:
                    matched.append({"input_level_dbfs":level,"main_gain_after_recording_minus_dry_db":round(g2-g1,3)})
        rows[name]={"main_on_dry":on_dry,"main_after_recording":after_recording,
                    "same_input_level_differences":matched}
    return {"sample_rate":sr,"analysis_window_s":list(window),"frame_ms":10,
            "band_response":rows,"sources_modified":False,
            "confidence_note":"Observational source-conditioned transfer; does NOT identify plugins or recover proprietary settings. Bins with insufficient frames are omitted."}
