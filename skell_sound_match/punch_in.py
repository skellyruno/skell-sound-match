"""Identify separate active-vocal regions and blend pre-rendered candidates between phrases.

Waveform activity DOES NOT prove the FL Studio edit/punch boundaries.
The reference never controls the render. Offline research; not realtime-safe DSP.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Sequence
import numpy as np
from scipy.ndimage import gaussian_filter1d, binary_closing, binary_opening

@dataclass(frozen=True)
class Region:
    start: float
    end: float

def detect_regions(dry: np.ndarray, rate: int, *, frame_ms=10.0,
                   min_gap_ms=180., min_duration_ms=50.,
                   relative_threshold=.05, minimum_rms=.0003) -> list[Region]:
    x = np.asarray(dry, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] not in (1, 2) or not np.isfinite(x).all():
        raise ValueError("Dry source must be finite mono/stereo (samples,channels)")
    if not 16000 <= rate <= 192000 or len(x) < rate // 4:
        raise ValueError("Invalid audio rate or duration")
    if not (2 <= frame_ms <= 40 and 0 <= min_gap_ms <= 1000
            and 10 <= min_duration_ms <= 1000 and 0 < relative_threshold < 1
            and 0 <= minimum_rms < 1):
        raise ValueError("Invalid detection configuration")
    step = max(1, round(rate * frame_ms / 1000))
    n = len(x) // step
    rms = np.sqrt(np.mean(x[:n*step].reshape(n, step, x.shape[1])**2, axis=(1,2)))
    smooth = gaussian_filter1d(rms, sigma=max(.5, 20. / frame_ms))
    threshold = max(float(np.quantile(smooth, .95)) * relative_threshold, minimum_rms)
    mask = smooth > threshold
    mask = binary_closing(mask, structure=np.ones(max(1, round(min_gap_ms/frame_ms)), dtype=bool))
    mask = binary_opening(mask, structure=np.ones(max(1, round(min_duration_ms/frame_ms)), dtype=bool))
    edges = np.diff(np.r_[0,mask.astype(np.int8),0])
    return [Region(float(s*step/rate),float(e*step/rate))
            for s,e in zip(np.where(edges==1)[0],np.where(edges==-1)[0])]

def blend_regions(champion: np.ndarray, experiment: np.ndarray, rate: int,
                  regions: Sequence[Region], weights: Sequence[float]) -> np.ndarray:
    """Keep each active phrase constant, crossfade between phrases in silence.

    Region weights are fitted/reviewed for ONE TAKE and MUST NOT be reused
    by timestamp for future vocals or exported as native automation.
    """
    a=np.asarray(champion,dtype=np.float64)
    b=np.asarray(experiment,dtype=np.float64)
    if (a.ndim!=2 or a.shape!=b.shape or a.shape[1] not in (1,2)
            or not np.isfinite(a).all() or not np.isfinite(b).all()):
        raise ValueError("Same-shaped finite mono/stereo arrays required")
    if not 16000 <= rate <= 192000 or not regions or len(weights)!=len(regions):
        raise ValueError("Invalid rate or region weights")
    n=len(a);positions=[0];values=[float(weights[0])];previous=0
    for i,(region,weight) in enumerate(zip(regions,weights)):
        if not np.isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError("Unsafe mix weight")
        start=round(region.start*rate);end=round(region.end*rate)
        if not 0<=start<end<=n or start<previous:
            raise ValueError("Invalid, overlapping or out-of-bounds regions")
        if start==0 and i==0:values[0]=float(weight)
        else:positions.append(start);values.append(float(weight))
        positions.append(end-1);values.append(float(weight))
        previous=end
    if positions[-1]<n-1:
        positions.append(n-1);values.append(float(weights[-1]))
    knots={k:v for k,v in zip(positions,values)}
    keys=np.array(sorted(knots),dtype=int)
    levels=np.array([knots[k] for k in keys],dtype=float)
    alpha=np.interp(np.arange(n),keys,levels)
    return a+alpha[:,None]*(b-a)

def main():
    import argparse, json
    import soundfile as sf
    p=argparse.ArgumentParser(description="Estimate dry-vocal activity; not actual punch edits")
    p.add_argument("dry_wav");args=p.parse_args()
    x,rate=sf.read(args.dry_wav,dtype="float64",always_2d=True)
    out=detect_regions(x,rate)
    print(json.dumps({"sample_rate":rate,"regions":[asdict(r) for r in out],
      "notice":"Candidate active-vocal regions only; verify true punch boundaries in FL Studio"},indent=2))

if __name__=="__main__":
    main()
