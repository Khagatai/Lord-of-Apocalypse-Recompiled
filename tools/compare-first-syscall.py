"""Compare the first syscall's GPR/HILO checkpoint, never a boot acceptance gate.

The separate 14-instruction prefix comparison must already have passed. PSP
import syscall encodings differ between runtimes, so this compares state at
that one measured PC and makes no opcode or kernel-trace equivalence claim.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title

def gpr(response):
    category = next(c for c in response["categories"] if c["id"] == 0)
    values = category["uintValues"]
    return {**{f"r{i}": values[i] for i in range(1, 32)}, "hi": values[33], "lo": values[34]}

def main():
    title.verify_inputs()
    oracle = ROOT / "private/oracle-entry-96"
    native = ROOT / "private/native-prefix"
    initial = json.loads((oracle / "initial-state.json").read_text())
    prefix_initial = json.loads((ROOT / "private/oracle-prefix/initial-state.json").read_text())
    prefix_result = json.loads((native / "result.json").read_text())
    build_record = json.loads((ROOT / "private/diagnostic-boot-30s/result.json").read_text())
    executable_hash = hashlib.sha256((title.BUILD / "lordofapocalypse.exe").read_bytes()).hexdigest()
    if executable_hash != build_record["executable_sha256"]:
        raise ValueError("Executable changed since the associated local diagnostic")
    for sample in (initial, prefix_initial):
        if sample["image_sha256"] != title.CONFIG["disc"]["iso_sha256"] or sample["ppsspp_revision"] != title.CONFIG["tools"]["ppsspp"]["commit"]:
            raise ValueError("Oracle identity differs")
    if initial["executable_sha256"] != prefix_initial["executable_sha256"]:
        raise ValueError("Oracle executable changed")
    if gpr(initial["registers"]) != gpr(prefix_initial["registers"]):
        raise ValueError("Oracle initial registers differ")
    if not prefix_result["register_and_memory_delta_match"] or prefix_result["instructions"] != 14:
        raise ValueError("Validated pre-syscall prefix required")
    steps = json.loads((oracle / "debugger-steps.json").read_text())
    syscall = next(s for s in steps if (s["opcode"] & 0xfc00003f) == 0x0c)
    if syscall["index"] != 14:
        raise ValueError("First syscall moved outside the validated prefix boundary")
    state = gpr(initial["registers"])
    records = (native / "window.trace").read_text().splitlines()
    records += (native / "full.trace").read_text().splitlines()
    parsed = [line for line in records if re.match(r"^\d+ pc=", line)]
    parsed.sort(key=lambda line: int(line.split()[0]))
    for index, line in enumerate(parsed[:15]):
        if int(line.split()[0]) != index:
            raise ValueError("Incomplete native prefix records")
        for key, value in re.findall(r"\b(r\d+|hi|lo)=0x([0-9a-fA-F]+)", line):
            state[key] = int(value, 16)
        expected = gpr(steps[index]["after"])
        if index < 14 and state != expected:
            raise ValueError("Native registers differ before the syscall under investigation")
    if len(parsed) < 15 or f"pc=0x{syscall['pc']:08x}" not in parsed[14]:
        raise ValueError("Native first-syscall checkpoint missing")
    differences = {key: {"ppsspp": f"0x{expected[key]:08x}", "native": f"0x{state[key]:08x}"}
                   for key in expected if expected[key] != state[key]}
    report = {"scope": "first-syscall-gpr-hilo-checkpoint-only", "boot_validated": False,
              "framework_commit": title.CONFIG["runtime"]["commit"],
              "native_executable_sha256": executable_hash,
              "oracle_executable_sha256": initial["executable_sha256"],
              "syscall_index": 14, "pc": f"0x{syscall['pc']:08x}",
              "state_match": not differences, "differences": differences,
              "notes": "No opcode, syscall memory-write, timing, or scheduler equivalence asserted"}
    (ROOT / "private/first-syscall-checkpoint.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(bool(differences))

if __name__ == "__main__":
    raise SystemExit(main())
