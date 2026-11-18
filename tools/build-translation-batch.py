"""Apply multiple checked MES manifests to a separate private archive pair."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import Bundle, GlyphTable
from mes_edits import apply_edits, digest
from rgf_archive import parse_index, resources
from rgf_edits import append_edits
from companion_name_layout import fit_companion_names


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare_replacements(manifests, payloads, table):
    replacements, affected = {}, 0
    for manifest in manifests:
        identity = int(manifest["resource_id"], 16)
        key = identity, manifest["source_bundle_sha256"]
        if identity >> 16 != 4:
            raise ValueError("Translation batch may replace only MES resource kind 4")
        if key in replacements:
            raise ValueError("Duplicate resource variant manifest")
        if key not in payloads:
            raise ValueError("Requested resource variant not found")
        source = payloads[key]
        target = apply_edits(source, table, manifest)
        if identity == 0x400f9:
            target = fit_companion_names(target, table)
        if target == source:
            raise ValueError("Manifest contains no actual changes")
        bundle = Bundle.parse(source)
        after = Bundle.parse(target)
        if after.offsets != bundle.offsets:
            raise ValueError('Translation batch changed message aliases')
        changed_blocks = {index for index, (old, new) in enumerate(zip(bundle.blocks, after.blocks)) if old != new}
        affected += sum(block in changed_blocks for block in bundle.offsets)
        replacements[key] = target
    if not replacements:
        raise ValueError("Translation batch is empty")
    return replacements, affected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Private JSON containing a bundles list")
    parser.add_argument("--archives", type=Path, default=ROOT / "private/translation/archives/english-v16")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    from translation_baseline import ensure_archives
    args.archives=ensure_archives(args.archives)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    raw_manifest = args.manifest.read_bytes()
    manifests = json.loads(raw_manifest)["bundles"]
    wanted = {(int(m["resource_id"], 16), m["source_bundle_sha256"]) for m in manifests}
    originals = {name: file_hash(args.archives / name) for name in ("REGFILE.RZL", "REGFILE.RZP")}
    index = (args.archives / "REGFILE.RZL").read_bytes()
    groups = parse_index(index, (args.archives / "REGFILE.RZP").stat().st_size)
    payloads, glyph_tables = {}, set()
    with (args.archives / "REGFILE.RZP").open("rb") as stream:
        for _, identity, data in resources(stream, groups):
            if identity == 0x50d78:
                glyph_tables.add(data)
            if identity >> 16 == 4:
                key = identity, digest(data)
                if key in wanted:
                    payloads[key] = data
    if len(glyph_tables) != 1:
        raise ValueError("Expected one measured Unicode glyph-table variant")
    glyph_raw = glyph_tables.pop()
    replacements, affected = prepare_replacements(manifests, payloads, GlyphTable.parse(glyph_raw))
    output.mkdir(parents=True)
    messages = output / "messages"
    messages.mkdir()
    for (identity, before_hash), data in replacements.items():
        (messages / f"{identity:08x}-{before_hash[:16]}.MES").write_bytes(data)
    shutil.copyfile(args.archives / "REGFILE.RZP", output / "REGFILE.RZP")
    with (args.archives / "REGFILE.RZP").open("rb") as source, (output / "REGFILE.RZP").open("r+b") as target:
        rebuilt, checks = append_edits(index, source, target, replacements)
    (output / "REGFILE.RZL").write_bytes(rebuilt)
    if any(file_hash(args.archives / name) != value for name, value in originals.items()):
        raise ValueError("Source archive changed during generation")
    result = {"status": "candidate-not-installed-requires-in-game-review", "translation_complete": False,
              "scope": "text-only", "manifest_sha256": digest(raw_manifest),
              "glyph_table_sha256": digest(glyph_raw), "resource_id": None,
              "resource_ids": sorted({m["resource_id"] for m in manifests}),
              "edited_bundle_variants": len(replacements),
              "edited_messages": sum(len(m["entries"]) for m in manifests),
              "affected_message_entries": affected, **checks,
              "source_archives_sha256": originals, "source_unchanged": True,
              "candidate_archives_sha256": {name: file_hash(output / name) for name in originals}}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
