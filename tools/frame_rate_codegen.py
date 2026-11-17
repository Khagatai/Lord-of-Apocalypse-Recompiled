"""Title-owned, opt-in timing seams emitted from the pinned original instructions.

Timing sites identified by LunaMoo's NPJH-50503 patch (PPSSPP forum post #297):
https://forums.ppsspp.org/showthread.php?pid=104163&tid=4799
No guest code or movie data is copied into this source module.
"""

SITES={0x08cb3cc4: (0x08cb3ddc,0x00000000),
       0x08cb3f3c: (0x08cb3f8c,0x1480000a)}


def rewrite(lines,start):
    if start not in SITES:return lines
    text='\n'.join(lines)
    pc,word=SITES[start]
    token=f'sr_begin(s, 0x{pc:08x}u, 0x{word:08x}u);'
    if text.count(token)!=1:raise ValueError('Timing site instruction identity changed')
    if start==0x08cb3cc4:
        old=token+' (void)0; sr_end(s, 0u, 0);'
        new=(token+' if (loa_fps_update(s, s->r[16], MEM_R32(s->r[16]+0x44u))) { '
             'float _a=s->f[22]; s->f[22]=sr_fpu_div_s(_a,_a,s->fcr31); } sr_end(s, 0u, 0);')
        declaration='    extern int loa_fps_update(CpuState *, uint32_t, uint32_t); extern int loa_fps_movie_restore(void);'
        label='  L_08cb3d20: ;'
        if text.count(label)!=1:raise ValueError('Timing loop identity changed')
        text=text.replace(label,label+'\n    if (loa_fps_movie_restore()) s->fi[22]=0x40000000u;')
    else:
        old='{ uint32_t _c = (s->r[4] != 0u);\n      '+token
        new='{ uint32_t _c = (s->r[4] != 0u) && !(loa_fps_enabled() && MEM_R32(0x08d18ae0u)==0u);\n      '+token
        declaration='    extern int loa_fps_enabled(void);'
    if text.count(old)!=1:raise ValueError('Timing emitter contract changed')
    text=text.replace(old,new)
    result=text.split('\n');result.insert(1,declaration)
    return result


def install(codegen):
    original=codegen.emit_function
    def emit(elf,start,*args,**kwargs):
        result=original(elf,start,*args,**kwargs)
        return result if codegen.ADDRESS_SPACE.runtime_module else rewrite(result,start)
    codegen.emit_function=emit
