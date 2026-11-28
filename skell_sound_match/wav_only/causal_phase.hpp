#pragma once
// Research-only causal phase correction. No sample lookahead, no allocation,
// and no dependencies on reference audio. Static configuration is off the
// audio thread; this is not yet an automatable Skell Preset effect.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
namespace skell::match {
class CausalPhase {
public:
    struct Section { double hz=1000.0, q=0.70710678; };
    bool configure(double sampleRate, const std::array<Section,3>& settings,
                   std::size_t sections, int polarity=1) noexcept {
        if(!std::isfinite(sampleRate)||sampleRate<32000.||sampleRate>192000.||sections>3||(polarity!=1&&polarity!=-1))return false;
        for(std::size_t i=0;i<sections;++i)
            if(!std::isfinite(settings[i].hz)||!std::isfinite(settings[i].q)||settings[i].hz<40.||settings[i].hz>14000.||settings[i].q<0.25||settings[i].q>8.)return false;
        constexpr double pi=3.1415926535897932384626433832795;
        count=sections;sign=polarity;
        for(std::size_t i=0;i<count;++i){
            double w=2.*pi*std::clamp(settings[i].hz,40.,sampleRate*.45)/sampleRate;
            double a=std::sin(w)/(2.*settings[i].q);
            filters[i].a1=-2.*std::cos(w)/(1.+a);filters[i].a2=(1.-a)/(1.+a);
        }
        reset();return true;
    }
    void reset() noexcept {for(auto& f:filters){f.z1.fill(0.);f.z2.fill(0.);}}
    std::array<float,2> process(float left,float right) noexcept {
        std::array<float,2> result{};const float input[2]{left,right};
        for(std::size_t ch=0;ch<2;++ch){
            double x=std::isfinite(input[ch])?input[ch]:0.;
            for(std::size_t k=0;k<count;++k){
                auto& f=filters[k];const double y=f.a2*x+f.z1[ch];
                f.z1[ch]=f.a1*(x-y)+f.z2[ch];f.z2[ch]=x-f.a2*y;
                if(std::abs(f.z1[ch])<1.e-25)f.z1[ch]=0.;
                if(std::abs(f.z2[ch])<1.e-25)f.z2[ch]=0.;
                x=y;
            }
            result[ch]=std::isfinite(x)?static_cast<float>(sign*x):0.f;
        }
        return result;
    }
private:
    struct Filter{double a1=0.,a2=0.;std::array<double,2> z1{},z2{};};
    std::array<Filter,3> filters{};
    std::size_t count=0;int sign=1;
};
} // namespace skell::match
