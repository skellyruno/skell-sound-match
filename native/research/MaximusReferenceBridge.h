#pragma once
// Research-only bridge to the pinned Gridline Maximus reference engine.
// Upstream is GPL-3.0; preserve upstream license; no production rack wiring.
#include "packs/dynamics/maximus_ref.h"
#include <array>
#include <cmath>
#include <cstddef>
namespace skellmatch::maximus {
namespace ref=gl::packs::dynamics::maxref;
struct Point {double x,y,tension;int type;};
struct Settings {
    std::array<int,59> raw{};
    std::array<int,4> counts{};
    std::array<std::array<Point,64>,4> curves{};
    int oversampling=0;
};
// Initial static-only subset: IIR crossovers, no linear-phase, solo or live
// automation. No arbitrary saved state is passed to the upstream processor.
inline bool validate(const Settings& s,double rate) noexcept {
    if(!std::isfinite(rate)||rate<44100.||rate>192000.||s.oversampling<0||s.oversampling>1)return false;
    constexpr int lo[7]={0,0,0,0,0,0,-1},hi[7]={65536,1,65536,1,10000,1000,65536};
    for(int i=0;i<7;++i)if(s.raw[i]<lo[i]||s.raw[i]>hi[i])return false;
    constexpr int blo[13]={0,0,0,-1000,-1000,0,0,0,1,0,1,0,0};
    constexpr int bhi[13]={3,2000,2000,1000,1000,2000,10000,10000,8,10000,8,10000,1};
    for(int b=0;b<4;++b){
        for(int j=0;j<13;++j){auto v=s.raw[7+13*b+j];if(v<blo[j]||v>bhi[j])return false;}
        auto n=s.counts[b];if(n<2||n>64)return false;
        for(int k=0;k<n;++k){const auto& p=s.curves[b][k];
            if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.tension)||p.x<0.||p.x>1.||p.y<0.||p.y>1.||std::abs(p.tension)>1.||p.type<0||p.type>12||(k&&p.x<=s.curves[b][k-1].x))return false;
        }
        if(s.curves[b][0].x!=0.||s.curves[b][n-1].x!=1.)return false;
    }
    return true;
}
class StaticProcessor {
    ref::Engine engine;
    bool ready=false;
public:
    bool prepare(const Settings& s,double rate){
        ready=false;if(!validate(s,rate))return false;
        ref::RefState state{};std::copy(s.raw.begin(),s.raw.end(),state.raw);state.os=s.oversampling;
        for(int b=0;b<4;++b){auto& c=state.curve[b];c.n=s.counts[b];for(int i=0;i<c.n;++i){auto p=s.curves[b][i];c.x[i]=p.x;c.y[i]=p.y;c.t[i]=p.tension;c.type[i]=p.type;}c.prepareTangents();}
        engine.prepare(state,rate);engine.configure(state,rate);engine.reset();ready=true;return true;
    }
    int latency() const noexcept{return ready?engine.latency():-1;}
    // Static processing. Callers must supply distinct, valid planar buffers.
    // Bound extreme/nonfinite audio before the reference engine sees it.
    bool process(float* left,float* right,int n) noexcept{
        if(!ready||!left||!right||left==right||n<0)return false;
        for(int i=0;i<n;++i){auto clean=[](float x){return std::isfinite(x)?std::clamp(x,-8.f,8.f):0.f;};left[i]=clean(left[i]);right[i]=clean(right[i]);}
        engine.process(left,right,n);return true;
    }
};
}
