#include "PlanarCorrection.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
#include <limits>
static bool tracking=false;static int allocs=0;
void* operator new(std::size_t n){if(tracking)++allocs;if(auto* p=std::malloc(n))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}void operator delete(void* p,std::size_t) noexcept{std::free(p);}
using namespace skelly::research;
int main(){int cases=0;for(int rate:{44100,48000,96000,192000}){int n=rate/2;std::vector<float> l(n),r(n),inter(2*n);for(int i=0;i<n;++i){inter[2*i]=l[i]=.12f*std::sin(i*.033);inter[2*i+1]=r[i]=.15f*std::cos(i*.029);}
CorrectionSettings s;s.low=-3;s.high=5;s.compression=.4;s.drive=1.8;s.side=6;s.echo=.35;s.delay_ms=25;s.motion=.4;s.gain=-2;
StreamCorrection raw;PlanarCorrection a,b;assert(raw.prepare(rate,s)&&a.prepare(rate,s));auto x=l,y=r;raw.process(inter.data(),n);tracking=true;assert(a.process(x.data(),y.data(),n));tracking=false;for(int i=0;i<n;++i){assert(x[i]==inter[2*i]&&y[i]==inter[2*i+1]);}++cases;
a.reset();x=l;y=r;assert(a.process(x.data(),y.data(),n));for(int i=0;i<n;++i)assert(x[i]==inter[2*i]&&y[i]==inter[2*i+1]);++cases;
assert(a.prepare(rate,s,0));x=l;y=r;assert(a.process(x.data(),y.data(),n));assert(x==l&&y==r);++cases;
// Same events, different host partitions; repeated setWet must not restart.
auto run=[&](int block){PlanarCorrection p;assert(p.prepare(rate,s,0));auto u=l,v=r;int i=0;tracking=true;while(i<n){float w=i<100?0:i<rate/50?1:.35f;assert(p.setWet(w));int stop=i<100?100:i<rate/50?rate/50:n;int k=std::min(block,stop-i);assert(p.process(u.data()+i,v.data()+i,k));i+=k;}tracking=false;return std::make_pair(u,v);};
assert(run(127)==run(1024));++cases;
assert(b.prepare(rate,s,0));assert(b.setWet(1));x=l;y=r;assert(b.process(x.data(),y.data(),rate/100));assert(b.currentWet()==1);++cases;
assert(!b.setWet(std::numeric_limits<float>::quiet_NaN())&&!b.setWet(-.1f)&&!b.setWet(1.1f));assert(!b.process(x.data(),x.data(),1));assert(!b.process(nullptr,y.data(),1));++cases;
assert(b.prepare(rate,s,0));x[0]=std::numeric_limits<float>::infinity();y[0]=std::numeric_limits<float>::quiet_NaN();assert(b.process(x.data(),y.data(),1));assert(x[0]==0&&y[0]==0);++cases;
// Bypass must retain delayed history: an impulse during bypass echoes after unmute.
CorrectionSettings e;e.echo=.5;e.delay_ms=100;assert(b.prepare(rate,e,0));x.assign(n,0);y.assign(n,0);x[0]=.5;assert(b.process(x.data(),y.data(),rate/50));assert(b.setWet(1));assert(b.process(x.data()+rate/50,y.data()+rate/50,n-rate/50));assert(y[rate/10]==.25f);++cases;
}assert(allocs==0);std::cout<<cases<<" planar host checks passed; processing allocations "<<allocs<<'\n';}
