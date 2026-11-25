#pragma once
#include <algorithm>
#include <cmath>
namespace skelly::research {
struct CompressorSettings {
 double fastMs=2, slowMs=80, threshold=-18, slope=0, knee=6, peakMix=0, wet=1, makeup=1;
};
// Independent static-recipe linked compressor. Configure outside the callback.
class StreamingCompressor {
public:
 bool prepare(double rate, const CompressorSettings& v) noexcept {
  const auto in=[](double x,double lo,double hi){return std::isfinite(x)&&x>=lo&&x<=hi;};
  if(!in(rate,32000,192000)||!in(v.fastMs,.1,40)||!in(v.slowMs,10,400)||v.fastMs>v.slowMs||!in(v.threshold,-60,0)||!in(v.slope,0,.98)||!in(v.knee,0,24)||!in(v.peakMix,0,1)||!in(v.wet,0,1)||!in(v.makeup,.05,8))return false;
  s=v; af=-std::expm1(-1000/(s.fastMs*rate)); as=-std::expm1(-1000/(s.slowMs*rate)); reset(); return true;
 }
 void reset() noexcept { fast=slow=0; }
 void process(float* left,float* right,int n) noexcept {
  for(int i=0;i<n;++i){
   const double l=left[i],r=right[i],p=(l*l+r*r)*.5;
   const double d=p+s.peakMix*(std::max(l*l,r*r)-p);
   fast=af*d+(1-af)*fast;slow=as*d+(1-as)*slow;
   const double level=10*std::log10(std::max({fast,slow,1e-15}));
   const double x=level-s.threshold,h=s.knee*.5;
   const double excess=s.knee==0?std::max(x,0.):x<=-h?0.:x>=h?x:(x+h)*(x+h)/(2*s.knee);
   const double g=s.makeup*((1-s.wet)+s.wet*std::pow(10.,-s.slope*excess/20));
   left[i]=static_cast<float>(l*g);right[i]=static_cast<float>(r*g);
  }
 }
private:
 CompressorSettings s{};double af=0,as=0,fast=0,slow=0;
};
}
