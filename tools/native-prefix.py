"""Compare a bounded native integer entry prefix against observed PPSSPP deltas."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title

def main():
    revision = title.verify_inputs()
    build = title.BUILD
    executable = build / "lordofapocalypse.exe"
    reference = ROOT / "private/oracle-prefix/entry-prefix.trace"
    if not executable.is_file() or not reference.is_file():
        raise FileNotFoundError("Build the title and export the PPSSPP entry-prefix trace first")
    output = ROOT / "private/native-prefix"
    if output.exists():
        raise ValueError("Archive the previous private/native-prefix run before repeating")
    output.mkdir()
    window = output / "window.trace"
    env = title.environment()
    env.update({"SR_HEADLESS": "1", "SR_TRACE_PC": "0x08804000:0x08ffffff",
                "SR_TRACE_LIMIT": "14", "SR_TRACE": str(window)})
    command = [str(executable), "--image", str(build / "lordofapocalypse_image.bin"),
               "08804000", "08be596c", str(reference), str(output / "full.trace")]
    reached = False
    terminated = False
    with (output / "native.log").open("wb") as log:
        process = subprocess.Popen(command, cwd=title.FRAMEWORK, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while process.poll() is None and time.monotonic() < deadline:
                if window.is_file() and "# window complete records=14" in window.read_text(errors="replace"):
                    reached = True
                    break
                full = output / "full.trace"
                if full.exists() and full.stat().st_size > 8 * 1024 * 1024:
                    raise RuntimeError("Diagnostic trace exceeded 8 MiB without the expected bounded window")
                time.sleep(0.01)
            if window.is_file() and "# window complete records=14" in window.read_text(errors="replace"):
                reached = True
        finally:
            if process.poll() is None:
                terminated = True
                process.terminate()
            process.wait(timeout=10)
    if not reached:
        raise RuntimeError("Native entry prefix was not reached; inspect private/native-prefix/native.log")
    # No native failures are suppressed. Only the explicitly bounded prefix is
    # compared; the harness terminates its child and makes no boot/HLE claim.
    records = [line for line in window.read_text().splitlines() if re.match(r"^\d+ pc=", line)]
    if len(records) != 14:
        raise ValueError(f"Expected 14 native records, got {len(records)}")
    native = output / "native-prefix.trace"
    native.write_text("# psp-recomp trace v1 target=loa-entry-prefix oracle=recomp\n" + "\n".join(records) + "\n")
    command = [str(title.PYTHON), str(title.FRAMEWORK / "tools/tracediff.py"), str(reference), str(native)]
    with (output / "comparison.log").open("w") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    report = {"framework_commit": revision, "instructions": 14,
              "codegen_adapter_sha256": title.CONFIG["runtime"]["codegen_adapter_sha256"],
              "register_and_memory_delta_match": result.returncode == 0,
              "scope": "integer-entry-prefix-before-first-syscall", "boot_validated": False,
              "child_terminated_at_diagnostic_checkpoint": terminated,
              "native_process_returncode": process.returncode}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if result.returncode:
        raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
