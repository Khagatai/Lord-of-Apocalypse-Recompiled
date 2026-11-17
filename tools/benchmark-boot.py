"""Sequential deterministic CPU-presenter A/B; not a gameplay FPS benchmark."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vblanks", type=int, choices=range(300, 1501), default=1000)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    output.mkdir()
    results = []
    for profile in ("diagnostic", "release"):
        folder = output / profile
        command = [sys.executable, str(ROOT / "tools/diagnostic-boot.py"), str(args.image.resolve()),
                   "--output", str(folder), "--profile", profile, "--seconds", "30",
                   "--offscreen-frames", "--frame-window", f"{args.vblanks-10}-{args.vblanks}", "--perf",
                   "--deterministic", "--exit-vblank", str(args.vblanks)]
        start = time.monotonic()
        subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        report = json.loads((folder / "result.json").read_text())
        if report["timed_out"] or report["returncode"] != 0:
            raise RuntimeError(f"{profile} did not complete the diagnostic; no speed verdict")
        log = (folder / "native.log").read_text(errors="replace")
        performance = json.loads((folder / "perf.json").read_text())
        exits = re.findall(r"BOOT_EVENT phase=exit_at_vblank vblanks=(\d+)", log)
        if not exits:
            raise ValueError("Missing explicit VBLANK diagnostic exit")
        images = list(folder.glob("frame_v*.ppm"))
        latest = max(images, key=lambda p: int(p.stem[7:])) if images else None
        results.append({"profile": profile, "process_wall_seconds": time.monotonic() - start,
                        "vblanks": int(exits[-1]), "runtime_wall_ms": performance["wall_ns"] / 1e6,
                        "aot_ms": performance["guest"]["aot_ns"] / 1e6,
                        "last_frame": latest.name if latest else None,
                        "last_frame_sha256": hashlib.sha256(latest.read_bytes()).hexdigest() if latest else None,
                        "executable_sha256": report["executable_sha256"]})
    report = {"scope": f"deterministic-boot-{args.vblanks}-vblank-software-presenter-only",
              "gameplay_fps_validated": False, "runs": results,
              "last_captured_frames_identical": bool(results[0]["last_frame_sha256"]) and
                  results[0]["last_frame_sha256"] == results[1]["last_frame_sha256"]}
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
