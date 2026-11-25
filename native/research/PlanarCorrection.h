#pragma once
#include "StreamCorrection.h"
#include <cmath>
#include <algorithm>
namespace skelly::research {
// Fixed recipe, stereo planar host adapter. All lifecycle and control calls
// are serialized by the caller; prepare/reset are outside live processing.
// Wet changes on the processing thread only. No parameter/latency ID changes.
class PlanarCorrection final {
    StreamCorrection engine;
    int ramp=1,remaining=0;
    float wet=1.f,target=1.f,start=1.f;
    static float safe(float v) noexcept {return std::isfinite(v)?v:0.f;}
public:
    bool prepare(int rate,const CorrectionSettings& settings,float initialWet=1.f) {
        if(!std::isfinite(initialWet)||initialWet<0||initialWet>1)return false;
        if(!engine.prepare(rate,settings))return false;
        ramp=std::max(1,rate/100);wet=target=start=initialWet;remaining=0;return true;
    }
    void reset() noexcept {engine.reset();wet=start=target;remaining=0;}
    bool setWet(float v) noexcept {
        if(!std::isfinite(v)||v<0||v>1)return false;
        if(v!=target){start=wet;target=v;remaining=ramp;}return true;
    }
    float currentWet() const noexcept {return wet;}
    bool process(float* l,float* r,std::size_t frames) noexcept {
        // Require two distinct, non-overlapping channel buffers. No mono aliasing.
        if(!engine.ready()||!l||!r||l==r)return false;
        for(std::size_t i=0;i<frames;++i){
            const float a=safe(l[i]),b=safe(r[i]);float f[2]{a,b};
            engine.process(f,1); // preserve history even while bypassed
            if(wet==0){l[i]=a;r[i]=b;}
            else if(wet==1){l[i]=safe(f[0]);r[i]=safe(f[1]);}
            else {l[i]=safe(float(double(a)+(double(safe(f[0]))-a)*wet));r[i]=safe(float(double(b)+(double(safe(f[1]))-b)*wet));}
            if(remaining>0){--remaining;wet=remaining==0?target:float(double(start)+(double(target)-start)*double(ramp-remaining)/ramp);}
        }
        return true;
    }
};
}
