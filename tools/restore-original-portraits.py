"""Disable HD dialogue illustrations in place; game assets supply original art."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))

import pack_update
import remaster_policy
import texture_pack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',type=Path,required=True)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    for name in ('pack','catalog','output'):
        value=getattr(args,name).resolve()
        if not value.is_relative_to(texture_pack.ROOT/'private'):
            parser.error('Use private storage')
        setattr(args,name,value)
    if args.output.is_relative_to(args.pack):parser.error('Keep reports outside the pack')
    checked=texture_pack.verify_sample(args.pack)
    raw=(args.catalog/'catalog.json').read_bytes()
    keys=remaster_policy.portrait_keys(json.loads(raw))
    report=json.loads((args.pack/'sample.json').read_bytes())
    removed=[g for g in report['textures'] if remaster_policy.portrait_group(g,keys)]
    kept=[g for g in report['textures'] if not remaster_policy.portrait_group(g,keys)]
    referenced={e['file'] for g in kept for e in g['levels']}
    obsolete=sorted({e['file'] for g in removed for e in g['levels']}-referenced)
    result=dict(scope='original-dialogue-portrait-policy',applied=False,
                catalog_sha256=hashlib.sha256(raw).hexdigest(),
                base_manifest_sha256=checked['sample_manifest_sha256'],
                removed_groups=len(removed),retained_groups=len(kept),
                orphan_pngs=obsolete,
                names=sorted({r['name'] for g in removed for r in g.get('archive_references',[])}))
    if args.apply and removed:
        lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
        for group in kept:
            lines.extend(f"{group['key']}_{level} = {entry['file']}" for level,entry in enumerate(group['levels']))
        ini=('\n'.join(lines)+'\n').encode('ascii')
        report.update(textures=kept,ini_sha256=hashlib.sha256(ini).hexdigest(),
                      base_manifest_sha256=checked['sample_manifest_sha256'],
                      dialogue_portraits='original-game-assets')
        after=pack_update.commit(args.pack,report,ini)
        if any(remaster_policy.portrait_group(g,keys) for g in after['textures']):
            raise ValueError('Portrait replacements remain')
        result.update(applied=True,manifest_sha256=after['sample_manifest_sha256'],images=after['images'])
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='orphan_pngs'},indent=2))


if __name__=='__main__':main()
