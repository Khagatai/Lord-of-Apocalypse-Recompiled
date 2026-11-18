"""Inventory every MES entry and check text against recorded panel geometry.

Unmeasured callers and runtime substitutions remain explicit review work.
Reports and all decoded game text stay under private/.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from mes_codec import Bundle, GlyphTable, Message
from mes_legacy import LegacyMessage
from mes_subtitles import TimedMessage
from rgf_archive import parse_index, resources
from text_panel_layout import measurements, profile_for


def audit(archives, profiles):
    index = (archives / 'REGFILE.RZL').read_bytes()
    path = archives / 'REGFILE.RZP'
    groups = parse_index(index, path.stat().st_size)
    with path.open('rb') as stream:
        glyphs = {raw for _, identity, raw in resources(stream, groups) if identity == 0x50d78}
    if len(glyphs) != 1:
        raise ValueError('Glyph table is missing or ambiguous')
    table = GlyphTable.parse(glyphs.pop())
    counts = Counter()
    by_resource = {}
    seen = set()
    review = []
    with path.open('rb') as stream:
        for group, identity, raw in resources(stream, groups):
            if identity >> 16 != 4:
                continue
            counts['resource_occurrences'] += 1
            digest = hashlib.sha256(raw).hexdigest()
            if (identity, digest) in seen:
                continue
            seen.add((identity, digest))
            resource_id = f'{identity:08x}'
            stats = by_resource.setdefault(resource_id, Counter())
            stats['variants'] += 1
            bundle = Bundle.parse(raw)
            for index, block in enumerate(bundle.offsets):
                stats['entries'] += 1
                record = dict(resource_id=resource_id, bundle_sha256=digest,
                              first_group=group, message_index=index)
                data = bundle.blocks[block]
                try:
                    if identity == 0x40008:
                        messages = [LegacyMessage.parse(data, table)]
                        record['framing'] = 'legacy'
                    else:
                        try:
                            messages = [Message.parse(data)]
                            record['framing'] = 'normal'
                        except ValueError:
                            timed = TimedMessage.parse(data)
                            messages = [cue.message() for cue in timed.cues]
                            record['framing'] = 'timed'
                except ValueError as error:
                    stats['framing_needs_review'] += 1
                    review.append(dict(record, status='framing-needs-review', reason=str(error)))
                    continue
                for cue, message in enumerate(messages):
                    try:
                        lines, advances, uncertain = measurements(message, table)
                    except ValueError as error:
                        stats['commands_need_review'] += 1
                        review.append(dict(record, status='commands-need-review', reason=str(error)))
                        continue
                    if not any(line.strip() for line in lines) or lines == ['\u2121']:
                        stats['empty_or_unused'] += 1
                        continue
                    profile = profile_for(profiles, resource_id, index, lines)
                    entry = dict(record, cue=cue if len(messages) > 1 else None,
                                 lines=lines, advances=advances, rows=len(lines))
                    if profile:
                        entry.update(profile=profile['name'], width=profile['width'],
                                     maximum_rows=profile['rows'])
                    if uncertain:
                        status = 'runtime-controls-need-review'
                        entry['commands'] = uncertain
                    elif not profile:
                        status = 'caller-geometry-needs-review'
                    elif max(advances) > profile['width'] or len(lines) > profile['rows']:
                        status = 'exceeds-recorded-panel'
                    else:
                        status = 'fits-recorded-geometry'
                    stats[status] += 1
                    if status != 'fits-recorded-geometry':
                        review.append(dict(entry, status=status))
    for stats in by_resource.values():
        counts.update(stats)
    return dict(scope='all MES resource variants and entries in the working archive',
                counts=counts, resources=by_resource, review=review,
                complete_visual_validation=False,
                width_model='6-pixel ASCII, 12-pixel full-width glyphs and icons',
                texture_lettering_and_movie_overlays_included=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, default=ROOT / 'private/translation/text-pass-16-archives')
    parser.add_argument('--profiles', type=Path, default=ROOT / 'config/text-panel-layout.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'private/panel-layout-audit/messages.json')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'private'):
        parser.error('Decoded text reports must stay private')
    config = json.loads(args.profiles.read_text(encoding='utf-8'))
    report = audit(args.archives, config['profiles'])
    report['profile_sha256'] = hashlib.sha256(args.profiles.read_bytes()).hexdigest()
    report['index_sha256'] = hashlib.sha256((args.archives / 'REGFILE.RZL').read_bytes()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['counts'], indent=2))


if __name__ == '__main__':
    main()
