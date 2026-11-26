/* SPDX-License-Identifier: GPL-3.0-or-later
 * Preserve the original fatal error, adding local context for load-time faults.
 * This never repairs a pointer, skips a guest call or changes a PSP result. */
#include "recomp.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void local_words(const char *owner,uint32_t address) {
    /* RAM only: diagnostic reads must not touch device/VRAM registers. Raw words
     * stay in the private log and are excluded from exported bug reports. */
    if(!g_mem || address<0x08800000u || address>0x09ffffe0u || (address&3u))return;
    fprintf(stderr,"LOA_COOP_MEMORY: %s address=%08x",owner,address);
    for(unsigned i=0;i<8;i++){
        uint32_t word;memcpy(&word,SR_HOST_LINEAR(address+4*i),4);
        fprintf(stderr," word%u=%08x",i,word);
    }
    fputc('\n',stderr);
}

__attribute__((noreturn)) void __real_sr_null_code_pointer(CpuState *,uint32_t);
__attribute__((noreturn,cold)) void __wrap_sr_null_code_pointer(CpuState *s,uint32_t pc) {
    const char *rate=getenv("LOA_GAMEPLAY_FPS");
    fprintf(stderr,"LOA_COOP_FAULT: pc=0x%08x ra=0x%08x sp=0x%08x uid=0x%x vblank=%u fps=%d a0=0x%08x a1=0x%08x a2=0x%08x s0=0x%08x s1=0x%08x\n",
        pc,s->r[31],s->r[29],sched_current_uid(),sr_display_vcount(),rate&&!strcmp(rate,"60")?60:30,
        s->r[4],s->r[5],s->r[6],s->r[16],s->r[17]);
    local_words("argument",s->r[4]);local_words("owner",s->r[17]);
    fflush(stderr);
    __real_sr_null_code_pointer(s,pc);
}
