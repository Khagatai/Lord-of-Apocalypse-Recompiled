"""Merge verified private artwork batches, refusing conflicting texture identities."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import sampler_pack
import texture_pack


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():parser.error('Use fresh private output')
    packs=[(path.resolve(),texture_pack.verify_sample(path)) for path in args.pack]
    if any(report['scope']!='verified-mip-texture-pack' for path,report in packs):
        raise ValueError('Use complete-chain packs')
    output.mkdir(parents=True);groups={};files={};namespaces=[];inputs=[]
    for folder,report in packs:
        namespaces.append(report.get('sampler_namespace'))
        inputs.append(dict(path=str(folder),manifest_sha256=report['sample_manifest_sha256']))
        for original in report['textures']:
            group=json.loads(json.dumps(original));key=group['key']
            signature=(group['source_width'],group['source_height'],group['factor'],
                       tuple((l['width'],l['height'],l['sha256']) for l in group['levels']))
            if key in groups:
                if groups[key][0]!=signature:raise ValueError('Conflicting texture identity: '+key)
                continue
            for level,entry in enumerate(group['levels']):
                digest=entry['sha256']
                if digest not in files:
                    name=f'tex-{len(files):05d}-{level}.png';data=(folder/entry['file']).read_bytes()
                    if sha(data)!=digest:raise ValueError('Pack changed during merge')
                    (output/name).write_bytes(data);files[digest]=name
                entry['file']=files[digest]
            groups[key]=(signature,group)
    lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
    textures=[value[1] for value in groups.values()]
    for group in textures:
        lines.extend(f"{group['key']}_{level} = {entry['file']}" for level,entry in enumerate(group['levels']))
    ini=('\n'.join(lines)+'\n').encode('ascii');(output/'textures.ini').write_bytes(ini)
    report=dict(scope='verified-mip-texture-pack',textures=textures,ini_sha256=sha(ini),
        sampler_namespace=sampler_pack.NAMESPACE if any(namespaces) else None,merge_inputs=inputs,
        complete_hd_pack=False,visual_quality_validated=False)
    (output/'sample.json').write_text(json.dumps(report,indent=2)+'\n')
    verified=texture_pack.verify_sample(output)
    print(json.dumps({key:verified[key] for key in ('folder','sample_manifest_sha256','images','mip_chains')},indent=2))


if __name__=='__main__':main()
