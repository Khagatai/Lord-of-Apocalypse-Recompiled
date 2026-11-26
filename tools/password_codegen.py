"""English password aliases only at the measured main-menu submit boundary."""
START=0x08c9f680
PC=0x08c9f6bc
WORD=0x34040000

def rewrite(lines,start):
    if start!=START:return lines
    text='\n'.join(lines)
    token=f'sr_begin(s, 0x{PC:08x}u, 0x{WORD:08x}u);'
    if text.count(token)!=1:raise ValueError('Password submit boundary changed')
    text=text.replace(token,'loa_password_translate(s->r[16]);\n    '+token)
    result=text.split('\n');result.insert(1,'    extern void loa_password_translate(uint32_t);');return result

def install(codegen):
    original=codegen.emit_function
    def emit(elf,start,*args,**kwargs):
        lines=original(elf,start,*args,**kwargs)
        return lines if codegen.ADDRESS_SPACE.runtime_module else rewrite(lines,start)
    codegen.emit_function=emit
