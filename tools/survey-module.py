"""Static metadata only: base zero denotes relative offsets, never a boot base."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "external/psp-recomp/tools"))
from analyze import Elf
from imports import parse_imports

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / "private"):
        parser.error("Detailed module reports must stay under private/")
    data = args.module.read_bytes()
    etype = struct.unpack_from("<H", data, 16)[0]
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    phoff, shoff, phsize, phnum, shnum = header[5], header[6], header[9], header[10], header[12]
    programs = [struct.unpack_from("<8I", data, phoff + i * phsize) for i in range(phnum)]
    # Retail PSP modules may have no sections. Do not hand these to the
    # framework's section-dependent analyzer or pretend type-B relocs ran.
    elf = Elf(str(args.module), base=0) if shnum else None
    relocations = Counter()
    sections = []
    for section in elf.sections if elf else []:
        if section["typ"] in (0x700000a0, 0x700000a1, 9, 4):
            sections.append({key: section[key] for key in ("nm", "typ", "size", "entsz")})
        if section["typ"] == 0x700000a0:
            if section["size"] % 8:
                raise ValueError("Invalid type-A relocation size")
            for offset in range(section["off"], section["off"] + section["size"], 8):
                r_offset, info = struct.unpack_from("<II", data, offset)
                relocations[info & 0xff] += 1
    mi_offset = programs[0][3] & 0x7fffffff
    mi = elf.sec(".rodata.sceModuleInfo") if elf else None
    if elf and not mi:
        mi = next((section for section in elf.sections
                   if section["off"] == mi_offset and section["size"] >= 52), None)
    module = None
    if mi or (not elf and mi_offset + 52 <= len(data)):
        info = elf.read_at_vaddr(mi["addr"], 52) if mi else data[mi_offset:mi_offset + 52]
        attr, version, name, gp, exp, expend, imp, impend = struct.unpack(
            "<HH28s5I", info)
        module = {"name": name.split(b"\0", 1)[0].decode("ascii"), "attributes": attr,
                  "version": version, "gp_relative": gp, "export_start_relative": exp,
                  "export_end_relative": expend, "import_start_relative": imp,
                  "import_end_relative": impend}
    imports = {}
    import_error = None
    if elf and mi:
        # Diagnostic alias only. The original decrypted ELF is never rewritten.
        # Upstream tools currently require this exact section name.
        original_name = mi["nm"]
        mi["nm"] = ".rodata.sceModuleInfo"
        try:
            imports = parse_imports(elf)
        finally:
            mi["nm"] = original_name
    else:
        import_error = "Sectionless ELF/type-B relocations not supported by pinned offline tools"
    report = {"sha1": hashlib.sha1(data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest(),
              "size": len(data), "elf_type": hex(etype), "elf_entry": hex(header[4]),
              "address_semantics": "module-relative" if etype == 0xffa0 else "ELF-linked",
              "measured_load_base": None, "measured_runtime_entry": None,
              "program_headers": [{"type": hex(p[0]), "file_offset": p[1], "vaddr_relative": p[2],
                                   "paddr": p[3], "file_size": p[4], "memory_size": p[5],
                                   "flags": p[6], "alignment": p[7]} for p in programs],
              "module_info_file_offset": mi_offset, "module": module,
              "relocation_sections": sections, "type_A_relocation_counts": dict(relocations),
              "import_error": import_error,
              "import_libraries": dict(Counter(lib for lib, nid in imports.values())),
              "imports": [{"stub_relative": hex(stub), "library": lib, "nid": hex(nid)}
                          for stub, (lib, nid) in sorted(imports.items())]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "imports"}, indent=2))

if __name__ == "__main__":
    main()
