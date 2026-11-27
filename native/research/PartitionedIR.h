#pragma once
// Fixed-IR research processor: direct head, uniformly partitioned FFT tail.
// prepare() allocates; process()/reset() allocate nothing. No added sample
// delay beyond the IR itself. Not a JUCE host integration or automation API.
#include <algorithm>
#include <array>
#include <cmath>
#include <complex>
#include <cstddef>
#include <stdexcept>
#include <vector>
namespace skell::match {
template<std::size_t P=256> class PartitionedIR {
 static_assert(P>=16 && (P&(P-1))==0,"partition must be a power of two");
 using C=std::complex<float>;
 static constexpr std::size_t N=2*P, B=P+1;
 using Frame=std::array<C,N>;
 using Half=std::array<C,B>;
 std::array<float,P> head{}, history{}, input{}, tail{}, overlap{};
 std::array<C,N/2> twiddle{};
 std::array<std::size_t,N> reverse{};
 Frame frame{};
 std::vector<Half> kernels, spectra;
 std::size_t pos=0, write=0, ring=0, ready=0, headCount=0;
 void fft(Frame& a,bool inverse) noexcept {
  for(std::size_t i=0;i<N;++i)if(i<reverse[i])std::swap(a[i],a[reverse[i]]);
  for(std::size_t len=2;len<=N;len*=2){auto step=N/len;
   for(std::size_t j=0;j<len/2;++j){auto w=twiddle[j*step];if(inverse)w=std::conj(w);
    for(std::size_t i=j;i<N;i+=len){auto u=a[i],v=a[i+len/2]*w;a[i]=u+v;a[i+len/2]=u-v;}
   }
  }
  if(inverse)for(auto& v:a)v*=1.f/static_cast<float>(N);
 }
 void finishBlock() noexcept {
  if(kernels.empty())return;
  for(std::size_t i=0;i<P;++i){frame[i]={input[i],0};frame[i+P]={};}
  fft(frame,false);auto& slot=spectra[ring];std::copy_n(frame.begin(),B,slot.begin());
  ready=std::min(ready+1,kernels.size());frame.fill({});
  for(std::size_t j=0;j<ready;++j){const auto& x=spectra[(ring+kernels.size()-j)%kernels.size()];const auto& h=kernels[j];
   for(std::size_t k=0;k<B;++k)frame[k]+=x[k]*h[k];
  }
  frame[0]={frame[0].real(),0};frame[P]={frame[P].real(),0};
  for(std::size_t k=1;k<P;++k){frame[N-k]=std::conj(frame[k]);}
  fft(frame,true);
  for(std::size_t i=0;i<P;++i){tail[i]=frame[i].real()+overlap[i];overlap[i]=frame[i+P].real();}
  if(++ring==kernels.size())ring=0;
 }
public:
 static constexpr std::size_t additionalLatency=0;
 void prepare(const float* ir,std::size_t length){
  if(!ir || length==0 || length>1048576)throw std::invalid_argument("invalid IR length");
  for(std::size_t i=0;i<length;++i)if(!std::isfinite(ir[i]))throw std::invalid_argument("nonfinite IR");
  constexpr double pi=3.14159265358979323846;
  for(std::size_t k=0;k<N/2;++k){double phase=-2*pi*static_cast<double>(k)/static_cast<double>(N);twiddle[k]={static_cast<float>(std::cos(phase)),static_cast<float>(std::sin(phase))};}
  for(std::size_t i=0;i<N;++i){std::size_t q=i,r=0;for(std::size_t b=N;b>1;b>>=1){r=(r<<1)|(q&1);q>>=1;}reverse[i]=r;}
  head.fill(0);headCount=std::min(P,length);std::copy_n(ir,headCount,head.begin());
  const std::size_t count=length>P?(length-P+P-1)/P:0;
  kernels.assign(count,{});spectra.assign(count,{});
  for(std::size_t j=0;j<count;++j){frame.fill({});const auto offset=P+j*P;for(std::size_t k=0;k<std::min(P,length-offset);++k)frame[k]={ir[offset+k],0};fft(frame,false);std::copy_n(frame.begin(),B,kernels[j].begin());}
  reset();
 }
 void reset() noexcept {history.fill(0);input.fill(0);tail.fill(0);overlap.fill(0);pos=write=ring=ready=0;}
 float process(float sample) noexcept {
  if(!std::isfinite(sample))sample=0;
  history[write]=sample;input[pos]=sample;
  float sum=0;const auto first=std::min(headCount,write+1);
  for(std::size_t k=0;k<first;++k)sum+=head[k]*history[write-k];
  for(std::size_t k=first;k<headCount;++k)sum+=head[k]*history[P+write-k];
  sum+=tail[pos];write=(write+1)&(P-1);
  if(++pos==P){pos=0;finishBlock();}
  return sum;
 }
 void processBlock(const float* in,float* out,std::size_t n) noexcept {for(std::size_t i=0;i<n;++i)out[i]=process(in[i]);}
};
} // namespace skell::match
