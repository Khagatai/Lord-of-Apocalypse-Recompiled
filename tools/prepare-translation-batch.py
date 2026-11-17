"""Assemble private draft translations into identity-checked per-bundle manifests."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assemble(pairs, rows, max_glyphs=48):
    lookup, matches = {}, {}
    for sources, draft in pairs:
        translations = draft["translations"]
        if len(sources) != len(translations):
            raise ValueError("Draft count differs from source count")
        for index, (source, english) in enumerate(zip(sources, translations)):
            if source["id"] != index:
                raise ValueError("Source order differs from explicit message IDs")
            if len(source["lines"]) != len(english):
                raise ValueError(f"Original line count must be preserved: draft {index}")
            if not all(isinstance(line, str) and 0 < len(line) <= max_glyphs and
                       "\n" not in line and "\r" not in line for line in english):
                raise ValueError(f"Draft exceeds provisional line budget: draft {index}")
            key = tuple(source["lines"])
            if key in lookup and lookup[key] != english:
                raise ValueError("Conflicting translations for identical source text")
            lookup[key] = english
            matches[key] = 0
    bundles, seen, affected = {}, set(), 0
    for row in rows:
        key = tuple(row.get("lines", []))
        if key not in lookup or not row.get("editable_plain_text"):
            continue
        identity = row["resource_id"], row["bundle_sha256"]
        if int(identity[0], 16) >> 16 != 4:
            raise ValueError("Only MES text resources are permitted")
        matches[key] += 1
        affected += 1
        block = (*identity, row["block"])
        if block in seen:
            continue
        seen.add(block)
        manifest = bundles.setdefault(identity, {"resource_id": identity[0],
                                                "source_bundle_sha256": identity[1], "entries": []})
        manifest["entries"].append({"message_index": row["message_index"], "before_sha256": row["raw_sha256"],
                                    "original_lines": row["lines"], "english_lines": lookup[key]})
    if not lookup or not all(matches.values()):
        raise ValueError("One or more drafts have no editable source match")
    return {"status": "draft-requires-context-and-layout-review", "scope": "text-only",
            "bundles": list(bundles.values())}, {
                "unique_drafts": len(lookup), "bundle_variants": len(bundles),
                "edited_blocks": len(seen), "affected_entries": affected,
                "provisional_max_line_glyphs": max_glyphs, "layout_validated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", nargs=2, type=Path, action="append", required=True,
                        metavar=("SOURCE_JSON", "DRAFT_JSON"))
    parser.add_argument("--inventory", type=Path, default=ROOT / "private/translation/messages/english-v16.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh JSON file under private/")
    pairs = [(json.loads(source.read_text()), json.loads(draft.read_text())) for source, draft in args.pair]
    with args.inventory.open(encoding="utf-8") as stream:
        manifest, stats = assemble(pairs, map(json.loads, stream))
    raw = json.dumps(manifest, ensure_ascii=True, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(raw)
    stats["manifest_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
