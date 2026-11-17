"""Inventory remaining local MES text and protected records for offline drafting."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import Bundle, GlyphTable, Message
from mes_legacy import LegacyMessage
from mes_subtitles import TimedMessage
from rgf_archive import parse_index, resources
import mes_tokens
import password_keys

JAPANESE = re.compile(r"[\u3041-\u3096\u30a1-\u30fa\u3400-\u9fff\uff66-\uff9d]")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, default=ROOT / "private/translation/archives/english-v16")
    parser.add_argument("--human-manifest", type=Path, default=ROOT / "private/translation/work/text-pass-01-batch.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from translation_baseline import ensure_archives
    args.archives=ensure_archives(args.archives)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    human = {}
    for bundle in json.loads(args.human_manifest.read_text())["bundles"]:
        for entry in bundle["entries"]:
            for edit in entry.get("cue_edits", [entry]):
                key = tuple(edit["original_lines"])
                value = edit["english_lines"]
                if key in human and human[key] != value:
                    raise ValueError("Conflicting prior draft")
                human[key] = value
    index = (args.archives / "REGFILE.RZL").read_bytes()
    groups = parse_index(index, (args.archives / "REGFILE.RZP").stat().st_size)
    with (args.archives / "REGFILE.RZP").open("rb") as stream:
        tables = {data for _, identity, data in resources(stream, groups) if identity == 0x50d78}
    if len(tables) != 1:
        raise ValueError("Glyph table variant differs")
    table_raw = tables.pop()
    table = GlyphTable.parse(table_raw)
    output.mkdir(parents=True)
    jobs, seen, stats = {}, set(), Counter()

    def job(text):
        identity = hashlib.sha256(text.encode("utf-8")).hexdigest()
        jobs.setdefault(identity, {"id": identity, "source": text})
        return identity

    with (output / "messages.jsonl").open("w", encoding="utf-8") as rows, (args.archives / "REGFILE.RZP").open("rb") as stream:
        for group, identity, raw in resources(stream, groups):
            if identity >> 16 != 4:
                continue
            digest = hashlib.sha256(raw).hexdigest()
            if (identity, digest) in seen:
                continue
            seen.add((identity, digest))
            bundle = Bundle.parse(raw)
            if bundle.build() != raw:
                raise ValueError("Bundle roundtrip differs")
            for number, block in enumerate(bundle.offsets):
                data = bundle.blocks[block]
                row = {"resource_id": f"{identity:08x}", "bundle_sha256": digest, "group": group,
                       "message_index": number, "block": block,
                       "before_sha256": hashlib.sha256(data).hexdigest()}
                try:
                    legacy = False
                    try:
                        message = Message.parse(data)
                    except ValueError:
                        if identity != 0x40008:
                            raise
                        message = LegacyMessage.parse(data, table)
                        legacy = True
                        row["legacy_cp932"] = True
                    plain_lines = [table.decode(line[:-1]) for line in message.lines]
                    row["raw_decoded_lines"] = plain_lines
                    if password_keys.protected(identity, number):
                        row["status"] = "protected-functional-password"
                    elif message.editable(table) and tuple(plain_lines) in human:
                        row.update(status="prior-human-draft", original_lines=plain_lines,
                                   english_lines=human[tuple(plain_lines)])
                    elif legacy:
                        row["original_lines"] = plain_lines
                        row["status"] = "blocked-legacy-review" if any(JAPANESE.search(line) for line in plain_lines) else "existing-no-japanese-script"
                        if row["status"] == "blocked-legacy-review":
                            row["reason"] = "Legacy trial metadata text requires meaning/context review"
                    else:
                        templates, _ = mes_tokens.message_template(message, table)
                        row["original_lines"] = templates
                        if not any(JAPANESE.search(line) for line in templates):
                            row["status"] = "existing-no-japanese-script"
                        elif message.editable(table):
                            row.update(status="offline-draft-plain", job=job("".join(templates)))
                        else:
                            spans = [mes_tokens.TAG.split(line) for line in templates]
                            row["status"] = "offline-draft-formatted"
                            # Translate prose spans only; command words/operands are never model input.
                            row["line_jobs"] = [[job(span) if JAPANESE.search(span) else None
                                                 for span in parts[::2]] for parts in spans]
                except ValueError as error:
                    try:
                        timed = TimedMessage.parse(data)
                    except ValueError:
                        row.update(status="blocked-format", reason=str(error))
                    else:
                        if timed.build() != data:
                            raise ValueError("Timed subtitle roundtrip differs")
                        for index, cue in enumerate(timed.cues):
                            templates, _ = mes_tokens.message_template(cue.message(), table)
                            cue_row = {**row, "timed_subtitles": True, "cue_index": index,
                                       "cue_before_sha256": hashlib.sha256(cue.build()).hexdigest(),
                                       "timing": cue.timing, "original_lines": templates}
                            if tuple(templates) in human:
                                cue_row.update(status="prior-human-draft", english_lines=human[tuple(templates)])
                            elif not any(JAPANESE.search(line) for line in templates):
                                cue_row["status"] = "existing-no-japanese-script"
                            else:
                                cue_row.update(status="offline-draft-timed", job=job("".join(templates)))
                            stats[cue_row["status"]] += 1
                            rows.write(json.dumps(cue_row, ensure_ascii=True)+"\n")
                        continue
                stats[row["status"]] += 1
                rows.write(json.dumps(row, ensure_ascii=True) + "\n")
    (output / "jobs.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in jobs.values()))
    (output / "glyph-table.bin").write_bytes(table_raw)
    report = {"scope": "all-MES-variants-text-only", "translation_complete": False,
              "message_entries": sum(stats.values()), "unique_offline_jobs": len(jobs), "statuses": dict(stats)}
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
