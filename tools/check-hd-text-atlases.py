"""Independently check HD English PNG masks against current source and old wording."""
import argparse
import hashlib
import importlib.util
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
    spec=importlib.util.spec_from_file_location('hd_text',ROOT/'tools/build-hd-text-atlases.py')
    hd=importlib.util.module_from_spec(spec);spec.loader.exec_module(hd)
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('batch','catalog','text-report','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    for name in ('batch','catalog','text_report','output'):
        path=getattr(args,name).resolve()
        if not path.is_relative_to(ROOT/'private'):parser.error('Use private paths')
        setattr(args,name,path)
    if args.output.exists():parser.error('Use fresh private output')
    title.verify_inputs()
    report_raw=(args.batch/'result.json').read_bytes();report=json.loads(report_raw)
    pack=(ROOT/report['pack_folder']).resolve() if report.get('storage_mode')=='in-place' else args.batch/'pack'
    if not pack.is_relative_to(ROOT/'private'):raise ValueError('Working pack must remain private')
    verified=texture_pack.verify_sample(pack)
    if (report.get('scope')!='hd-existing-english-atlases-not-new-translations' or report.get('complete') is not True or
        report.get('pack_manifest_sha256')!=verified['sample_manifest_sha256']):raise ValueError('Incomplete or changed HD batch')
    catalog_raw=(args.catalog/'catalog.json').read_bytes();text_raw=args.text_report.read_bytes()
    if sha(catalog_raw)!=report['catalog_sha256'] or sha(text_raw)!=report['text_report_sha256']:raise ValueError('Current sources differ')
    linked,excluded=hd.linked_plans(json.loads(catalog_raw),json.loads(text_raw))
    references={(r['resource_id'],r['source_sha256'],r['texture_index']):(r,p,e,d) for r,p,e,d in linked}
    args.output.mkdir(parents=True);env=title.environment();gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk'
    scaler=args.output/'scale.exe';decoder=args.output/'decode.exe'
    commands=[
        [str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
         '-I'+str(gpu),'-I'+str(title.SDK/'include'),str(ROOT/'tools/scale-mip-texture.c'),
         str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),
         '-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(scaler)],
        [str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),
         str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)]]
    with (args.output/'build.log').open('w') as log:
        for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    checked=[];previews=[];labels=[]
    label_folder=args.output/'label-regions';label_folder.mkdir()
    png_module=hd.load('inventory','inventory-textures.py')
    for index,asset in enumerate(report['assets']):
        row,plan,edit,digest=references[(asset['resource_id'],asset['source_sha256'],asset['texture_index'])]
        paragraphs=[block['paragraphs'] for block in plan['blocks']]
        if paragraphs!=asset['paragraphs'] or digest!=asset['source_spec_sha256']:
            raise ValueError('Existing English wording/spec differs')
        regions=[[v*4 for v in rect] for rect in edit['regions']]
        if regions!=asset['regions']:raise ValueError('HD masks differ from approved text regions')
        if sorted(c['wrap'] for c in asset['contexts'])!=[0,1,256,257]:raise ValueError('A sampling context is missing')
        w,h=row['width'],row['height'];width,height=w*4,h*4
        source=args.catalog/'rgba'/(row['authored_levels'][0]['rgba_sha256']+'.rgba')
        if sha(source.read_bytes())!=row['authored_levels'][0]['rgba_sha256']:raise ValueError('Source pixels changed')
        for context in asset['contexts']:
            if len(context['levels'])!=1:raise ValueError('Unexpected UI mip count')
            entry=context['levels'][0];image=pack/entry['file']
            if sha(image.read_bytes())!=entry['sha256']:raise ValueError('HD PNG changed')
            baseline=args.output/'baseline.rgba';decoded=args.output/'decoded.rgba';wrap=context['wrap']
            subprocess.run([str(scaler),str(source),str(baseline),str(w),str(h),'4',str(wrap&1),str((wrap>>8)&1)],env=env,check=True,timeout=30)
            subprocess.run([str(decoder),str(image),str(decoded),str(width),str(height),'0','0',str(width),str(height)],env=env,check=True,timeout=30)
            actual=decoded.read_bytes();expected=baseline.read_bytes()
            outside=hd.masked(actual,width,height,regions)
            if outside!=hd.masked(expected,width,height,regions) or sha(outside)!=context['outside_mask_sha256']:
                raise ValueError('Pixels outside English masks changed')
            changed=sum(a!=b for a,b in zip(memoryview(actual).cast('I'),memoryview(expected).cast('I')))
            checked.append(dict(name=asset['name'],wrap=wrap,file=entry['file'],sha256=entry['sha256'],
                unchanged_english_wording=True,outside_text_masks_exact=True,changed_inside_pixels=changed,
                paragraphs_sha256=sha(json.dumps(paragraphs,ensure_ascii=False).encode())))
        name=f'preview-{index:05d}.png';shutil.copyfile(pack/asset['contexts'][0]['levels'][0]['file'],args.output/name)
        previews.append(dict(resource_id=asset['resource_id'],sha256=asset['source_sha256'],textures=[dict(name=asset['name'],preview=name)]))
        for block,(x,y,rw,rh) in enumerate(regions):
            crop=b''.join(actual[(iy*width+x)*4:(iy*width+x+rw)*4] for iy in range(y,y+rh))
            name=f'label-{len(labels):04d}.png';(label_folder/name).write_bytes(png_module.png(rw,rh,crop))
            labels.append(dict(resource_id=asset['resource_id'],sha256=asset['source_sha256'],
                textures=[dict(name=f"{asset['name']} #{block}",preview=name)],paragraphs=paragraphs[block]))
    if not checked or not any(row['changed_inside_pixels'] for row in checked):raise ValueError('HD text rendering not exercised')
    (args.output/'textures.json').write_text(json.dumps(previews,indent=2)+'\n')
    (label_folder/'textures.json').write_text(json.dumps(labels,indent=2)+'\n')
    result=dict(scope='independent-hd-existing-english-check',passed=True,atlases=len(report['assets']),
        png_contexts=len(checked),all_existing_wording_unchanged=True,all_pixels_outside_masks_exact=True,
        pack_manifest_sha256=verified['sample_manifest_sha256'],batch_report_sha256=sha(report_raw),
        checked=checked,visual_quality_validated=False)
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='checked'},indent=2))


if __name__=='__main__':main()
