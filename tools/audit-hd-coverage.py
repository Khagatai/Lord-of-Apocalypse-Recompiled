"""Measure exact archive-identity coverage of a private HD pack, without playing."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import sampler_pack
import texture_pack
import remaster_policy
import archive_identity


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','pack','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    for name in ('catalog','pack','output'):
        path=getattr(args,name).resolve();setattr(args,name,path)
        if not path.is_relative_to(ROOT/'private'):parser.error('Use private paths')
    if args.output.exists():parser.error('Use fresh private output')
    verified=texture_pack.verify_sample(args.pack)
    raw=(args.catalog/'catalog.json').read_bytes();catalog=json.loads(raw)
    spec=importlib.util.spec_from_file_location('archive_selection',ROOT/'tools/build-archive-remaster.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    identities={}
    for row in catalog:
        for key in row['candidate_keys']:identities.setdefault(key,set()).add(module.signature(row))
    groups={g['key']:g for g in verified['textures']};rows=[]
    resolved={key:archive_identity.longest_compatible(sigs) for key,sigs in identities.items()}
    for row in catalog:
        sig=module.signature(row);contexts=[];ambiguous=False
        if sig:
            for wrap in (0,1,256,257):
                matched=[]
                for key in row['candidate_keys']:
                    if resolved[key] is None:ambiguous=True;continue
                    # Tagged context takes precedence in the actual renderer.
                    group=(groups.get(sampler_pack.tagged_key(key,wrap)) if verified.get('sampler_namespace') else None)
                    # A zero raw hash must never be installed as an INI wildcard.
                    if group is None and int(key[-8:],16):group=groups.get(key)
                    if not int(key[-8:],16) and group is None:ambiguous=True
                    if group is None:continue
                    if not archive_identity.supplies(group,sig):continue
                    matched.append(dict(key=group['key'],origin=group.get('origin','legacy')))
                if matched:contexts.append(dict(wrap=wrap,matches=matched))
        required=list(row['candidate_keys'])
        for context in contexts:
            context['required_alignment_identities']=len(required)
            context['complete']=len(context['matches'])==len(required) and bool(required)
        status='complete-four-context-identity' if not ambiguous and len(contexts)==4 and all(c['complete'] for c in contexts) else 'partial-context-identity' if contexts else 'no-pack-identity'
        if remaster_policy.original_portrait(row['name']):
            status='original-dialogue-portrait' if not contexts else 'unexpected-portrait-replacement'
        elif sig is None:status='incomplete-source-decode'
        elif ambiguous and not contexts:status='ambiguous-or-wildcard-source'
        rows.append(dict(resource_id=row['resource_id'],source_sha256=row['source_sha256'],texture_index=row['texture_index'],
            name=row['name'],status=status,contexts=contexts,opaque=all(l.get('opaque') for l in row['authored_levels']),
            signature=sig))
    totals=Counter(r['status'] for r in rows);unique={}
    for row in rows:
        key=json.dumps(row['signature']) if row['signature'] is not None else json.dumps([row['resource_id'],row['source_sha256'],row['texture_index']])
        # Identical pixels may have different palette keys; keep each row's coverage above.
        unique.setdefault(key,set()).add(row['status'])
    summary=dict(scope='offline-pack-identity-coverage-not-campaign-validation',catalog_sha256=hashlib.sha256(raw).hexdigest(),
        pack_manifest_sha256=verified['sample_manifest_sha256'],descriptors=len(rows),descriptor_status=dict(totals),
        unique_pixel_chains=len(unique),unique_chains_all_rows_covered=sum(v=={'complete-four-context-identity'} for v in unique.values()),
        visual_quality_validated=False,campaign_validated=False,notes=[
            'Counts include palette variants, aliases and potentially unused assets.',
            'Identity coverage does not establish that every texture is used, visually acceptable or restored with a neural model.',
            'Unmatched textures retain the renderer fallback; source decode failures are never filled with invented palette values.'])
    summary['archive_identity_coverage_complete']=all(r['status'] in ('complete-four-context-identity','original-dialogue-portrait') for r in rows)
    args.output.mkdir(parents=True)
    (args.output/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
    (args.output/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
