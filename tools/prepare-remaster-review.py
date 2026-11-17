"""Prepare deduplicated private artwork previews from an exported coverage catalog.

This never edits archives, enables a pack, or marks an image visually reviewed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/inventory-textures.py')
inventory=importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--minimum-dimension',type=int,choices=range(1,513),default=1)
    args=parser.parse_args()
    catalog=args.catalog.resolve();output=args.output.resolve()
    if not catalog.is_relative_to(ROOT/'private') or not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use an exported private catalog and a fresh private output directory')
    report=json.loads((catalog/'result.json').read_text())
    if report.get('exported_rgba') is not True:
        raise ValueError('Catalog lacks exported RGBA data')
    data=(catalog/'catalog.json').read_bytes();rows=json.loads(data)
    output.mkdir(parents=True)
    exports={};records=[]
    for row in rows:
        base=row['authored_levels'][0]
        if 'rgba_sha256' not in base or min(row['width'],row['height'])<args.minimum_dimension:
            continue
        digest=base['rgba_sha256']
        # A hash identifies bytes; dimensions also participate in deduplication.
        key=(digest,row['width'],row['height'])
        if key not in exports:
            source=catalog/'rgba'/(digest+'.rgba')
            if not source.resolve().is_relative_to(catalog):
                raise ValueError('RGBA reference escapes catalog')
            raw=source.read_bytes()
            if len(raw)!=row['width']*row['height']*4 or hashlib.sha256(raw).hexdigest()!=digest:
                raise ValueError('Exported RGBA geometry or hash differs')
            name=f"preview-{len(exports):05d}.png"
            (output/name).write_bytes(inventory.png(row['width'],row['height'],raw))
            exports[key]=name
        records.append(dict(resource_id=row['resource_id'],sha256=row['source_sha256'],
                            textures=[dict(name=row['name'],preview=exports[key],
                                texture_index=row['texture_index'],width=row['width'],height=row['height'])]))
    (output/'textures.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    summary=dict(scope='private-remaster-review-preparation',descriptor_references=len(records),
                 unique_previews=len(exports),catalog_sha256=hashlib.sha256(data).hexdigest(),
                 minimum_dimension=args.minimum_dimension,visual_review_complete=False)
    (output/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
