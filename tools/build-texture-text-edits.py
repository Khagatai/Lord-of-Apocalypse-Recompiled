"""Layer measured text texture edits over a verified private MES archive candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from rgf_archive import parse_index, resources
from rgf_edits import append_edits
from texture_text import digest, reconstruct, verify


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--archives', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    parent_raw = (args.archives/'result.json').read_bytes()
    parent = json.loads(parent_raw)
    if not parent.get('all_resource_payloads_verified'):
        raise ValueError('Parent archive has no verified resource report')
    for name, expected in parent['candidate_archives_sha256'].items():
        if file_hash(args.archives/name) != expected:
            raise ValueError('Parent archive hash differs')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    records = {int(record['resource_id'], 16): record for record in manifest['resources']}
    if not records or len(records) != len(manifest['resources']):
        raise ValueError('Empty or duplicate texture manifest')
    index = (args.archives/'REGFILE.RZL').read_bytes()
    groups = parse_index(index, (args.archives/'REGFILE.RZP').stat().st_size)
    replacements, checked = {}, []
    with (args.archives/'REGFILE.RZP').open('rb') as source:
        for _, identity, raw in resources(source, groups):
            if identity not in records:
                continue
            record = records[identity]
            key = identity, digest(raw)
            if key in replacements:
                continue
            if digest(raw) != record['source_sha256']:
                continue
            target = reconstruct(raw, record, ROOT/'private')
            if target == raw:
                raise ValueError('Texture manifest makes no change')
            verified = {**record, 'target_sha256': digest(target)}
            verify(raw, target, verified, ROOT/'private')
            replacements[key] = target
            checked.append(verified)
    if len(checked) != len(records):
        raise ValueError('Texture source variant missing')
    output.mkdir(parents=True)
    shutil.copyfile(args.archives/'REGFILE.RZP', output/'REGFILE.RZP')
    with (args.archives/'REGFILE.RZP').open('rb') as source, (output/'REGFILE.RZP').open('r+b') as target:
        rebuilt, checks = append_edits(index, source, target, replacements)
    (output/'REGFILE.RZL').write_bytes(rebuilt)
    for name, expected in parent['candidate_archives_sha256'].items():
        if file_hash(args.archives/name) != expected:
            raise ValueError('Parent archive changed during generation')
    texture_report = {'scope': 'verified-local-texture-text-regions', 'resources': checked,
                      'parent_archive_report_sha256': digest(parent_raw), 'all_other_parent_resource_payloads_unchanged': True}
    (output/'texture-text-report.json').write_text(json.dumps(texture_report, indent=2)+'\n')
    result = {**parent, **checks, 'status': 'candidate-not-installed-requires-in-game-review',
              'translation_complete': False, 'source_unchanged': True,
              'resource_ids': sorted(set(parent['resource_ids']) | {f'{identity:08x}' for identity in records}),
              'candidate_archives_sha256': {name: file_hash(output/name) for name in ('REGFILE.RZL', 'REGFILE.RZP')},
              'parent_archive_report_sha256': digest(parent_raw), 'texture_text_resource_variants': len(checked),
              'texture_text_report_sha256': file_hash(output/'texture-text-report.json')}
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'edited_texture_variants': len(checked), 'all_resource_payloads_verified': checks['all_resource_payloads_verified'],
                      'candidate_archives_sha256': result['candidate_archives_sha256']}, indent=2))


if __name__ == '__main__':
    main()
