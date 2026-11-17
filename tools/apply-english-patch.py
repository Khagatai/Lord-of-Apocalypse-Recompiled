"""Apply the exact local v1.6 PSP patch privately and compare disc file identities."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CONFIG = tomllib.loads((ROOT / "config/lordofapocalypse.toml").read_text())
PATCH_SHA256 = "4f344ff39ccfea127272b32bbdf17844fdb0e1013bb2e9b40f1f3fa1c07c2ae7"
DECODER_SHA256 = "d81f59b2fe5e8589c0ee9782e231c805084f4d23dfade413903a4cad63b4e342"
spec = importlib.util.spec_from_file_location("disc_survey", ROOT / "tools/survey-disc.py")
survey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(survey)

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def file_hash(iso, extent):
    result = hashlib.sha256()
    position, remaining = extent["lba"] * survey.SECTOR, extent["size"]
    while remaining:
        length = min(remaining, 1024 * 1024)
        result.update(iso.read(position, length))
        position += length
        remaining -= length
    return result.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT.parent / "Lord of Apocalypse (Japan).iso")
    parser.add_argument("--patch", type=Path, default=ROOT.parent / "v1.6_2020.12.28/v1.6_2020.12.28.xdelta3")
    parser.add_argument("--output", type=Path, default=ROOT / "private/translation/v1.6")
    args = parser.parse_args()
    decoder = ROOT / "private/tools/xdelta/xdelta3.exe"
    for path, expected in ((args.input, CONFIG["disc"]["iso_sha256"]),
                           (args.patch, PATCH_SHA256), (decoder, DECODER_SHA256)):
        if digest(path) != expected:
            raise ValueError(f"Identity mismatch: {path.name}")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh output directory under private/")
    output.mkdir(parents=True)
    image = output / "LordOfApocalypse-English-v1.6.iso"
    command = [str(decoder), "-d", "-s", str(args.input.resolve()), str(args.patch.resolve()), str(image)]
    with (output / "patch.log").open("wb") as log:
        run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    report = {"patch_sha256": PATCH_SHA256, "decoder_sha256": DECODER_SHA256,
              "source_sha256": CONFIG["disc"]["iso_sha256"], "command": command,
              "returncode": run.returncode, "status": "PATCH_FAILED"}
    report_path = output / "comparison.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if run.returncode:
        raise RuntimeError(f"Patch decoder refused input; see {output / 'patch.log'}")
    report.update({"source_unchanged": digest(args.input) == CONFIG["disc"]["iso_sha256"],
                   "patched_iso_size": image.stat().st_size, "patched_iso_sha256": digest(image)})
    if not report["source_unchanged"]:
        raise RuntimeError("Original ISO changed during patching")
    with args.input.open("rb") as a, image.open("rb") as b:
        original, patched = survey.ISO(a), survey.ISO(b)
        left, right = original.files(), patched.files()
        sfo = right["PSP_GAME/PARAM.SFO"]
        metadata = survey.sfo(patched.read(sfo["lba"] * survey.SECTOR, sfo["size"]))
        if metadata["DISC_ID"] != CONFIG["disc"]["id"]:
            raise ValueError("Patched image disc ID differs")
        changes = []
        for name in sorted(left.keys() | right.keys()):
            old, new = left.get(name), right.get(name)
            old_hash = file_hash(original, old) if old else None
            new_hash = file_hash(patched, new) if new else None
            if old != new or old_hash != new_hash:
                changes.append({"path": name, "original": old, "patched": new,
                                "original_sha256": old_hash, "patched_sha256": new_hash,
                                "content_changed": old_hash != new_hash})
        for label, iso, files in (("japanese", original, left), ("english-v16", patched, right)):
            directory = output / "archives" / label
            directory.mkdir(parents=True)
            for suffix in ("RZL", "RZP"):
                extent = files[f"PSP_GAME/USRDIR/UPDATA/REGFILE.{suffix}"]
                with (directory / f"REGFILE.{suffix}").open("wb") as stream:
                    position, remaining = extent["lba"] * survey.SECTOR, extent["size"]
                    while remaining:
                        length = min(remaining, 1024 * 1024)
                        stream.write(iso.read(position, length))
                        position += length
                        remaining -= length
    main_changed = any(c["path"] == "PSP_GAME/SYSDIR/EBOOT.BIN" and c["content_changed"] for c in changes)
    report.update({"status": "PATCHED_AND_SURVEYED_ONLY", "disc": metadata,
                   "original_file_count": len(left), "patched_file_count": len(right),
                   "changes": changes, "main_executable_changed": main_changed,
                   "native_compatibility": "NOT_VALIDATED", "translation_completeness": "NOT_MEASURED"})
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("command", "changes")}, indent=2))
    print("Changed content: " + ", ".join(c["path"] for c in changes if c["content_changed"]))

if __name__ == "__main__":
    main()
