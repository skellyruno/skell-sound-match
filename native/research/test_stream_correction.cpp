#include "StreamCorrection.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
static bool tracking=false;static int allocs=0;
void* operator new(std::size_t n){if(tracking)++allocs;if(auto* p=std::malloc(n))return p;throw std::bad_alloc();}
void operator delete(void* p) noexcept{std::free(p);}void operator delete(void* p,std::size_t) noexcept{std::free(p);}
using namespace skelly::research;
int main(){int cases=0;for(int rate:{44100,48000,96000,192000}){std::vector<float>x(rate*2);for(size_t i=0;i<x.size();++i)x[i]=.08f*std::sin(i*.018)+.04f*std::cos(i*.071);CorrectionSettings s;s.low=-3;s.high=5;s.compression=.4;s.drive=1.8;s.side=6;s.echo=.35;s.delay_ms=125;s.motion=.4;s.gain=-2;
StreamCorrection a,b;assert(a.prepare(rate,s)&&b.prepare(rate,s));auto y=x,z=x;tracking=true;a.process(y.data(),rate);for(int i=0;i<rate;i+=127)b.process(z.data()+2*i,std::min(127,rate-i));tracking=false;assert(y==z&&allocs==0);++cases;
a.reset();z=x;a.process(z.data(),rate);assert(y==z);++cases;
assert(std::all_of(y.begin(),y.end(),[](float v){return std::isfinite(v);}));++cases;
assert(a.prepare(rate,{}));z=x;a.process(z.data(),rate);assert(x==z);++cases;
assert(a.delayStorageBytes()<=static_cast<size_t>(3*rate*.125+1)*8);++cases;
CorrectionSettings invalid;invalid.echo=2;assert(!a.prepare(rate,invalid));++cases;
}std::cout<<cases<<" native checks passed; process allocations "<<allocs<<'\n';}
