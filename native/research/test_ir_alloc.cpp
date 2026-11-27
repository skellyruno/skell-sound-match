#include "PartitionedIR.h"
#include <cassert>
#include <iostream>
unsigned long irAllocationCount() noexcept;
int main(){std::vector<float> h(136241,.00001f),x(48000,.1f),y(x.size());skell::match::PartitionedIR<256> p;p.prepare(h.data(),h.size());auto before=irAllocationCount();for(int k=0;k<2;++k){p.processBlock(x.data(),y.data(),x.size());p.reset();}assert(irAllocationCount()==before);std::cout<<"PASS no allocations during processBlock/reset, 136241 taps\n";}
