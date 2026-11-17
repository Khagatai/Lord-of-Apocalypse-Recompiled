"""Capture bounded, private PPSSPP software-reference boot images; no acceptance pass."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title
import save_storage

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--language", choices=("japanese", "english-v16"), default="japanese")
    parser.add_argument("--candidate-report", type=Path, help="Explicit private translation-image build report; diagnostics only")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--press-script", help="Explicit PPSSPP emulated-time button schedule")
    parser.add_argument("--save-fixture", type=Path, help="Copy a memstick for independent load validation")
    args = parser.parse_args()
    candidate_report_hash = None
    if args.candidate_report:
        if args.language != "english-v16":
            parser.error("Translation candidates require --language english-v16")
        from translation_candidate import verify
        digest, candidate_report_hash = verify(args.image, args.candidate_report)
    else:
        digest = title.verify_disc_image(args.image, args.language)
    source = ROOT / "private/tools/ppsspp"
    revision = subprocess.check_output(["git", "-c", f"safe.directory={source.as_posix()}",
                                       "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != title.CONFIG["tools"]["ppsspp"]["commit"]:
        raise ValueError("PPSSPP source pin differs")
    executable = source / "Windows/x64/Release/PPSSPPHeadless.exe"
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh output directory under private/")
    output.mkdir()
    memstick = output / "memstick"
    fixture_hashes = save_storage.tree_hashes(args.save_fixture) if args.save_fixture else None
    if args.save_fixture:
        shutil.copytree(args.save_fixture, memstick)
    else:
        memstick.mkdir()
    times = (0.5, 1, 2, 3, 5, 8, 12, 18, 24)
    snapshots = [(t, output / f"oracle-{t:g}s.png") for t in times]
    command = [str(executable), str(args.image.resolve()), "--cpu=interpreter", "--graphics=software",
               "--timeout-wall=30", "--timeout-emulated=25", "--log",
               f"--memstick={memstick}", f"--appendconfig={ROOT / 'config/oracle.ini'}",
               "--screenshot-at=" + ",".join(f"{t:g}:{path}" for t, path in snapshots)]
    if args.press_script:
        command.append("--press=" + args.press_script)
    terminated = False
    with (output / "ppsspp.log").open("wb") as log:
        process = subprocess.Popen(command, cwd=source, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=35)
        except subprocess.TimeoutExpired:
            terminated = True
            process.terminate()
            code = process.wait(timeout=10)
    report = {"scope": "software-boot-image-reference-only", "boot_validated": False,
              "language": args.language,
              "translation_candidate_report_sha256": candidate_report_hash,
              "command": command, "ppsspp_revision": revision, "image_sha256": digest,
              "oracle_executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "returncode": code, "harness_terminated_child": terminated,
              "save_fixture_files_sha256": fixture_hashes,
              "save_fixture_source_unchanged": save_storage.tree_hashes(args.save_fixture) == fixture_hashes if args.save_fixture else None,
              "snapshots": [{"requested_emulated_seconds": t, "file": path.name,
                             "captured": path.is_file(),
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}
                            for t, path in snapshots]}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"returncode": code, "captured_images": sum(p.is_file() for _, p in snapshots),
                      "boot_validated": False, "harness_terminated_child": terminated}, indent=2))

if __name__ == "__main__":
    main()
