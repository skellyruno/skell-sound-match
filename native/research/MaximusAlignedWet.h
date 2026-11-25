#pragma once
// Research-only adapter. Static reference settings prepared off audio thread.
// Wet control and process are called by a single audio thread; no concurrent prepare.
#include "MaximusReferenceBridge.h"
#include <vector>
namespace skellmatch::maximus {
class AlignedWet {
    StaticProcessor processor;
    std::vector<float> delayL,delayR,dryL,dryR;
    std::size_t head=0,chunk=0;
    int latencyFrames=-1,ramp=0,remaining=0;
    float mix=1.f,target=1.f;
    static float finite(float x) noexcept {return std::isfinite(x)?x:0.f;}
public:
    bool prepare(const Settings& settings,double rate,std::size_t maxBlock,float initialWet=1.f){
        latencyFrames=-1;
        if(!maxBlock||maxBlock>65536||!std::isfinite(initialWet)||initialWet<0||initialWet>1||!processor.prepare(settings,rate))return false;
        const int lat=processor.latency();if(lat<0||lat>rate*3.)return false;
        delayL.assign(static_cast<std::size_t>(lat),0.f);delayR=delayL;
        dryL.assign(maxBlock,0.f);dryR=dryL;chunk=maxBlock;head=0;
        ramp=std::max(1,static_cast<int>(std::round(rate*.010)));remaining=0;mix=target=initialWet;latencyFrames=lat;return true;
    }
    int latency() const noexcept{return latencyFrames;}
    bool setWet(float wet) noexcept {
        if(latencyFrames<0||!std::isfinite(wet)||wet<0.f||wet>1.f)return false;
        if(wet!=target){target=wet;remaining=ramp;}return true;
    }
    // Distinct non-overlapping planar buffers; no host latency changes after prepare.
    bool process(float* l,float* r,int n) noexcept {
        if(latencyFrames<0||!l||!r||l==r||n<0)return false;
        for(std::size_t base=0;base<static_cast<std::size_t>(n);){
            const auto count=std::min(chunk,static_cast<std::size_t>(n)-base);
            for(std::size_t i=0;i<count;++i){
                const float a=finite(l[base+i]),b=finite(r[base+i]);
                if(latencyFrames){dryL[i]=delayL[head];dryR[i]=delayR[head];delayL[head]=a;delayR[head]=b;if(++head==delayL.size())head=0;}
                else {dryL[i]=a;dryR[i]=b;}
            }
            // Always run the engine, including bypass, to retain detector history.
            if(!processor.process(l+base,r+base,static_cast<int>(count)))return false;
            for(std::size_t i=0;i<count;++i){
                if(remaining>0){mix+=(target-mix)/static_cast<float>(remaining);if(--remaining==0)mix=target;}
                const auto at=base+i;
                if(mix==0.f){l[at]=dryL[i];r[at]=dryR[i];}
                else if(mix!=1.f){l[at]=dryL[i]+mix*(l[at]-dryL[i]);r[at]=dryR[i]+mix*(r[at]-dryR[i]);}
            }
            base+=count;
        }return true;
    }
};
}
