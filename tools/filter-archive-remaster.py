"""Select independently checked archive artwork while preserving the base pack."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import sampler_pack
import texture_pack


def sha(data):return hashlib.sha256(data).hexdigest()


def excluded(asset,patterns,indices=()):
    # A shared atlas must be safe for every alias, not just its first name.
    return asset.get('index') in indices or any(pattern.search(ref['name']) for ref in asset['references'] for pattern in patterns)


def policy_indices(policy,manifest,assets,generation_sha256=None):
    required=policy.get('required_batch_manifest_sha256')
    indices=policy.get('exclude_asset_indices',[])
    if required is not None and required!=manifest:
        raise ValueError('Selection policy belongs to another batch manifest')
    if indices and required is None:raise ValueError('Index exclusions must pin the exact batch manifest')
    if indices and (generation_sha256 is None or policy.get('required_generation_sha256')!=generation_sha256):
        raise ValueError('Index exclusions must pin the exact generation report')
    if any(type(i) is not int for i in indices) or not set(indices)<={a['index'] for a in assets}:
        raise ValueError('Unknown or invalid exclusion index')
    return set(indices)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('batch','base-pack','check','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--policy',type=Path,required=True)
    args=parser.parse_args()
    for name in ('batch','base_pack','check','output'):
        path=getattr(args,name).resolve();setattr(args,name,path)
        if not path.is_relative_to(ROOT/'private'):parser.error('Artwork and evidence stay private')
    if args.output.exists():parser.error('Use fresh private output')
    batch=texture_pack.verify_sample(args.batch/'pack');base=texture_pack.verify_sample(args.base_pack)
    generation_raw=(args.batch/'result.json').read_bytes();generation=json.loads(generation_raw)
    check_raw=(args.check/'result.json').read_bytes();check=json.loads(check_raw)
    if not generation.get('complete') or generation['base_manifest_sha256']!=base['sample_manifest_sha256']:
        raise ValueError('Incomplete generation or wrong base')
    if generation['pack_manifest_sha256']!=batch['sample_manifest_sha256'] or not check.get('passed') or check['pack_manifest_sha256']!=batch['sample_manifest_sha256']:
        raise ValueError('Independent check does not certify this batch')
    if check['assets']!=len(generation['assets']) or check['png_context_levels']!=sum(len(c['levels']) for a in generation['assets'] for c in a['contexts']):
        raise ValueError('Independent check has incomplete coverage')
    policy_raw=args.policy.read_bytes();policy=json.loads(policy_raw)
    indices=policy_indices(policy,batch['sample_manifest_sha256'],generation['assets'],sha(generation_raw))
    patterns=[re.compile(value) for value in policy['exclude_name_patterns']]
    allowed={};rejected=[];accepted=[]
    for asset in generation['assets']:
        if excluded(asset,patterns,indices):rejected.append(asset);continue
        accepted.append(asset)
        for context in asset['contexts']:
            signature=tuple((l['width'],l['height'],l['sha256']) for l in context['levels'])
            for key in asset['canonical_keys']:
                tagged=sampler_pack.tagged_key(key,context['wrap'])
                if tagged in allowed and allowed[tagged]!=signature:raise ValueError('Conflicting admitted identity')
                allowed[tagged]=signature
    base_keys={g['key'] for g in base['textures']};groups=[(args.base_pack,g) for g in base['textures']]
    for group in batch['textures']:
        key=group['key']
        if key not in allowed:continue
        actual=tuple((l['width'],l['height'],l['sha256']) for l in group['levels'])
        if actual!=allowed.pop(key) or key in base_keys:raise ValueError('Batch identity differs or shadows base')
        groups.append((args.batch/'pack',group))
    if allowed:raise ValueError('An admitted identity is missing')
    args.output.mkdir(parents=True);files={};textures=[]
    for folder,original in groups:
        group=json.loads(json.dumps(original))
        for entry in group['levels']:
            name=entry['file'];digest=entry['sha256']
            if digest not in files:
                data=(folder/name).read_bytes()
                if sha(data)!=digest:raise ValueError('Source PNG changed')
                target=f'tex-{len(files):05d}-0.png';(args.output/target).write_bytes(data);files[digest]=target
            entry['file']=files[digest]
        textures.append(group)
    lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
    for group in textures:
        lines.extend(f"{group['key']}_{i} = {entry['file']}" for i,entry in enumerate(group['levels']))
    ini=('\n'.join(lines)+'\n').encode('ascii');(args.output/'textures.ini').write_bytes(ini)
    provenance=dict(batch_manifest_sha256=batch['sample_manifest_sha256'],base_manifest_sha256=base['sample_manifest_sha256'],
        generation_sha256=sha(generation_raw),independent_check_sha256=sha(check_raw),policy_sha256=sha(policy_raw),
        accepted_assets=len(accepted),rejected_assets=len(rejected))
    report=dict(scope='verified-mip-texture-pack',textures=textures,ini_sha256=sha(ini),sampler_namespace=sampler_pack.NAMESPACE,
        complete_hd_pack=False,visual_quality_validated=False,selection=provenance)
    (args.output/'sample.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.output/'selection.json').write_text(json.dumps(dict(**provenance,rejected=[dict(index=a['index'],references=a['references']) for a in rejected]),indent=2)+'\n')
    verified=texture_pack.verify_sample(args.output)
    print(json.dumps(dict(**provenance,manifest_sha256=verified['sample_manifest_sha256'],images=verified['images'],mip_chains=verified['mip_chains']),indent=2))


if __name__=='__main__':main()
