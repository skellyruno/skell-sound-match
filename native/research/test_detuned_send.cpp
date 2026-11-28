#include "DetunedSend.h"
#include <limits>
#include <cstdio>
extern bool tracking;
extern std::size_t allocations;
using skellmatch::DetunedSend;
int main(){int tests=0;for(double sr:{44100.,48000.,96000.,192000.})for(double cents:{6.,24.,50.}){
 DetunedSend a,b;if(!a.prepare(sr,cents,40,3)||!b.prepare(sr,cents,40,3))return 1;
 const int n=int(sr*.5);std::vector<std::array<float,2>> x(n),y(n),z(n);for(int i=0;i<n;++i){x[i]={.4f*std::sin(.04f*i),.3f*std::cos(.053f*i)};}x[111][0]=std::numeric_limits<float>::infinity();x[222][1]=std::numeric_limits<float>::quiet_NaN();
 tracking=true;for(int i=0;i<n;i+=127)for(int j=i;j<std::min(i+127,n);++j)y[j]=a.process(x[j][0],x[j][1]);for(int i=0;i<n;i+=512)for(int j=i;j<std::min(i+512,n);++j)z[j]=b.process(x[j][0],x[j][1]);tracking=false;
 float pk=0;for(int i=0;i<n;++i)for(int ch=0;ch<2;++ch){if(!std::isfinite(y[i][ch])||y[i][ch]!=z[i][ch])return 2;if(i<int(sr*.003)&&y[i][ch]!=0)return 3;pk=std::max(pk,std::abs(y[i][ch]));}if(allocations||pk<.05f||pk>.41f)return 4;
 a.reset();for(int i=0;i<n;++i){auto s=a.process(0,0);if(s[0]!=0||s[1]!=0)return 5;}if(a.prepare(sr,0,40,3)||a.prepare(sr,6,101,3)||a.prepare(sr,6,40,41)||a.prepare(std::numeric_limits<double>::quiet_NaN(),6,40,3))return 6;++tests;
 }
 std::printf("PASS %d rate/detuning cases; block equality, causal onset, reset silence, invalid controls, finite handling, %zu intercepted allocations\n",tests,allocations);
}
