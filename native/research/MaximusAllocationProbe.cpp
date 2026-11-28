// Separate translation unit for the test allocator: keep compiler's
// allocation/deallocation pairing analysis independent of test vectors.
#include <cstddef>
#include <cstdlib>
#include <new>
bool tracking=false;
std::size_t allocations=0;
void* operator new(std::size_t n){if(tracking)++allocations;if(auto p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
