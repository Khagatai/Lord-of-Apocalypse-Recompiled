"""Reuse verified artwork for exact source aliases without copying PNG payloads."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import archive_identity
import pack_update
import remaster_policy
import sampler_pack
import texture_pack


def signature(row):
    levels=row.get('authored_levels',[])
    if len(levels)!=row.get('mip_levels') or not levels or any('rgba_sha256' not in l for l in levels):return None
    return tuple((l['width'],l['height'],l['rgba_sha256']) for l in levels)


def aliases(catalog,groups):
    identities={};references={};donors={};owners={g['key'] for g in groups}
    protected=remaster_policy.portrait_keys(catalog)
    for row in catalog:
        sig=signature(row)
        for key in row['candidate_keys']:
            identities.setdefault(key,set()).add(sig)
            if sig is not None:references.setdefault((key,sig),[]).append(row)
    for g in groups:
        hashes=g.get('source_rgba_sha256')
        if g.get('factor')!=4 or g.get('wrap') not in (0,1,256,257) or not hashes or len(hashes)!=len(g['levels']):continue
        if remaster_policy.portrait_group(g,protected):continue
        sig=tuple((max(1,g['source_width']>>l),max(1,g['source_height']>>l),h) for l,h in enumerate(hashes))
        donors.setdefault((sig,g['wrap']),[]).append(g)
    added=[];refused=[]
    for key,sigs in sorted(identities.items()):
        sig=archive_identity.longest_compatible(sigs)
        if sig is None or key in protected:continue
        for wrap in (0,1,256,257):
            tagged=sampler_pack.tagged_key(key,wrap)
            if tagged in owners or key in owners:continue
            options=donors.get((sig,wrap),[])
            versions={tuple((l['width'],l['height'],l['sha256']) for l in g['levels']) for g in options}
            if len(versions)>1:
                refused.append(dict(key=key,wrap=wrap,reason='multiple differing restored donors'));continue
            if not options:continue
            donor=options[0];g=copy.deepcopy(donor)
            g.update(key=tagged,canonical_key=key,alias_of=donor['key'],
                archive_references=[{k:r[k] for k in ('resource_id','source_sha256','texture_index','name')}
                                    for r in references[(key,sig)]])
            added.append(g);owners.add(tagged)
    return added,refused


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','pack','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--apply',action='store_true');args=p.parse_args()
    for name in ('catalog','pack','output'):
        path=getattr(args,name).resolve()
        if path==texture_pack.ROOT/'private' or not path.is_relative_to(texture_pack.ROOT/'private'):p.error('Use private paths')
        setattr(args,name,path)
    if args.output.is_relative_to(args.pack):p.error('Keep reports outside the working pack')
    checked=texture_pack.verify_sample(args.pack)
    if checked.get('sampler_namespace')!=sampler_pack.NAMESPACE:
        raise ValueError('Alias extension requires the verified sampler namespace')
    raw=(args.catalog/'catalog.json').read_bytes()
    report=json.loads((args.pack/'sample.json').read_bytes())
    added,refused=aliases(json.loads(raw),report['textures'])
    result=dict(scope='verified-source-alias-extension',applied=False,new_groups=len(added),
        catalog_sha256=hashlib.sha256(raw).hexdigest(),base_manifest_sha256=checked['sample_manifest_sha256'],
        png_files_copied=0,png_files_written=0,refused=refused,
        aliases=[dict(key=g['key'],donor=g['alias_of'],references=g['archive_references']) for g in added])
    if args.apply and added:
        report['textures'].extend(added)
        lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
        for g in report['textures']:lines.extend(f"{g['key']}_{i} = {l['file']}" for i,l in enumerate(g['levels']))
        ini=('\n'.join(lines)+'\n').encode('ascii')
        report.update(ini_sha256=hashlib.sha256(ini).hexdigest(),base_manifest_sha256=checked['sample_manifest_sha256'])
        after=pack_update.commit(args.pack,report,ini)
        result.update(applied=True,pack_manifest_sha256=after['sample_manifest_sha256'],images=after['images'])
    args.output.mkdir(exist_ok=True,parents=True)
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('aliases','refused')},indent=2))


if __name__=='__main__':main()
