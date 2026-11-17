"""Independently compare subtitle timing and non-message payloads in archive copies."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import Bundle
from mes_subtitles import TimedMessage
from rgf_archive import parse_index, read_group
import texture_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--source", type=Path, default=ROOT / "private/translation/archives/english-v16")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument('--texture-report', type=Path, help='Independently reconstruct explicitly approved text-pixel regions')
    args = parser.parse_args()
    from translation_baseline import ensure_archives
    args.source=ensure_archives(args.source)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private report path")
    def index(root):
        return parse_index((root / "REGFILE.RZL").read_bytes(), (root / "REGFILE.RZP").stat().st_size)
    old, new = index(args.source), index(args.candidate)
    if len(old) != len(new):
        raise ValueError("Group count changed")
    texture_records = {}
    if args.texture_report:
        if not args.texture_report.resolve().is_relative_to(ROOT/'private'):
            raise ValueError('Texture reports must remain private')
        texture_report = json.loads(args.texture_report.read_text())
        if texture_report['scope'] != 'verified-local-texture-text-regions':
            raise ValueError('Unknown texture text report scope')
        texture_records = {(int(row['resource_id'], 16), row['source_sha256']): row for row in texture_report['resources']}
    checked_payloads, checked_bundles, checked_cues, checked_textures = 0, 0, 0, 0
    seen_textures = set()
    with (args.source / "REGFILE.RZP").open("rb") as source, (args.candidate / "REGFILE.RZP").open("rb") as target:
        for before, after in zip(old, new):
            if len(before.entries) != len(after.entries):
                raise ValueError("Descriptor count changed")
            original, candidate = read_group(source, before), read_group(target, after)
            a = b = 0
            for (old_size, identity), (new_size, new_identity) in zip(before.entries, after.entries):
                if identity != new_identity:
                    raise ValueError("Resource membership changed")
                x, y = original[a:a+old_size], candidate[b:b+new_size]
                a += old_size
                b += new_size
                if identity >> 16 != 4:
                    texture_key = identity, texture_text.digest(x)
                    if texture_key in texture_records:
                        texture_text.verify(x, y, texture_records[texture_key], ROOT/'private')
                        checked_textures += 1
                        seen_textures.add(texture_key)
                        continue
                    if x != y:
                        raise ValueError("Non-message resource changed, including audio")
                    checked_payloads += 1
                    continue
                xb, yb = Bundle.parse(x), Bundle.parse(y)
                if xb.offsets != yb.offsets:
                    raise ValueError("Message aliases changed")
                for block, raw in enumerate(xb.blocks):
                    try:
                        timed = TimedMessage.parse(raw)
                    except ValueError:
                        continue
                    changed = TimedMessage.parse(yb.blocks[block])
                    if timed.header != changed.header or timed.padding != changed.padding or len(timed.cues) != len(changed.cues):
                        raise ValueError("Timed message metadata changed")
                    for first, second in zip(timed.cues, changed.cues):
                        if first.timing != second.timing or first.ending != second.ending or len(first.lines) != len(second.lines):
                            raise ValueError("Subtitle clock, boundary or line count changed")
                        checked_cues += 1
                    checked_bundles += 1
    if seen_textures != set(texture_records):
        raise ValueError('An approved texture text resource was not found')
    report = {"subtitle_timing_fields": "byte-identical", "cue_boundaries": "unchanged",
              "non_message_payload_instances_verified": checked_payloads,
              "timed_bundle_instances_verified": checked_bundles, "timed_cues_verified": checked_cues,
              "audio_and_non_message_assets_unchanged": not bool(checked_textures),
              "audio_and_non_text_assets_unchanged": True,
              "approved_texture_text_instances_verified": checked_textures,
              "translation_quality_validated": False, "in_game_layout_validated": False}
    output.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
