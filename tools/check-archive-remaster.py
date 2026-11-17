"""Independently decode generated artwork PNGs and check pinned-scaler alpha."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import texture_pack
import title


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--original-scaling',action='store_true',help='Require every decoded RGBA byte to equal pinned xBRZ; no neural restoration')
    args=parser.parse_args()
    for name in ('batch','catalog','output'):
        path=getattr(args,name).resolve()
        if not path.is_relative_to(ROOT/'private'):parser.error('Use private paths')
        setattr(args,name,path)
    if args.output.exists():parser.error('Use a fresh private output')
    title.verify_inputs()
    report=json.loads((args.batch/'result.json').read_text())
    pack=(ROOT/report['pack_folder']).resolve() if report.get('storage_mode')=='in-place' else args.batch/'pack'
    if not pack.is_relative_to(ROOT/'private'):raise ValueError('Working pack must remain private')
    verified=texture_pack.verify_sample(pack)
    if args.original_scaling and report.get('scope')!='archive-original-hd-generation':
        raise ValueError('Original-scaling check requires an original-only batch')
    if report.get('complete') is not True or report.get('pack_manifest_sha256')!=verified['sample_manifest_sha256']:
        raise ValueError('Batch is incomplete or pack identity differs')
    source=(args.catalog/'catalog.json').read_bytes()
    if sha(source)!=report['catalog_sha256']:raise ValueError('Source catalog changed')
    catalog=json.loads(source);references={}
    for row in catalog:
        references[(row['resource_id'],row['source_sha256'],row['texture_index'],row['name'])]=row
    args.output.mkdir(parents=True);env=title.environment()
    gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk';scaler=args.output/'scale.exe';decoder=args.output/'decode.exe'
    commands=[
        [str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
         '-I'+str(gpu),'-I'+str(title.SDK/'include'),str(ROOT/'tools/scale-mip-texture.c'),
         str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),
         '-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(scaler)],
        [str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),
         str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)]]
    with (args.output/'build.log').open('w') as log:
        for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    checked=[];previews=[]
    for asset_index,asset in enumerate(report['assets']):
        ref=asset['references'][0]
        row=references[tuple(ref[k] for k in ('resource_id','source_sha256','texture_index','name'))]
        for context in asset['contexts']:
            wrap=context['wrap']
            if len(context['levels'])!=len(row['authored_levels']):raise ValueError('Authored mip missing')
            for level,(entry,original) in enumerate(zip(context['levels'],row['authored_levels'])):
                w,h=original['width'],original['height'];raw=args.catalog/'rgba'/(original['rgba_sha256']+'.rgba')
                if sha(raw.read_bytes())!=original['rgba_sha256']:raise ValueError('Source pixels changed')
                scaled=args.output/'baseline.rgba';decoded=args.output/'decoded.rgba'
                subprocess.run([str(scaler),str(raw),str(scaled),str(w),str(h),'4',str(wrap&1),str((wrap>>8)&1)],
                               env=env,check=True,timeout=30)
                png=pack/entry['file']
                if sha(png.read_bytes())!=entry['sha256']:raise ValueError('Generated PNG changed')
                subprocess.run([str(decoder),str(png),str(decoded),str(w*4),str(h*4),'0','0',str(w*4),str(h*4)],
                               env=env,check=True,timeout=30)
                actual=decoded.read_bytes();expected=scaled.read_bytes()
                if len(actual)!=len(expected) or actual[3::4]!=expected[3::4]:raise ValueError('PNG alpha differs from pinned scaler')
                alpha=expected[3::4]
                if 0 in alpha and any(actual[index*4:index*4+3]!=expected[index*4:index*4+3]
                                      for index,a in enumerate(alpha) if not a):
                    raise ValueError('Invisible original RGB changed')
                # Alpha already matches; unequal RGBA words therefore mean unequal RGB.
                changed=sum(a!=b for a,b in zip(memoryview(actual).cast('I'),memoryview(expected).cast('I')))
                if args.original_scaling and changed:raise ValueError('Original-only PNG pixels differ from pinned scaler')
                checked.append(dict(asset=asset_index,name=ref['name'],wrap=wrap,level=level,
                    file=entry['file'],sha256=entry['sha256'],alpha_sha256=sha(actual[3::4]),
                    changed_rgb_pixels=changed,alpha_exact=True,invisible_rgb_exact=True))
            name=f'preview-{asset_index:05d}.png'
            if context is asset['contexts'][0]:
                shutil.copyfile(pack/context['levels'][0]['file'],args.output/name)
                previews.append(dict(resource_id=ref['resource_id'],sha256=ref['source_sha256'],
                                     textures=[dict(name=ref['name'],preview=name)]))
    if not checked or (not args.original_scaling and not any(entry['changed_rgb_pixels'] for entry in checked)):
        raise ValueError('Restoration not exercised')
    (args.output/'textures.json').write_text(json.dumps(previews,indent=2)+'\n')
    result=dict(scope='independent-archive-png-alpha-check',passed=True,assets=len(report['assets']),
        png_context_levels=len(checked),all_alpha_exact=True,all_invisible_rgb_exact=True,
        all_rgba_exact=args.original_scaling,
        pack_manifest_sha256=verified['sample_manifest_sha256'],checked=checked,visual_quality_validated=False)
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checked'},indent=2))


if __name__=='__main__':main()
