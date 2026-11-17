"""Build a private translation ISO candidate; stable launchers remain pinned."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title
from iso_edits import append_files, extent_hash, survey


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    image = title.disc_image("english-v16")
    original_hash = title.verify_disc_image(image, "english-v16")
    report = json.loads((args.archives / "result.json").read_text())
    if report.get("all_resource_payloads_verified") is not True:
        raise ValueError("Archives lack completed resource verification")
    archive_hashes = report["candidate_archives_sha256"]
    for name in ("REGFILE.RZL", "REGFILE.RZP"):
        if file_hash(args.archives / name) != archive_hashes[name]:
            raise ValueError("Archive candidate differs from its report")
    with image.open("rb") as stream:
        files = survey.ISO(stream).files()
        for name in archive_hashes:
            record = files["PSP_GAME/USRDIR/UPDATA/" + name]
            if extent_hash(stream, record["lba"] * 2048, record["size"]) != report["source_archives_sha256"][name]:
                raise ValueError("Archive source differs from pinned English ISO")
    output.mkdir(parents=True)
    candidate = output / "LordOfApocalypse-English-WIP.iso"
    shutil.copyfile(image, candidate)
    with ExitStack() as stack:
        source = stack.enter_context(image.open("rb"))
        target = stack.enter_context(candidate.open("r+b"))
        replacements = {"PSP_GAME/USRDIR/UPDATA/" + name: stack.enter_context((args.archives / name).open("rb"))
                        for name in ("REGFILE.RZL", "REGFILE.RZP")}
        checks = append_files(source, target, replacements)
    if file_hash(image) != original_hash:
        raise ValueError("Source ISO changed during generation")
    result = {"status": "candidate-not-installed-requires-in-game-review", "translation_complete": False,
              "source_iso_sha256": original_hash, "source_unchanged": True,
              "candidate_iso_sha256": file_hash(candidate), "candidate_iso_size": candidate.stat().st_size,
              "resource_id": report["resource_id"],
              "resource_ids": report.get("resource_ids") or [report["resource_id"]],
              "edited_messages": report["edited_messages"],
              "affected_message_entries": report.get("affected_message_entries", report["edited_messages"]), **checks}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
