"""Bound the measured quest-start roster-name conversion, including old saves.

Only the call returning to 0884b4d8 has the measured 18-byte output buffer.
Other callers keep the original conversion. No PSP imports are intercepted.
"""
FUNCTION = 0x08c0b414
PARTY_RETURN = 0x0884b4d8
BUFFER_BYTES = 18


def rewrite(lines, start):
    if start != FUNCTION:
        return lines
    text = '\n'.join(lines)
    for token in ('sr_begin(s, 0x08c0b414u, 0x27bdffe0u);',
                  'sr_begin(s, 0x08c0b474u, 0xa6240000u);',
                  'sr_begin(s, 0x08c0b48cu, 0xa6240000u);'):
        if text.count(token) != 1:
            raise ValueError('Companion name conversion instruction identity changed')
    entry = '    uint32_t _sp_entry = s->r[29]; (void)_sp_entry;'
    loop = '  L_08c0b448: ;'
    if text.count(entry) != 1 or text.count(loop) != 1:
        raise ValueError('Companion name conversion emitter contract changed')
    text = text.replace(entry, entry + '\n'
        '    const uint32_t _loa_name_base = s->r[6];\n'
        f'    const int _loa_party_name = s->r[31] == 0x{PARTY_RETURN:08x}u;')
    text = text.replace(loop, loop + '\n'
        '    if (_loa_party_name && (uint32_t)(s->r[17] - _loa_name_base) >= 16u) {\n'
        '        s->r[17] = _loa_name_base + 16u;\n'
        '        goto L_08c0b488; /* original FFFF terminator, within the 18-byte field */\n'
        '    }')
    return text.split('\n')


def install(codegen):
    original = codegen.emit_function
    def emit(elf, start, *args, **kwargs):
        result = original(elf, start, *args, **kwargs)
        return result if codegen.ADDRESS_SPACE.runtime_module else rewrite(result, start)
    codegen.emit_function = emit
