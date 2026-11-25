#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>
namespace skelly::research {
struct CorrectionSettings {
    double low=0,mid=0,high=0,compression=0,side=0,gain=0,drive=0,echo=0,delay_ms=125,motion=0,motion_hz=.7,threshold_db=-24;
    bool valid() const noexcept {
        auto in=[](double x,double lo,double hi){return std::isfinite(x)&&x>=lo&&x<=hi;};
        return in(low,-9,9)&&in(mid,-9,9)&&in(high,-9,9)&&in(compression,0,.8)&&in(side,-12,12)&&in(gain,-18,18)&&in(drive,0,4)&&in(echo,0,.7)&&in(delay_ms,20,900)&&in(motion,0,.7)&&in(motion_hz,.15,8)&&in(threshold_db,-90,0);
    }
};
// Independent R19 correction, not a proprietary effect emulation. Fixed settings;
// prepare only while stopped. No callback allocations, locks or parameter changes.
class StreamCorrection {
    using Frame=std::array<float,2>;
    CorrectionSettings p{}; int rate=0; std::size_t delay=1,pos=0; unsigned long long sample=0;
    std::vector<Frame> ring; std::array<std::array<double,2>,2> low{};
    std::array<std::array<double,3>,2> env{};
    std::array<double,2> alpha{},det{}; float sideScale=0,gainScale=1; double phaseStep=0;
public:
    bool prepare(int sr,CorrectionSettings settings) {
        if(sr<32000||sr>192000||!settings.valid())return false;
        p=settings; rate=sr; delay=static_cast<std::size_t>(std::nearbyint(p.delay_ms*sr/1000.)); delay=std::max<std::size_t>(1,delay);
        ring.assign(p.echo!=0?3*delay+1:1,Frame{});
        constexpr double pi=3.14159265358979323846;
        alpha={-std::expm1(-2*pi*250/sr),-std::expm1(-2*pi*3500/sr)};
        det={-std::expm1(-1000./(4*sr)),-std::expm1(-1000./(90*sr))};
        sideScale=static_cast<float>(std::pow(10.,p.side/20)-1);gainScale=static_cast<float>(std::pow(10.,p.gain/20));phaseStep=2*pi*p.motion_hz/sr;
        reset();return true;
    }
    void reset() noexcept {low={};env={};std::fill(ring.begin(),ring.end(),Frame{});pos=0;sample=0;}
    std::size_t delayStorageBytes()const noexcept{return ring.capacity()*sizeof(Frame);}
    bool ready() const noexcept{return rate!=0;}
    void process(float* interleaved,std::size_t frames) noexcept {
        if(!ready()||!interleaved)return;
        const bool tone=p.low!=0||p.mid!=0||p.high!=0||p.compression!=0;
        const std::array<float,3> bandsDb{static_cast<float>(p.low),static_cast<float>(p.mid),static_cast<float>(p.high)};
        for(std::size_t i=0;i<frames;++i,++sample){
            Frame x{interleaved[2*i],interleaved[2*i+1]},y=x;
            for(auto& v:x)if(!std::isfinite(v))v=0;
            y=x;
            if(tone){
                std::array<Frame,3>b{};
                for(int c=0;c<2;++c){for(int j=0;j<2;++j)low[j][c]+=alpha[j]*(x[c]-low[j][c]);float a=static_cast<float>(low[0][c]),d=static_cast<float>(low[1][c]);b[0][c]=a;b[1][c]=d-a;b[2][c]=x[c]-d;}
                y={};
                for(int k=0;k<3;++k){double power=(double(b[k][0])*b[k][0]+double(b[k][1])*b[k][1])*.5;for(int j=0;j<2;++j)env[j][k]+=det[j]*(power-env[j][k]);float over=static_cast<float>(std::max(10*std::log10(std::max({env[0][k],env[1][k],1e-15}))-p.threshold_db,0.));float g=std::pow(10.f,(bandsDb[k]-static_cast<float>(p.compression)*over)/20.f);for(int c=0;c<2;++c)y[c]+=g*b[k][c];}
            }
            if(p.drive){float d=static_cast<float>(p.drive);for(auto& v:y)v=std::tanh(v*d)/d;}
            if(p.side){float d=(y[0]-y[1])*.5f*sideScale;y[0]+=d;y[1]-=d;}
            if(p.motion){double a=p.motion*std::sin(double(sample)*phaseStep);y[0]=static_cast<float>(y[0]*(1+a));y[1]=static_cast<float>(y[1]*(1-a));}
            if(p.echo){Frame dry=y;ring[pos]=dry;for(int j=1;j<=3;++j){auto idx=(pos+ring.size()-j*delay)%ring.size();float g=static_cast<float>(p.echo*(j==1?1.:j==2?.35:.12));y[0]+=g*ring[idx][1];y[1]+=g*ring[idx][0];}if(++pos==ring.size())pos=0;}
            if(p.gain)for(auto& v:y)v*=gainScale;
            interleaved[2*i]=y[0];interleaved[2*i+1]=y[1];
        }
    }
};
}
