/* Read-only archive audit adapter. Uses the pinned runtime's real algorithms. */
#include "texrepl.h"
__declspec(dllexport) uint32_t loa_quick(const void *p,uint32_t n,uint32_t addr) {
    return nk_texrepl_quick_hash(p,n,addr);
}
__declspec(dllexport) uint32_t loa_clut(const void *p,uint32_t n,uint32_t cf,uint32_t tf) {
    return nk_texrepl_clut_identity(p,n,cf,tf,n,n);
}
__declspec(dllexport) uint64_t loa_key(uint32_t fmt,uint32_t dim,uint32_t ch) {
    return nk_texrepl_cache_key(0,fmt,dim,ch);
}
