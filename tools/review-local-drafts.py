"""Structural/terminology triage, never an automatic semantic-quality pass."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import GlyphTable
import mes_tokens

spec = importlib.util.spec_from_file_location("local_draft_checks", ROOT / "tools/draft-local-dialogue.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def latin_ascii(text):
    if not isinstance(text, str):
        raise ValueError("Non-string draft text")
    output = []
    for char in unicodedata.normalize("NFKD", checks.normalize(text)):
        if unicodedata.combining(char) and output and "LATIN" in unicodedata.name(output[-1], ""):
            continue
        output.append(char)
    return unicodedata.normalize("NFC", "".join(output)).replace("\u2022", "-")


def review(row, table, terminology, literal_glossary=None):
    source = row["source_lines"]
    proposed = row.get("translated_lines")
    provenance = "local-model"
    literal_glossary = literal_glossary or {}
    if len(source) == 1 and source[0] in literal_glossary:
        proposed = [literal_glossary[source[0]]]
        provenance = "existing-patch-or-authored-glossary"
    try:
        if isinstance(proposed, str):
            proposed = checks.wrap_paragraph(latin_ascii(proposed), len(source))
        elif isinstance(proposed, list):
            proposed = [latin_ascii(line) for line in proposed]
        else:
            raise ValueError(row.get("reason", "No translated text"))
        if re.search(r'earlier rejected draft|rejection reason|protected literal meanings|japanese passage|visible characters to leave room',
                     ' '.join(proposed), re.IGNORECASE):
            raise ValueError('Model copied translation instructions into game text')
        try:
            translated = checks.check(proposed, source, table)
        except ValueError as error:
            if str(error) != 'Line exceeds provisional width budget':
                raise
            translated = checks.check(checks.wrap_paragraph(' '.join(proposed), len(source)), source, table)
    except ValueError as error:
        return {**row, "status": "blocked-review", "reason": str(error), "quality_reviewed": False}
    original = "".join(source)
    english = " ".join(translated)
    issues = []
    # Only a review flag: synonyms, inflections and contextual uses require judgement.
    missing = [target for term, target in terminology.items() if term in original and target.casefold() not in english.casefold()]
    if missing:
        issues.append({"kind": "terminology-review", "expected": sorted(set(missing))})
    visible = mes_tokens.TAG.sub("", english).strip()
    if re.search(r"\b(the|a|an|its|their|whose|with|of|to)\s*$", visible, re.IGNORECASE):
        issues.append({"kind": "possible-incomplete-sentence"})
    if re.match(r"(?:the\s+)?(?:english\s+)?translation\s*(?:is|:)", visible, re.IGNORECASE):
        issues.append({"kind": "possible-model-commentary"})
    stars = Counter(char for char in original if char in "★☆")
    if Counter(char for char in english if char in "★☆") != stars:
        return {**row, "status": "blocked-review", "reason": "Visible star rating changed", "quality_reviewed": False}
    return {**row, "translated_lines": translated, "status": "machine-draft-structure-checked",
            "provenance": provenance, "review_flags": issues, "quality_reviewed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", type=Path)
    parser.add_argument("drafts", type=Path)
    parser.add_argument("--terminology", type=Path, default=ROOT / "private/translation/work/text-terminology-derived.json")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--corrections", type=Path, help="Private directly authored corrections bound to source IDs")
    parser.add_argument("--literal-glossary", type=Path, default=ROOT / "private/translation/work/text-terminology.json",
                        help="Explicitly chosen literal names; derived terminology is used only for review flags")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    table = GlyphTable.parse((args.queue / "glyph-table.bin").read_bytes())
    terminology = json.loads(args.terminology.read_text(encoding="utf-8"))
    literal_glossary = json.loads(args.literal_glossary.read_text(encoding="utf-8"))
    corrections = json.loads(args.corrections.read_text(encoding="utf-8")) if args.corrections else {}
    output.mkdir(parents=True)
    stats = Counter()
    with args.drafts.open(encoding="utf-8") as source, (output / "drafts.jsonl").open("w", encoding="utf-8") as target:
        for row in map(json.loads, source):
            corrected = False
            if row["id"] in corrections:
                correction = corrections[row["id"]]
                if row["source_lines"] != correction["source_lines"]:
                    raise ValueError("Direct correction source differs")
                row = {**row, "translated_lines": checks.check(correction["translated_lines"], row["source_lines"], table)}
                corrected = True
            result = review(row, table, terminology, literal_glossary)
            if corrected:
                result["provenance"] = "directly-authored-correction"
            stats[result["status"]] += 1
            stats["entries_with_review_flags"] += bool(result.get("review_flags"))
            target.write(json.dumps(result, ensure_ascii=True)+"\n")
    report = {"translation_complete": False, "semantic_quality_validated": False, "counts": dict(stats)}
    (output / "summary.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
