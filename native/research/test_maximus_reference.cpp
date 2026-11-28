#include "MaximusReferenceBridge.h"
#include <cstdio>
#include <cstdlib>
#include <new>
#include <limits>
#include <vector>
extern bool tracking;
extern std::size_t allocations;
using namespace skellmatch::maximus;
static Settings testState(int os){
    Settings s{};s.oversampling=os;
    const int g[7]={19800,1,48065,1,1115,700,32768};std::copy(g,g+7,s.raw.begin());
    const int band[13]={0,1000,1000,0,0,1000,1115,0,2,5000,3,2882,0};
    for(int b=0;b<4;++b){std::copy(band,band+13,s.raw.begin()+7+b*13);s.counts[b]=3;s.curves[b][0]={0,0,0,0};s.curves[b][1]={.5,.43,0,0};s.curves[b][2]={1,.55,0,0};}
    return s;
}
int main(){int checks=0;for(double rate:{44100.,48000.,96000.,192000.})for(int os:{0,1}){
    auto s=testState(os);StaticProcessor a,b;if(!a.prepare(s,rate)||!b.prepare(s,rate))return 1;
    if(a.latency()<0||a.latency()!=b.latency())return 2;
    const int n=24000;std::vector<float> l(n),r(n),u(n),v(n);
    for(int i=0;i<n;++i){l[i]=.15f*std::sin(i*.018f)+.08f*std::sin(i*.64f);r[i]=.11f*std::sin(i*.021f);}
    l[102]=std::numeric_limits<float>::quiet_NaN();r[122]=std::numeric_limits<float>::infinity();u=l;v=r;
    tracking=true;for(int i=0;i<n;i+=127)if(!a.process(l.data()+i,r.data()+i,std::min(127,n-i)))return 3;for(int i=0;i<n;i+=512)if(!b.process(u.data()+i,v.data()+i,std::min(512,n-i)))return 4;tracking=false;
    float diff=0.f,pk=0.f;for(int i=0;i<n;++i){if(!std::isfinite(l[i])||!std::isfinite(r[i])||!std::isfinite(u[i])||!std::isfinite(v[i]))return 5;diff=std::max({diff,std::abs(l[i]-u[i]),std::abs(r[i]-v[i])});pk=std::max({pk,std::abs(l[i]),std::abs(r[i])});}
    if(diff>1e-6f||pk<=1e-6f||pk>8.f||allocations)return 6;
    std::printf("rate %.0f os %d latency %d peak %.8f block diff %.9g allocations %zu\n",rate,os,a.latency(),pk,diff,allocations);++checks;
    s.raw[5]=1001;if(validate(s,rate))return 7;s=testState(os);s.curves[0][1].x=0;if(validate(s,rate))return 8;
}
std::printf("%d Maximus reference static rate/oversampling cases passed\n",checks);}
