"""Restore deduplicated opaque archive artwork offline for review, never installation.

Unseen sampler modes are unknown. These clamped-context candidates have no INI,
cannot be selected as a game pack, and require edge/sampler/native validation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import neural_texture
import title


def sha(raw):return hashlib.sha256(raw).hexdigest()


def private(value):
    path=Path(value).resolve()
    if not path.is_relative_to(ROOT/'private'):
        raise ValueError('All artwork and model files must stay private')
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=private,required=True)
    parser.add_argument('--neural-tool',type=private,required=True)
    parser.add_argument('--output',type=private,required=True)
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--limit',type=int,choices=range(1,2049),default=32)
    args=parser.parse_args()
    if args.output.exists() or args.offset<0:
        parser.error('Use a fresh output directory and nonnegative offset')
    revision=title.verify_inputs();pins=neural_texture.verify_tool(args.neural_tool)
    report=json.loads((args.catalog/'result.json').read_text())
    if report.get('exported_rgba') is not True:
        raise ValueError('Catalog must include private RGBA exports')
    source=(args.catalog/'catalog.json').read_bytes();catalog=json.loads(source)
    chains={}
    for row in catalog:
        levels=row['authored_levels']
        if len(levels)<2 or not all(l.get('opaque') is True and 'rgba_sha256' in l for l in levels):continue
        if min(row['width'],row['height'])<32:continue
        signature=tuple((l['width'],l['height'],l['rgba_sha256']) for l in levels)
        chains.setdefault(signature,[]).append(row)
    ordered=sorted(chains.items(),key=lambda pair:(-pair[0][0][0]*pair[0][0][1],pair[0]))
    chosen=ordered[args.offset:args.offset+args.limit]
    if not chosen:raise ValueError('No opaque complete chains at requested offset')
    args.output.mkdir(parents=True);work=args.output/'work';work.mkdir()
    decoder=args.output/'decode-png.exe';env=title.environment()
    with (args.output/'decoder-build.log').open('w') as log:
        subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),
                        str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)],env=env,
                       stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/inventory-textures.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=dict(scope='offline-artwork-candidates-not-installed',framework_revision=revision,
                catalog_sha256=sha(source),model_pins=pins,eligible_unique_chains=len(ordered),
                requested_offset=args.offset,requested_limit=args.limit,context='clamp-both-axes',
                sampler_mode_measured=False,pack_created=False,visual_review_complete=False,
                completed=False,assets=[])
    def checkpoint():
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    checkpoint()
    try:
        for position,(signature,references) in enumerate(chosen,args.offset):
            directory=args.output/f'asset-{position:05d}';directory.mkdir()
            asset=dict(index=position,references=[dict(resource_id=r['resource_id'],
                       source_sha256=r['source_sha256'],texture_index=r['texture_index'],name=r['name'])
                       for r in references],levels=[])
            for level,(width,height,digest) in enumerate(signature):
                raw=(args.catalog/'rgba'/(digest+'.rgba')).read_bytes()
                if sha(raw)!=digest or len(raw)!=width*height*4:
                    raise ValueError('Source RGBA geometry/hash differs')
                border=64;pw=width+2*border;ph=height+2*border
                padded=neural_texture.pad_opaque(raw,width,height,border,257)
                input_file=work/f'{position}-{level}-input.png'
                input_file.write_bytes(module.png(pw,ph,padded))
                restored=work/f'{position}-{level}-restored.png'
                with (work/f'{position}-{level}-inference.log').open('w') as log:
                    subprocess.run([str(args.neural_tool/'realesrgan-ncnn-vulkan.exe'),
                       '-i',str(input_file),'-o',str(restored),'-m',str(args.neural_tool/'models'),
                       '-n','realesrgan-x4plus','-s','4','-t','128','-j','1:1:1'],env=env,
                       cwd=work,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
                rgba=work/f'{position}-{level}-cropped.rgba'
                subprocess.run([str(decoder),str(restored),str(rgba),str(pw*4),str(ph*4),
                                '256','256',str(width*4),str(height*4)],env=env,check=True,timeout=30)
                pixels=rgba.read_bytes()
                if len(pixels)!=width*height*64 or any(a!=255 for a in pixels[3::4]):
                    raise ValueError('Candidate geometry or opaque alpha differs')
                png=module.png(width*4,height*4,pixels);name=f'level-{level}.png'
                (directory/name).write_bytes(png)
                asset['levels'].append(dict(file=str((directory/name).relative_to(args.output)),
                    width=width*4,height=height*4,source_rgba_sha256=digest,sha256=sha(png)))
            result['assets'].append(asset);checkpoint()
            print(json.dumps(dict(completed_assets=len(result['assets']),index=position)),flush=True)
        result['completed']=True;checkpoint()
    except Exception as error:
        result['error']=str(error);checkpoint();raise
    print(json.dumps({k:v for k,v in result.items() if k not in ('assets','model_pins')},indent=2),flush=True)


if __name__=='__main__':main()
