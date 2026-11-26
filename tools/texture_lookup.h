/* SPDX-License-Identifier: GPL-3.0-or-later
 * Included after the pinned renderer's TexEnt/TexMipKey and cache globals.
 * Only cache an array index. Never cache pixels, content validity or descriptors. */
#define LOA_TEXTURE_HINT_COUNT 1024u
static unsigned loa_texture_hints[LOA_TEXTURE_HINT_COUNT];
static int loa_texture_lookup_enabled,loa_texture_lookup_verify;
static uint64_t loa_texture_hint_hits,loa_texture_searches,loa_texture_comparisons;

static void loa_texture_lookup_reset(void) {
    const char *mode=getenv("LOA_TEXTURE_LOOKUP");
    if(mode && strcmp(mode,"linear") && strcmp(mode,"cached")){
        fprintf(stderr,"LOA_TEXTURE_LOOKUP: invalid mode; use linear or cached\n");exit(1);
    }
    loa_texture_lookup_enabled=!mode || strcmp(mode,"linear");
    loa_texture_lookup_verify=getenv("LOA_TEXTURE_LOOKUP_VERIFY")!=NULL;
    memset(loa_texture_hints,0,sizeof loa_texture_hints);
    loa_texture_hint_hits=loa_texture_searches=loa_texture_comparisons=0;
}
static unsigned loa_texture_slot(uint64_t key) {
    key^=key>>33;key*=UINT64_C(0xff51afd7ed558ccd);key^=key>>33;
    return (unsigned)key&(LOA_TEXTURE_HINT_COUNT-1u);
}
static int loa_texture_linear(uint64_t key,const TexMipKey *mip) {
    for(int i=0;i<s_tex_n;i++){
        loa_texture_comparisons++;
        if(s_tex[i].key==key && !memcmp(&s_tex[i].mip,mip,sizeof *mip))return i;
    }
    return -1;
}
static int loa_texture_find(uint64_t key,const TexMipKey *mip) {
    unsigned slot=loa_texture_slot(key),hint=loa_texture_hints[slot];
    if(loa_texture_lookup_enabled && hint && hint<=(unsigned)s_tex_n){
        int index=(int)hint-1;const TexEnt *e=&s_tex[index];
        if(e->key==key && !memcmp(&e->mip,mip,sizeof *mip)){
            /* Entries are unique by this exact pair: tex_get updates an existing
             * pair in place and only appends after the complete search misses.
             * A compacted/reused slot must still pass the exact same comparison. */
            if(loa_texture_lookup_verify && loa_texture_linear(key,mip)!=index){
                fprintf(stderr,"LOA_TEXTURE_LOOKUP: cached index differs from original search\n");abort();
            }
            loa_texture_hint_hits++;return index;
        }
    }
    loa_texture_searches++;
    int found=loa_texture_linear(key,mip);
    if(loa_texture_lookup_enabled)loa_texture_hints[slot]=found<0?0u:(unsigned)found+1u;
    return found;
}
