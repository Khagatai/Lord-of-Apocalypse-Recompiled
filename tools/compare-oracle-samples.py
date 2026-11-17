"""Check repeatability of two raw oracle samples; never a native correctness gate."""
import argparse
import json
from pathlib import Path

def load(root, name):
    return json.loads((root / name).read_text())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    args = parser.parse_args()
    left, right = (load(p, "initial-state.json") for p in (args.first, args.second))
    a, b = (load(p, "debugger-steps.json") for p in (args.first, args.second))
    def normalized(steps):
        return [{"pc": s["pc"], "opcode": s["opcode"],
                 "before": s["before"]["categories"], "after": s["after"]["categories"]} for s in steps]
    checks = {
        "nonempty_equal_step_count": len(a) > 0 and len(a) == len(b),
        "image_identity": left["image_sha256"] == right["image_sha256"],
        "executable_identity": left["executable_sha256"] == right["executable_sha256"],
        "initial_registers": left["registers"]["categories"] == right["registers"]["categories"],
        "modules": left["modules"]["modules"] == right["modules"]["modules"],
        "threads": left["threads"]["threads"] == right["threads"]["threads"],
        "argument": left.get("argument_hex") == right.get("argument_hex"),
        "sampled_register_transitions": normalized(a) == normalized(b),
    }
    print(json.dumps({"oracle_repeatability_only": checks, "debugger_steps": len(a),
                      "memory_write_deltas_compared": False, "native_code_compared": False}, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
