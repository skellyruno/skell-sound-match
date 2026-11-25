#include "SampleGlide.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
#include <vector>
using skelly::research::SampleGlide;
int main(){int cases=0;for(int rate:{44100,48000,96000,192000}){int n=rate/100;auto run=[&](int block){SampleGlide s;s.snap(0);std::vector<float> v;for(int i=0;i<3*n;){int m=std::min(block,3*n-i);for(int j=0;j<m;++j,++i){if(i==0)s.set(1,n);if(i==n/2)s.set(-1,n);if(i%19==0)s.set(i<n/2?1:-1,n);v.push_back(s.tick());}}return v;};auto a=run(512);for(int b:{1,64,127,1024}){assert(a==run(b));++cases;}assert(a.front()==0&&a.back()==-1);++cases;SampleGlide s;s.snap(.2f);s.set(1,n);for(int i=0;i<n;++i)s.tick();assert(s.tick()==1);s.set(std::numeric_limits<float>::quiet_NaN(),n);assert(s.tick()==1);s.snap(std::numeric_limits<float>::infinity());assert(s.tick()==1);++cases;}std::cout<<cases<<" sample glide cases passed\n";}
