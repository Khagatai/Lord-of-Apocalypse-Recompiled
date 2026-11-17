"""Inventory original/English RGF1 resources and privately extract changed payloads."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rgf_archive

ROOT = Path(__file__).resolve().parents[1]

def inspect(folder):
    packed = folder / "REGFILE.RZP"
    groups = rgf_archive.parse_index((folder / "REGFILE.RZL").read_bytes(), packed.stat().st_size)
    records, types = {}, Counter()
    with packed.open("rb") as stream:
        for group, identity, data in rgf_archive.resources(stream, groups):
            digest = hashlib.sha256(data).hexdigest()
            key = f"{identity:08x}"
            types[identity >> 16] += 1
            record = records.setdefault(key, {"kind": identity >> 16, "variants": {}})
            variant = record["variants"].setdefault(digest, {"size": len(data), "groups": [], "header_hex": data[:16].hex()})
            variant["groups"].append(group)
    return {"group_count": len(groups), "distinct_resources": len(records),
            "descriptor_count": sum(types.values()), "kind_descriptor_counts": dict(types), "resources": records}, groups

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, default=ROOT / "private/translation/archives")
    parser.add_argument("--output", type=Path, default=ROOT / "private/translation/archive-inventory")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    output.mkdir(parents=True)
    surveys, indexes = {}, {}
    for name in ("japanese", "english-v16"):
        from translation_baseline import ensure_archives
        surveys[name], indexes[name] = inspect(ensure_archives(args.archives / name))
        (output / f"{name}.json").write_text(json.dumps(surveys[name], indent=2) + "\n")
    left, right = (surveys[n]["resources"] for n in ("japanese", "english-v16"))
    changed = {key for key in left.keys() | right.keys()
               if set(left.get(key, {}).get("variants", {})) != set(right.get(key, {}).get("variants", {}))}
    for name in surveys:
        destination = output / name
        destination.mkdir()
        with (args.archives / name / "REGFILE.RZP").open("rb") as stream:
            for group, identity, data in rgf_archive.resources(stream, indexes[name]):
                if f"{identity:08x}" in changed:
                    digest = hashlib.sha256(data).hexdigest()
                    path = destination / f"{identity:08x}-{digest[:16]}.bin"
                    if not path.exists():
                        path.write_bytes(data)
    summary = {"scope": "resource-content-difference-not-translation-coverage", "changed_resource_ids": sorted(changed),
               "variants": {name: {k: value for k, value in report.items() if k != "resources"} for name, report in surveys.items()},
               "translation_completeness": "NOT_MEASURED", "text_format": "NOT_YET_DECODED"}
    (output / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"changed_resource_ids": len(changed), "variants": summary["variants"],
                      "translation_completeness": "NOT_MEASURED"}, indent=2))

if __name__ == "__main__":
    main()
