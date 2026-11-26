/* SPDX-License-Identifier: GPL-3.0-or-later
 * At the measured password-submit boundary, expand an English alias into the
 * original key read from this player's live MES and glyph table. The original
 * comparison, unlock flags, reward checks, duplicates and save code still run. */
#include "recomp.h"
#include <stdio.h>
#include <stdlib.h>
#include "password_alias.h"
void loa_password_translate(uint32_t object){
    if(!sr_guest_span_readable(object,0x2b0u)||!sr_guest_span_writable(object+4u,64u))return;
    uint16_t input[32],original[32];unsigned n=0;
    while(n<32&&(input[n]=MEM_R16(object+4u+2u*n))!=0)n++;
    int index=loa_password_alias_index(input,n);if(index<0)return;
    uint32_t mes=MEM_R32(object+0x2acu);
    if(!sr_guest_span_readable(mes,12u)||MEM_R32(mes)!=0x53454d2eu||MEM_R32(mes+4u)!=1u||MEM_R32(mes+8u)!=28u)return;
    if(!sr_guest_span_readable(mes+12u+4u*(unsigned)index,4u))return;
    uint32_t offset=MEM_R32(mes+12u+4u*(unsigned)index);
    if(offset<124u||offset>0x10000u||!sr_guest_span_readable(mes+offset,10u))return;
    uint32_t message=mes+offset;unsigned words=MEM_R16(message+8u);
    if(words<2||words>32||!sr_guest_span_readable(message+10u,2u*words)||MEM_R16(message+8u+2u*words)!=0xffffu)return;
    /* Measured glyph decoder object: .codes at +fc, count at +100. These are
     * checked on every submit, never cached across a title resource load. */
    uint32_t glyph_object=0x08d1be68u;
    if(!sr_guest_span_readable(glyph_object+0xfcu,8u))return;
    uint32_t glyphs=MEM_R32(glyph_object+0xfcu),count=MEM_R32(glyph_object+0x100u);
    if(!count||count>65535||!sr_guest_span_readable(glyphs,2u*count))return;
    for(unsigned i=0;i<words-1;i++){
        unsigned code=MEM_R16(message+10u+2u*i);
        if(!code||code>=count)return;
        original[i]=MEM_R16(glyphs+2u*code);
        if(!original[i]||original[i]==0xffffu)return;
    }
    original[words-1]=0;
    /* Complete validation precedes any writes. No reward or status is invented. */
    for(unsigned i=0;i<32;i++)MEM_W16(object+4u+2u*i,i<words?original[i]:0);
    if(getenv("LOA_PASSWORD_TRACE"))fprintf(stderr,"LOA_PASSWORD: translated alias message=%d units=%u\n",index,words-1);
}
