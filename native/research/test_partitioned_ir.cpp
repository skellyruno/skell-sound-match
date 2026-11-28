#include "PartitionedIR.h"
#include <cassert>
#include <iostream>
#include <random>
#include <limits>
using skell::match::PartitionedIR;
int main(){
 std::mt19937 rng(71);std::uniform_real_distribution<float> d(-.1f,.1f);
 for(auto n:{1,15,128,256,257,513,4097}){
  std::vector<float> h(n),x(2049),a(x.size()+n),b(a.size()),expected(a.size());for(auto& v:h)v=d(rng);for(auto& v:x)v=d(rng);
  x.resize(a.size(),0);PartitionedIR<256> p;p.prepare(h.data(),h.size());
  for(std::size_t i=0;i<a.size();++i)for(std::size_t k=0;k<h.size()&&k<=i;++k)expected[i]+=h[k]*x[i-k];
  p.processBlock(x.data(),a.data(),x.size());for(std::size_t i=0;i<a.size();++i)assert(std::abs(a[i]-expected[i])<5e-5f);
  p.reset();for(std::size_t i=0;i<b.size();){auto k=std::min<std::size_t>(b.size()-i,37);p.processBlock(x.data()+i,b.data()+i,k);i+=k;}assert(a==b);
  p.reset();p.processBlock(x.data(),b.data(),b.size());assert(a==b);
 }
 PartitionedIR<256> p;std::vector<float> impulse(4097);impulse[0]=1;impulse[256]=.2f;impulse[4096]=.1f;p.prepare(impulse.data(),impulse.size());for(std::size_t n=0;n<5000;++n)assert(std::abs(p.process(n==0?1.f:0.f)-(n<impulse.size()?impulse[n]:0))<1e-6f);
 bool rejected=false;float nan=std::numeric_limits<float>::quiet_NaN();try{p.prepare(&nan,1);}catch(const std::invalid_argument&){rejected=true;}assert(rejected);std::cout<<"PASS 7 IR lengths, direct convolution, odd blocks, reset, boundary impulses, invalid IR\n";
}
