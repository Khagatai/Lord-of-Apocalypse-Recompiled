"""Check the selected loader against a measured PPSSPP main-image snapshot."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title
sys.path.insert(0, str(title.FRAMEWORK / "tools"))
from analyze import Elf
from imports import parse_imports
from prxload import Prx

def main():
    title.verify_inputs()
    module = ROOT / title.CONFIG["module"]["file"]
    base = title.CONFIG["module"]["base"]
    oracle_dir = ROOT / "private/oracle-image"
    snapshot = json.loads((oracle_dir / "initial-state.json").read_text())
    oracle = (oracle_dir / "main-image.bin").read_bytes()
    if hashlib.sha256(oracle).hexdigest() != snapshot["main_image_sha256"]:
        raise ValueError("Oracle image integrity mismatch")
    if snapshot["image_sha256"] != title.CONFIG["disc"]["iso_sha256"]:
        raise ValueError("Oracle disc identity mismatch")
    image = Prx(str(module), base)
    count = image.relocate()
    imports = parse_imports(Elf(str(module), base=base))
    # Only PSP loader-patched import delay-slot words may differ. Every other
    # byte, including code, relocated pointers, data and BSS, must match.
    expected = {stub + 4 + offset - base for stub in imports for offset in range(4)}
    for stub in imports:
        offset = stub + 4 - base
        instruction = int.from_bytes(oracle[offset:offset + 4], "little")
        if instruction >> 26 != 0 or instruction & 0x3f != 0x0c:
            raise ValueError("An excluded import word is not an observed PSP syscall patch")
    differences = [i for i, (a, b) in enumerate(zip(image.mem, oracle)) if a != b]
    unexpected = [i for i in differences if i not in expected]
    report = {"compared_bytes": len(image.mem), "oracle_bytes": len(oracle),
              "relocations": count, "different_bytes": len(differences),
              "unexpected_different_bytes": len(unexpected), "expected_hle_patch_stubs": len(imports),
              "verified_syscall_patch_words": len(imports),
              "unexpected_first_addresses": [hex(base + i) for i in unexpected[:16]]}
    (ROOT / "private/evaluation/nakagawa-image-comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if len(image.mem) != len(oracle) or unexpected:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
