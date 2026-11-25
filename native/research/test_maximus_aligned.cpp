#include "MaximusAlignedWet.h"
#include <cstdio>
#include <limits>
extern bool tracking;
extern std::size_t allocations;
using namespace skellmatch::maximus;
static Settings state(int os){
 Settings s{};s.oversampling=os;const int g[7]={19800,1,48065,1,891,500,32768};std::copy_n(g,7,s.raw.begin());
 const int band[13]={0,1000,1000,0,0,1000,1115,0,2,5000,3,2882,0};
 for(int b=0;b<4;++b){std::copy_n(band,13,s.raw.begin()+7+b*13);s.counts[b]=3;s.curves[b][0]={0,0,0,0};s.curves[b][1]={.5,.43,0,0};s.curves[b][2]={1,.55,0,0};}return s;
}
int main(){int checks=0;for(double rate:{44100.,48000.,96000.,192000.})for(int os:{0,1}){
 auto s=state(os);AlignedWet a,b,dry,wet;StaticProcessor ref;
 if(!a.prepare(s,rate,127)||!b.prepare(s,rate,512)||!dry.prepare(s,rate,127,0)||!wet.prepare(s,rate,512)||!ref.prepare(s,rate))return 1;
 int delay=a.latency();if(delay<0||b.latency()!=delay||ref.latency()!=delay)return 2;
 const int n=24000;std::vector<float> l(n),r(n);for(int i=0;i<n;++i){l[i]=.25f*std::sin(i*.036f);r[i]=.17f*std::sin(i*.021f);}
 auto x=l,y=r,u=l,v=r,dl=l,dr=r,wl=l,wr=r,rl=l,rr=r;
 if(a.setWet(std::numeric_limits<float>::quiet_NaN())||a.setWet(-1.f))return 3;
 tracking=true;
 // Identical sample-position automation with differing internal and host blocks.
 auto run=[&](AlignedWet& p,std::vector<float>& xx,std::vector<float>& yy,int bs){for(int start=0;start<n;){int stop=start<4000?4000:start<12000?12000:n;if(start==4000&&!p.setWet(0.f))return false;if(start==12000&&!p.setWet(1.f))return false;int k=std::min(bs,stop-start);if(!p.process(xx.data()+start,yy.data()+start,k))return false;start+=k;}return true;};
 if(!run(a,x,y,127)||!run(b,u,v,512)||!dry.process(dl.data(),dr.data(),n)||!wet.process(wl.data(),wr.data(),n)||!ref.process(rl.data(),rr.data(),n))return 4;
 tracking=false;if(allocations)return 5;
 for(int i=0;i<n;++i){if(!std::isfinite(x[i])||!std::isfinite(y[i])||x[i]!=u[i]||y[i]!=v[i]||wl[i]!=rl[i]||wr[i]!=rr[i])return 6;
 float wantL=i>=delay?l[i-delay]:0.f,wantR=i>=delay?r[i-delay]:0.f;if(dl[i]!=wantL||dr[i]!=wantR)return 7;
 if(i>=4000+int(std::round(rate*.01))&&i<12000&&(x[i]!=wantL||y[i]!=wantR))return 8;
 if(i>=12000+int(std::round(rate*.01))&&(x[i]!=wl[i]||y[i]!=wr[i]))return 9;
 }
 std::printf("rate %.0f os %d latency %d wet/dry exact; automated block exact; allocations %zu\n",rate,os,delay,allocations);++checks;
 }std::printf("%d latency-aligned wet/bypass cases passed\n",checks);}
