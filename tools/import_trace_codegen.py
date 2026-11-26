# SPDX-License-Identifier: GPL-3.0-or-later
"""Title CODEGEN_TOOL adapter repairing import trace boundaries and emitting timing seams.

The pinned upstream import emitter calls sr_end without sr_begin, attributing
the syscall to the previous delay slot. Add trace hooks during generation and
conditional 60 FPS timing and optional camera seams; never edit generated C or suppress a PSP error.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / "external/nakagawa-recomp/tools"))
import codegen

ORIGINAL_IMPORT_EMITTER = codegen.import_stub_text

def traced_import(addr, lib, nid, lle_import_seam=None, *, options=None):
    body = ORIGINAL_IMPORT_EMITTER(addr, lib, nid, lle_import_seam, options=options)
    head, separator, rest = body.partition("\n")
    if not separator or "/* import:" not in head:
        raise ValueError("Pinned import emitter contract changed")
    instruction = codegen.G(addr)
    syscall = codegen.G(addr + 4)
    hooks = (f"    sr_begin(s, {instruction}, MEM_R32({instruction}));\n"
             "    sr_end(s, 0u, 0);\n"
             f"    sr_begin(s, {syscall}, MEM_R32({syscall}));\n")
    return head + separator + hooks + rest

def main():
    import frame_rate_codegen
    frame_rate_codegen.install(codegen)
    import camera_codegen
    camera_codegen.install(codegen)
    import password_codegen
    password_codegen.install(codegen)
    import companion_name_codegen
    companion_name_codegen.install(codegen)
    codegen.import_stub_text = traced_import
    return codegen.main(sys.argv)

if __name__ == "__main__":
    raise SystemExit(main())
