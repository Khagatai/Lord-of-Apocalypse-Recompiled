"""Export original base pixels of uncovered archive selections for local review."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import texture_pack


def helper(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','base-pack','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--pattern',required=True)
    parser.add_argument('--allow-alpha',action='store_true')
    args=parser.parse_args()
    for name in ('catalog','base_pack','output'):
        path=getattr(args,name).resolve();setattr(args,name,path)
        if not path.is_relative_to(ROOT/'private'):parser.error('Original art stays private')
    if args.output.exists():parser.error('Use fresh output')
    builder=helper('selection_builder','build-archive-remaster.py');inventory=helper('selection_inventory','inventory-textures.py')
    catalog_raw=(args.catalog/'catalog.json').read_bytes();catalog=json.loads(catalog_raw)
    if json.loads((args.catalog/'result.json').read_text()).get('exported_rgba') is not True:raise ValueError('Exact RGBA exports required')
    base=texture_pack.verify_sample(args.base_pack)
    selected,excluded=builder.select(catalog,re.compile(args.pattern),args.allow_alpha)
    selected,retained=builder.uncovered(selected,base);excluded.extend(retained)
    args.output.mkdir(parents=True);rows=[]
    for i,(sig,references,keys) in enumerate(selected):
        w,h,digest=sig[0];raw=(args.catalog/'rgba'/(digest+'.rgba')).read_bytes()
        if len(raw)!=w*h*4 or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Original source pixels differ')
        name=f'original-{i:05d}.png';(args.output/name).write_bytes(inventory.png(w,h,raw))
        rows.append(dict(resource_id=references[0]['resource_id'],sha256=references[0]['source_sha256'],
                         textures=[dict(name=references[0]['name'],preview=name)]))
    (args.output/'textures.json').write_text(json.dumps(rows,indent=2)+'\n')
    report=dict(scope='original-selected-archive-preview',catalog_sha256=hashlib.sha256(catalog_raw).hexdigest(),
        base_manifest_sha256=base['sample_manifest_sha256'],pattern=args.pattern,assets=len(selected),
        selected_names=[[r['name'] for r in e[1]] for e in selected],exclusions=excluded,
        visual_quality_validated=False,pack_created=False)
    (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Prepared {len(selected)} original base-art previews; no pack generated or review claimed.')


if __name__=='__main__':main()
