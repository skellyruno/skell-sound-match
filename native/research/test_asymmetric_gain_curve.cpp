#include "AsymmetricGainCurve.h"
#include <cassert>
#include <iostream>
#include <limits>
#include <vector>
using skell::match::AsymmetricGainCurve;
int main(){
    const AsymmetricGainCurve::Params p{std::log(12.),std::log(90.),-24.,.75,3.,6.,std::log(.5),std::log(30.)};
    for(double sr:{44100./16.,48000./16.,96000./16.,44100.,48000.})for(int mode=0;mode<3;++mode){
        AsymmetricGainCurve c;assert(c.prepare(sr,mode,p));std::vector<float>x(10000,.01f),a(x.size()),b(x.size());
        for(std::size_t k=1000;k<6000;++k)x[k]=.5f;
        for(std::size_t k=0;k<x.size();++k)a[k]=c.process(x[k]);
        assert(a[5000]<a[500]-8.f);assert(a.back()>a[5000]);
        c.reset();for(std::size_t k=0;k<x.size();){auto n=std::min<std::size_t>(37,x.size()-k);for(std::size_t j=0;j<n;++j)b[k+j]=c.process(x[k+j]);k+=n;}assert(a==b);
        assert(std::isfinite(c.process(std::numeric_limits<float>::quiet_NaN())));
    }
    AsymmetricGainCurve c;assert(!c.prepare(0,0,p));assert(!c.prepare(44100,3,p));auto bad=p;bad[5]=0;assert(!c.prepare(44100,0,bad));assert(c.process(1)==0);
    std::cout<<"PASS 15 rate/domain configurations, attack/release, reset, block splits, invalid controls\n";
}
