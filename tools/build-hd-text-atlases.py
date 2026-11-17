"""Rerender existing hash-bound English labels at 4x; never translate new text."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import sampler_pack
import texture_pack
import title


def sha(data):return hashlib.sha256(data).hexdigest()


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def rectangles(plan):return [[block[k] for k in ('x','y','width','height')] for block in plan['blocks']]


def masked(data,width,height,regions):
    """Hashable outside-mask reference; no pixels outside approved rows change."""
    if len(data)!=width*height*4:raise ValueError('Invalid image extent')
    result=bytearray(data)
    for x,y,w,h in regions:
        if any(type(v) is not int for v in (x,y,w,h)) or min(x,y)<0 or min(w,h)<1 or x+w>width or y+h>height:
            raise ValueError('Text mask exceeds image')
        for row in range(y,y+h):result[(row*width+x)*4:(row*width+x+w)*4]=bytes(w*4)
    return bytes(result)


def linked_plans(catalog,report,private_root=ROOT/'private'):
    rows={(r['resource_id'],r['source_sha256'],r['texture_index']):r for r in catalog}
    chosen=[];excluded=[]
    if report.get('scope')!='verified-local-texture-text-regions':raise ValueError('Verified text-region report required')
    for resource in report['resources']:
        if resource.get('caption_layout') is True:
            excluded.append(dict(resource_id=resource['resource_id'],reason='Caption placement resource; no texture pixels to upscale'))
            continue
        for edit in resource['edits']:
            pixels=Path(edit['rgba_path']).resolve()
            if not pixels.is_relative_to(private_root.resolve()):raise ValueError('Text pixels escape private storage')
            if sha(pixels.read_bytes())!=edit['rgba_sha256']:raise ValueError('Existing English pixels changed')
            spec=pixels.parent.parent/(pixels.parent.name+'.json')
            if not spec.is_file():
                excluded.append(dict(resource_id=resource['resource_id'],texture_index=edit['texture_index'],
                    reason='No adjacent hash-bound spec; retain existing HD notice/fallback'));continue
            raw=spec.read_bytes();plan=json.loads(raw.decode('utf-8-sig'))
            render=json.loads((pixels.parent/'render.json').read_text(encoding='utf-8-sig'))
            if render.get('scope')=='local-serif-caption-atlas':
                excluded.append(dict(resource_id=resource['resource_id'],texture_index=edit['texture_index'],
                    reason='Vector caption atlas requires its own renderer; retain native translated texture'))
                continue
            if sha(raw)!=render['spec_sha256'] or sorted(rectangles(plan))!=sorted(edit['regions']):
                raise ValueError('Existing English typesetting spec or masks changed')
            row=rows.get((resource['resource_id'],resource['target_sha256'],edit['texture_index']))
            if not row or len(row['authored_levels'])!=1:raise ValueError('Current catalog does not match translated resource')
            if (render['width'],render['height'])!=(row['width'],row['height']):raise ValueError('Existing English geometry differs')
            chosen.append((row,plan,edit,sha(raw)))
    return chosen,excluded


def main():
    builder=load('archive_builder','build-archive-remaster.py');png_module=load('inventory','inventory-textures.py')
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','text-report','base-pack','output'):parser.add_argument('--'+name,type=builder.private,required=True)
    parser.add_argument('--name',action='append',help='Optional exact atlas names for a bounded pilot')
    parser.add_argument('--copy-base',action='store_true',help='Explicit legacy full-pack export; default updates the working pack in place')
    args=parser.parse_args()
    if args.output.exists():parser.error('Use fresh private output')
    revision=title.verify_inputs();base=texture_pack.verify_sample(args.base_pack)
    if base['scope']!='verified-mip-texture-pack':raise ValueError('Use a complete-chain base pack')
    catalog_raw=(args.catalog/'catalog.json').read_bytes();catalog=json.loads(catalog_raw)
    report_raw=args.text_report.read_bytes();chosen,excluded=linked_plans(catalog,json.loads(report_raw))
    if args.name:chosen=[item for item in chosen if item[0]['name'] in args.name]
    if not chosen:raise ValueError('No linked existing English specs')
    if args.output.is_relative_to(args.base_pack) or args.base_pack.is_relative_to(args.output):
        parser.error('Keep report/work output separate from the working pack')
    args.output.mkdir(parents=True);work=args.output/'work';work.mkdir()
    pack=args.output/'pack' if args.copy_base else args.base_pack
    if args.copy_base:pack.mkdir()
    gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk';scaler=work/'scale.exe';decoder=work/'decode.exe';env=title.environment()
    commands=[
        [str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
         '-I'+str(gpu),'-I'+str(title.SDK/'include'),str(ROOT/'tools/scale-mip-texture.c'),
         str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),
         '-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(scaler)],
        [str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),
         str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)]]
    with (work/'build.log').open('w') as log:
        for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    groups=json.loads(json.dumps(base['textures']));files={}
    for group in groups:
        for entry in group['levels']:
            if entry['file'] not in files:
                if args.copy_base:shutil.copyfile(args.base_pack/entry['file'],pack/entry['file'])
                files[entry['file']]=entry['sha256']
    protected={group['key'] for group in groups if group.get('origin')=='base-ui'}
    owners={group['key'] for group in groups};next_file=0
    fonts={str(path):sha(path.read_bytes()) for path in (Path('C:/Windows/Fonts/arial.ttf'),Path('C:/Windows/Fonts/arialbd.ttf'))}
    result=dict(scope='hd-existing-english-atlases-not-new-translations',framework_revision=revision,
        storage_mode='full-copy' if args.copy_base else 'in-place',pack_folder=pack.relative_to(ROOT).as_posix(),
        catalog_sha256=sha(catalog_raw),text_report_sha256=sha(report_raw),font_sha256=fonts,
        renderer_sha256=sha((ROOT/'tools/render-texture-text.ps1').read_bytes()),
        source_tool_sha256=sha(Path(__file__).read_bytes()),
        complete=False,translation_text_changed=False,assets=[],exclusions=excluded)
    def checkpoint():
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    checkpoint()
    try:
        for index,(row,original_plan,edit,spec_sha) in enumerate(chosen):
            # Reuse the global conflict/wildcard policy; never synthesize identity candidates.
            selected,refused=builder.select(catalog,re.compile(re.escape(row['name'])),True)
            signature=builder.signature(row)
            matches=[item for item in selected if item[0]==signature]
            if len(matches)!=1:raise ValueError('Existing English atlas identity is ambiguous')
            keys=[key for key in matches[0][2] if key not in protected]
            if not keys:
                result['exclusions'].append(dict(name=row['name'],reason='Existing protected vector atlas'));continue
            w,h=row['width'],row['height'];width,height=w*4,h*4
            blank=work/f'blank-{index}.png';blank.write_bytes(png_module.png(width,height,bytes(width*height*4)))
            plan=json.loads(json.dumps(original_plan));plan['source_png']=str(blank.relative_to(ROOT));plan['hd_antialias']=True
            for block in plan['blocks']:
                for field in ('x','y','width','height','font_pixels','line_height'):block[field]*=4
            if [b['paragraphs'] for b in plan['blocks']]!=[b['paragraphs'] for b in original_plan['blocks']]:
                raise ValueError('English strings changed during scaling')
            spec=work/f'spec-{index}.json';spec.write_text(json.dumps(plan,indent=2)+'\n')
            rendered=work/f'render-{index}'
            with (work/f'render-{index}.log').open('w') as log:
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'tools/render-texture-text.ps1'),'-Spec',str(spec),'-Output',str(rendered),'-PngOnly'],
                    env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
            overlay_path=work/'overlay.rgba'
            subprocess.run([str(decoder),str(rendered/'preview.png'),str(overlay_path),str(width),str(height),
                            '0','0',str(width),str(height)],env=env,check=True,timeout=30)
            overlay=overlay_path.read_bytes();regions=[[v*4 for v in rect] for rect in edit['regions']]
            if any(masked(overlay,width,height,regions)[3::4]):raise ValueError('HD glyphs exceed approved text masks: '+row['name'])
            source=args.catalog/'rgba'/(signature[0][2]+'.rgba')
            if sha(source.read_bytes())!=signature[0][2]:raise ValueError('Current atlas pixels changed')
            asset=dict(name=row['name'],resource_id=row['resource_id'],source_sha256=row['source_sha256'],
                texture_index=row['texture_index'],source_spec_sha256=spec_sha,regions=regions,
                paragraphs=[b['paragraphs'] for b in original_plan['blocks']],contexts=[])
            for wrap in (0,1,256,257):
                target=work/'scaled.rgba'
                subprocess.run([str(scaler),str(source),str(target),str(w),str(h),'4',str(wrap&1),str((wrap>>8)&1)],env=env,check=True,timeout=30)
                baseline=target.read_bytes();pixels=bytearray(baseline)
                for x,y,rw,rh in regions:
                    for iy in range(y,y+rh):
                        start=(iy*width+x)*4;end=start+rw*4;pixels[start:end]=overlay[start:end]
                if masked(pixels,width,height,regions)!=masked(baseline,width,height,regions):raise ValueError('Pixels outside text masks changed')
                png=png_module.png(width,height,pixels);digest=sha(png)
                name=next((name for name,value in files.items() if value==digest),None)
                if name is None:
                    while (pack/f'tex-{next_file:05d}-0.png').exists():next_file+=1
                    name=f'tex-{next_file:05d}-0.png';next_file+=1;(pack/name).write_bytes(png);files[name]=digest
                entry=dict(file=name,width=width,height=height,sha256=digest)
                for key in keys:
                    tagged=sampler_pack.tagged_key(key,wrap)
                    if tagged in owners:raise ValueError('Existing replacement would be overwritten: '+tagged)
                    owners.add(tagged);groups.append(dict(key=tagged,canonical_key=key,wrap=wrap,source_width=w,source_height=h,
                        factor=4,levels=[entry],origin='vector-typeset-existing-english',source_rgba_sha256=[signature[0][2]],
                        source_spec_sha256=spec_sha,text_translation=False,regions=regions))
                asset['contexts'].append(dict(wrap=wrap,levels=[entry],outside_mask_sha256=sha(masked(pixels,width,height,regions))))
            result['assets'].append(asset);checkpoint();print(json.dumps(dict(completed_atlases=len(result['assets']),selected=len(chosen),name=row['name'])),flush=True)
        if not result['assets']:raise ValueError('No new HD English atlases')
        lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
        for group in groups:lines.extend(f"{group['key']}_{level} = {entry['file']}" for level,entry in enumerate(group['levels']))
        ini=('\n'.join(lines)+'\n').encode('ascii')
        manifest=dict(scope='verified-mip-texture-pack',textures=groups,ini_sha256=sha(ini),sampler_namespace=sampler_pack.NAMESPACE,
            complete_hd_pack=False,visual_quality_validated=False,base_manifest_sha256=base['sample_manifest_sha256'],
            hd_existing_english={k:v for k,v in result.items() if k not in ('assets','exclusions')})
        if args.copy_base:
            (pack/'textures.ini').write_bytes(ini)
            (pack/'sample.json').write_text(json.dumps(manifest,indent=2)+'\n');verified=texture_pack.verify_sample(pack)
        else:
            import pack_update
            verified=pack_update.commit(pack,manifest,ini)
        result.update(complete=True,pack_manifest_sha256=verified['sample_manifest_sha256'],images=verified['images']);checkpoint()
    except Exception as error:
        result['error']=str(error);checkpoint();raise
    print(json.dumps({k:v for k,v in result.items() if k not in ('assets','exclusions')},indent=2))


if __name__=='__main__':main()
