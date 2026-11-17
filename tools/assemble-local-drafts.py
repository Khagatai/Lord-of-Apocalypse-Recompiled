"""Assemble checked local drafts into a private candidate; never mark them reviewed."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import GlyphTable

spec = importlib.util.spec_from_file_location("local_dialogue_checks", ROOT / "tools/draft-local-dialogue.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def assemble(messages, drafts, table, include_unreviewed):
    cache = {}
    for row in drafts:
        if row["id"] in cache:
            raise ValueError("Duplicate draft identity")
        cache[row["id"]] = row
    bundles, seen, stats, unresolved, timed_entries, timed_seen = {}, set(), Counter(), [], {}, set()
    for row in messages:
        status = row["status"]
        english, token_mode = None, False
        if status == "prior-human-draft":
            english = row["english_lines"]
        elif status.startswith("offline-draft-"):
            identity = hashlib.sha256(json.dumps(row["original_lines"], ensure_ascii=True).encode()).hexdigest()
            draft = cache.get(identity)
            if not draft:
                status = "not-yet-drafted"
            elif draft["source_lines"] != row["original_lines"]:
                raise ValueError("Draft source differs")
            elif draft["status"] != "machine-draft-structure-checked":
                status = "blocked-local-draft"
                row = {**row, "draft_reason": draft.get("reason")}
            elif not include_unreviewed:
                status = "unreviewed-not-included"
            else:
                english = checks.check(draft["translated_lines"], row["original_lines"], table)
                token_mode = "message-stream-v1"
                status = "unreviewed-draft-in-candidate"
        stats[status] += 1
        if english is None:
            if status not in ("existing-no-japanese-script", "protected-functional-password"):
                unresolved.append({"resource_id": row["resource_id"], "bundle_sha256": row["bundle_sha256"],
                                   "message_index": row["message_index"], "status": status,
                                   "cue_index": row.get("cue_index"),
                                   "reason": row.get("draft_reason", row.get("reason"))})
            continue
        identity = row["resource_id"], row["bundle_sha256"]
        block = (*identity, row["block"])
        if row.get("timed_subtitles"):
            cue_key = (*block, row["cue_index"])
            if cue_key in timed_seen:
                continue
            timed_seen.add(cue_key)
            bundle = bundles.setdefault(identity, {"resource_id": identity[0], "source_bundle_sha256": identity[1], "entries": []})
            if block not in timed_entries:
                timed_entries[block] = {"message_index": row["message_index"], "before_sha256": row["before_sha256"],
                                        "timed_subtitles": True, "cue_edits": []}
                bundle["entries"].append(timed_entries[block])
            timed_entries[block]["cue_edits"].append({"cue_index": row["cue_index"],
                "before_sha256": row["cue_before_sha256"], "original_lines": row["original_lines"], "english_lines": english})
            seen.add(block)
            continue
        if block in seen:
            continue
        seen.add(block)
        bundle = bundles.setdefault(identity, {"resource_id": identity[0], "source_bundle_sha256": identity[1], "entries": []})
        bundle["entries"].append({"message_index": row["message_index"], "before_sha256": row["before_sha256"],
                                  "original_lines": row["original_lines"], "english_lines": english,
                                  "token_mode": token_mode, "legacy_cp932": row.get("legacy_cp932", False)})
    manifest = {"status": "unreviewed-local-translation-candidate", "translation_complete": False,
                "quality_reviewed": False, "bundles": list(bundles.values())}
    report = {"translation_complete": False, "quality_reviewed": False, "all_text_layout_validated": False,
              "statuses": dict(stats), "message_entries": sum(stats.values()), "edited_blocks": len(seen),
              "bundle_variants": len(bundles), "unresolved_entries": len(unresolved)}
    report["edited_timed_cues"] = len(timed_seen)
    return manifest, report, unresolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", type=Path)
    parser.add_argument("drafts", type=Path)
    parser.add_argument("--include-unreviewed", action="store_true", help="Permit structure-checked machine drafts in this private candidate only")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    table = GlyphTable.parse((args.queue / "glyph-table.bin").read_bytes())
    with (args.queue / "messages.jsonl").open(encoding="utf-8") as messages, args.drafts.open(encoding="utf-8") as drafts:
        manifest, report, unresolved = assemble(map(json.loads, messages), map(json.loads, drafts), table, args.include_unreviewed)
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2)+"\n")
    (output / "coverage.json").write_text(json.dumps(report, indent=2)+"\n")
    (output / "unresolved.json").write_text(json.dumps(unresolved, ensure_ascii=True, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
