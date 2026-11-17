"""Inventory local XET names and dimensions, with optional private PNG previews."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from rgf_archive import parse_index, resources
from xet_codec import Xet


def png(width, height, rgba):
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    scan = b''.join(b'\0'+rgba[y*width*4:(y+1)*width*4] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>2I5B', width, height, 8, 6, 0, 0, 0))+
            chunk(b'IDAT', zlib.compress(scan))+chunk(b'IEND', b''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, default=ROOT/'private/translation/archives/english-v16')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview-pattern', help='Regular expression for texture names to decode')
    parser.add_argument('--preview-limit', type=int, default=64)
    parser.add_argument('--preview-dimension', type=int, default=256)
    args = parser.parse_args()
    from translation_baseline import ensure_archives
    args.archives=ensure_archives(args.archives)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    output.mkdir(parents=True)
    pattern = re.compile(args.preview_pattern, re.IGNORECASE) if args.preview_pattern else None
    index = parse_index((args.archives/'REGFILE.RZL').read_bytes(), (args.archives/'REGFILE.RZP').stat().st_size)
    seen, rows, previews = set(), [], 0
    with (args.archives/'REGFILE.RZP').open('rb') as stream:
        for group, identity, raw in resources(stream, index):
            if identity >> 16 != 2:
                continue
            digest = hashlib.sha256(raw).hexdigest()
            if (identity, digest) in seen:
                continue
            seen.add((identity, digest))
            row = {'resource_id': f'{identity:08x}', 'sha256': digest, 'group': group, 'size': len(raw)}
            try:
                container = Xet.parse(raw)
                row['textures'] = [asdict(texture) for texture in container.textures]
                row['palettes'] = container.palettes
                if pattern:
                    for number, texture in enumerate(container.textures):
                        if previews >= args.preview_limit or not pattern.search(texture.name):
                            continue
                        entry = row['textures'][number]
                        try:
                            width, height, pixels = container.preview(number, limit=args.preview_dimension)
                            filename = f'{identity:08x}-{digest[:12]}-{number:02d}.png'
                            (output/filename).write_bytes(png(width, height, pixels))
                            entry['preview'] = filename
                            previews += 1
                        except ValueError as error:
                            entry['preview_error'] = str(error)
            except (ValueError, struct.error) as error:
                row['parse_error'] = str(error)
            rows.append(row)
    report = {'scope': 'read-only-texture-inventory', 'resource_variants': len(rows),
              'parsed_variants': sum('textures' in row for row in rows), 'previews': previews,
              'visual_text_audit_complete': False, 'translation_complete': False}
    (output/'textures.json').write_text(json.dumps(rows, ensure_ascii=True, indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
