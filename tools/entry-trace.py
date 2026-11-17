"""Export only the observed integer entry prefix before its first syscall.

This deliberately refuses other instruction classes rather than fabricating
memory or coprocessor deltas. Raw samples and output must remain private.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    args = parser.parse_args()
    directory = args.sample.resolve()
    if not directory.is_relative_to(ROOT / "private"):
        parser.error("Sample/output must stay under private/")
    initial = json.loads((directory / "initial-state.json").read_text())
    steps = json.loads((directory / "debugger-steps.json").read_text())
    category = next(c for c in initial["registers"]["categories"] if c["id"] == 0)
    registers = category["uintValues"]
    seed = [f"r{i}=0x{registers[i]:08x}" for i in range(1, 32)]
    seed += [f"hi=0x{registers[33]:08x}", f"lo=0x{registers[34]:08x}"]
    lines = ["# psp-recomp trace v1 target=loa-entry-prefix oracle=ppsspp", "# init " + " ".join(seed)]
    count = 0
    for step in steps:
        opcode = step["opcode"]
        if opcode >> 26 == 0 and opcode & 0x3f == 0xc:
            break
        # Prefix scope: ordinary integer ALU, jumps, LUI/ORI and aligned SW.
        if opcode >> 26 not in (0, 2, 3, 9, 13, 15, 0x2b):
            raise ValueError("Instruction outside reviewed entry-prefix trace scope")
        if not step.get("prefix_store_capture_enabled"):
            raise ValueError("Actual memory-write capture is required")
        before = step["before"]["categories"]
        after = step["after"]["categories"]
        if before[1:] != after[1:]:
            raise ValueError("Coprocessor delta outside integer-prefix scope")
        a = next(c for c in before if c["id"] == 0)["uintValues"]
        b = next(c for c in after if c["id"] == 0)["uintValues"]
        changes = [f"r{i}=0x{b[i]:08x}" for i in range(1, 32) if a[i] != b[i]]
        for i, name in ((33, "hi"), (34, "lo")):
            if a[i] != b[i]:
                changes.append(f"{name}=0x{b[i]:08x}")
        writes = step["observed_memory_writes"]
        if (opcode >> 26 == 0x2b) != (len(writes) == 1):
            raise ValueError("Missing or unexpected observed store")
        for write in sorted(writes, key=lambda w: w["address"]):
            changes.append(f"m32[0x{write['address']:08x}]=0x{write['value']:08x}")
        lines.append(f"{count} pc=0x{step['pc']:08x} op=0x{opcode:08x}" + (" " + " ".join(changes) if changes else ""))
        count += 1
    if count != 14:
        raise ValueError(f"Expected the reviewed 14-instruction prefix, observed {count}")
    (directory / "entry-prefix.trace").write_text("\n".join(lines) + "\n")
    print(f"Exported {count} observed instructions including register and SW memory deltas; no native comparison yet.")

if __name__ == "__main__":
    main()
