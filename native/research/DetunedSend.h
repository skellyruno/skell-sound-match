#pragma once
#include <array>
#include <cstddef>
#include <algorithm>
#include <cmath>
#include <vector>
namespace skellmatch {
// Static-configuration, causal, two overlapping delay grains per voice.
// This is a new research dub send, not a port of any third-party pitch shifter.
class DetunedSend {
 std::array<std::vector<float>,2> ring;
 std::array<double,2> phase{},step{};
 std::array<double,2> base{};
 double window=1; std::size_t pos=0;
public:
 bool prepare(double sr,double cents,double windowMs,double baseMs) {
  if(!std::isfinite(sr)||sr<8000||sr>192000||!std::isfinite(cents)||cents<1||cents>50||!std::isfinite(windowMs)||windowMs<10||windowMs>100||!std::isfinite(baseMs)||baseMs<2||baseMs>40)return false;
  window=sr*windowMs*.001; base={sr*baseMs*.001,sr*(baseMs+3)*.001};
  step={(1-std::exp2(-cents/1200))/window,(1-std::exp2(cents/1200))/window};
  for(auto& r:ring)r.assign(std::size_t(sr*.15)+8,0.f);
  reset();return true;
 }
 void reset() noexcept {for(auto& r:ring)std::fill(r.begin(),r.end(),0.f);pos=0;phase={0.,.25};}
 std::array<float,2> process(float l,float r) noexcept {
  if(ring[0].empty())return {0,0};
  ring[0][pos]=std::isfinite(l)?std::clamp(l,-32.f,32.f):0.f;ring[1][pos]=std::isfinite(r)?std::clamp(r,-32.f,32.f):0.f;
  std::array<float,2> out{};
  for(int c=0;c<2;++c){
   auto read=[&](double p){double d=base[c]+window*p;auto whole=std::size_t(d);float a=float(d-whole);auto n=ring[c].size();const auto first=pos>=whole?pos-whole:pos+n-whole;
       const auto second=first==0?n-1:first-1;
       float x=ring[c][first],y=ring[c][second];return x+a*(y-x);};
   double p=phase[c],q=p+.5;if(q>=1)q-=1;
   // Complementary raised-cosine crossfade, continuous at the wrap.
   float w=float(.5-.5*std::cos(6.283185307179586*p));out[c]=read(p)*w+read(q)*(1-w);
   phase[c]+=step[c];if(phase[c]>=1)phase[c]-=1;if(phase[c]<0)phase[c]+=1;
  }
  if(++pos==ring[0].size())pos=0;
  return out;
 }
};
}
