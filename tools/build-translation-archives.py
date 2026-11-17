"""Build verified private RGF archives from one checked MES candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from rgf_edits import append_edits, digest


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Directory from build-message-edits.py")
    parser.add_argument("--archives", type=Path, default=ROOT / "private/translation/archives/english-v16")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from translation_baseline import ensure_archives
    args.archives=ensure_archives(args.archives)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    report = json.loads((args.candidate / "result.json").read_text())
    candidate = (args.candidate / "candidate.MES").read_bytes()
    if digest(candidate) != report["candidate_sha256"]:
        raise ValueError("Candidate differs from its build report")
    originals = {name: file_hash(args.archives / name) for name in ("REGFILE.RZL", "REGFILE.RZP")}
    index = (args.archives / "REGFILE.RZL").read_bytes()
    output.mkdir(parents=True)
    shutil.copyfile(args.archives / "REGFILE.RZP", output / "REGFILE.RZP")
    with (args.archives / "REGFILE.RZP").open("rb") as source, (output / "REGFILE.RZP").open("r+b") as target:
        rebuilt, checks = append_edits(index, source, target, {
            (int(report["resource_id"], 16), report["source_sha256"]): candidate})
    (output / "REGFILE.RZL").write_bytes(rebuilt)
    unchanged = all(file_hash(args.archives / name) == value for name, value in originals.items())
    if not unchanged:
        raise ValueError("Source archive changed during generation")
    result = {"status": "candidate-not-installed-requires-in-game-review", "translation_complete": False,
              **checks, "source_archives_sha256": originals, "source_unchanged": unchanged,
              "candidate_archives_sha256": {name: file_hash(output / name) for name in originals},
              "resource_id": report["resource_id"], "edited_messages": report["edited_messages"]}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
