#pragma once
#include <algorithm>
#include <cmath>
namespace skelly::research {
// Sample-count linear ramp. Set/reset on processing thread or before playback;
// callers own thread synchronization. A repeated target does not restart a ramp.
class SampleGlide {
public:
    void snap(float v) noexcept { if(!std::isfinite(v))return; value=target=start=v; left=0; }
    void set(float v,int samples) noexcept {
        if(!std::isfinite(v)||v==target)return;
        start=value;target=v;total=left=std::max(1,samples);
    }
    float tick() noexcept {
        const float out=value;
        if(left>0){--left;value=left==0?target:float(double(start)+(double(target)-start)*(double(total-left)/total));}
        return out;
    }
private:
    float value=0,target=0,start=0;
    int left=0,total=1;
};
}
