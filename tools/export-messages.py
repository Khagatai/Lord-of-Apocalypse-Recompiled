"""Export a private, losslessly checked Japanese/English message inventory."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import Bundle, GlyphTable, Message
import rgf_archive

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, default=ROOT / "private/translation/archives")
    parser.add_argument("--output", type=Path, default=ROOT / "private/translation/messages")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    output.mkdir(parents=True)
    summaries = {}
    for name in ("japanese", "english-v16"):
        root = args.archives / name
        groups = rgf_archive.parse_index((root / "REGFILE.RZL").read_bytes(), (root / "REGFILE.RZP").stat().st_size)
        with (root / "REGFILE.RZP").open("rb") as stream:
            table_raw = next(data for _, identity, data in rgf_archive.resources(stream, groups) if identity == 0x50d78)
        table = GlyphTable.parse(table_raw)
        (output / f"{name}-glyph-table.bin").write_bytes(table_raw)
        stats, seen, controls = Counter(), set(), Counter()
        with (output / f"{name}.jsonl").open("w", encoding="utf-8") as rows, (root / "REGFILE.RZP").open("rb") as stream:
            for group, identity, data in rgf_archive.resources(stream, groups):
                if identity >> 16 != 4:
                    continue
                digest = hashlib.sha256(data).hexdigest()
                if (identity, digest) in seen:
                    continue
                seen.add((identity, digest))
                bundle = Bundle.parse(data)
                if bundle.build() != data:
                    raise ValueError(f"Bundle round trip differs: {identity:08x}")
                stats["bundle_variants_roundtrip_exact"] += 1
                for index, block in enumerate(bundle.offsets):
                    raw = bundle.blocks[block]
                    record = {"resource_id": f"{identity:08x}", "bundle_sha256": digest,
                              "first_group": group, "message_index": index, "block": block,
                              "raw_sha256": hashlib.sha256(raw).hexdigest()}
                    stats["message_entries"] += 1
                    try:
                        message = Message.parse(raw)
                        assert message.build() == raw
                        editable = message.editable(table)
                        record.update({"framing": "decoded", "editable_plain_text": editable,
                                       "header": message.header,
                                       "lines": [table.decode(line[:-1]) for line in message.lines]})
                        controls.update(f"{v:04x}" for line in message.lines for v in line[:-1] if v >= len(table.codes))
                        stats["framed_entries"] += 1
                        stats["plain_text_editable_entries" if editable else "entries_with_unresolved_inline_codes"] += 1
                    except ValueError as error:
                        record.update({"framing": "opaque-preserved", "editable_plain_text": False, "reason": str(error)})
                        stats["opaque_entries"] += 1
                    rows.write(json.dumps(record, ensure_ascii=True) + "\n")
        summaries[name] = {**stats, "glyph_count": len(table.codes),
                           "glyph_table_sha256": hashlib.sha256(table_raw).hexdigest(),
                           "unresolved_inline_word_counts": controls}
    report = {"scope": "message-framing-and-glyph-inventory", "translation_complete": False,
              "variants": summaries, "new_translations_added": 0}
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
