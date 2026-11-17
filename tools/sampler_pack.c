/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host-only replacement namespace: sampler context never changes PSP state. */
static int s_loa_sampler_pack;
static uint32_t loa_sampler_tag(uint32_t wrap) {
    return 0x4c4f4100u | (wrap&1u) | ((wrap>>7)&2u);
}
static int loa_sampler_lookup(NkTexRepl *pack,NkTexReplId *id,NkTexReplHit *hit,uint32_t wrap) {
    if(s_loa_sampler_pack) {
        NkTexReplId tagged=*id;
#ifdef LOA_WRAP_MUTANT_IGNORE_SAMPLER
        wrap=0;
#endif
        /* Direct-colour formats omit CLUT identity from the reader's key. */
        tagged.hash^=loa_sampler_tag(wrap);
        if(nk_texrepl_lookup(pack,&tagged,hit)) { *id=tagged;return 1; }
    }
    /* Legacy UI and existing packs retain their ordinary identity. */
    return nk_texrepl_lookup(pack,id,hit);
}
