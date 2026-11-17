"""Build a private candidate MES bundle; does not modify archives or launchers."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import GlyphTable
from mes_edits import apply_edits, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--glyph-table", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    manifest_raw = args.manifest.read_bytes()
    manifest = json.loads(manifest_raw)
    source = args.source.read_bytes()
    glyph_raw = args.glyph_table.read_bytes()
    target = apply_edits(source, GlyphTable.parse(glyph_raw), manifest)
    output.mkdir(parents=True)
    (output / "candidate.MES").write_bytes(target)
    report = {"status": "candidate-not-installed-requires-in-game-review",
              "translation_complete": False, "resource_id": manifest["resource_id"],
              "edited_messages": len(manifest["entries"]),
              "source_sha256": digest(source), "candidate_sha256": digest(target),
              "manifest_sha256": digest(manifest_raw), "glyph_table_sha256": digest(glyph_raw),
              "source_unchanged": args.source.read_bytes() == source,
              "structural_roundtrip": "exact", "unchanged_blocks": "exact"}
    if not report["source_unchanged"]:
        raise ValueError("Source changed during candidate generation")
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
