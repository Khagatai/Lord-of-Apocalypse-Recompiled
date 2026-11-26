"""Optional analog yaw before the original player camera computes its orbit."""
START=0x08872590
PC=0x08873324
WORD=0xc6b40000

def rewrite(lines,start):
    if start!=START:return lines
    text='\n'.join(lines)
    instruction=f'sr_begin(s, 0x{PC:08x}u, 0x{WORD:08x}u);'
    if text.count(instruction)!=1:raise ValueError('Player camera rotation boundary changed')
    text=text.replace(instruction,'loa_camera_update(s,s->r[16],s->r[19]);\n    '+instruction)
    result=text.split('\n');result.insert(1,'    extern void loa_camera_update(CpuState *,uint32_t,uint32_t);');return result

def install(codegen):
    original=codegen.emit_function
    def emit(elf,start,*args,**kwargs):
        lines=original(elf,start,*args,**kwargs)
        return lines if codegen.ADDRESS_SPACE.runtime_module else rewrite(lines,start)
    codegen.emit_function=emit
