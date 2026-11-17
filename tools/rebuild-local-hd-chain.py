"""Rebuild one private HD mip chain from local English archives, without copying a pack.

This is a reproducibility pilot, not the complete HD installer. Active textures,
original ISO, saves and preferences are never changed.
"""
import argparse,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,neural_texture,remaster_policy
from rgf_archive import parse_index,read_group
from xet_codec import Xet


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archives',type=Path,required=True)
    p.add_argument('--key',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--audit',type=Path,default=ROOT/'private/local-build/hd-source-audit.json')
    p.add_argument('--neural-tool',type=Path,default=ROOT/'private/tools/realesrgan-20220424/package')
    a=p.parse_args();out=a.output.resolve()
    for path in (out,a.archives,a.audit,a.neural_tool):
        if not path.resolve().is_relative_to(ROOT/'private'):raise ValueError('Keep local HD inputs and outputs private')
    if out.is_relative_to(ROOT/'private/hd-remaster-pack') or out.is_relative_to(a.archives.resolve()):
        raise ValueError('Keep bounded HD work separate from active textures and source archives')
    if out.exists():raise ValueError('Use fresh, bounded chain work storage')
    revision=title.verify_inputs();audit=json.loads(a.audit.read_text());manifest=(ROOT/'private/hd-remaster-pack/sample.json').read_bytes()
    if sha(manifest)!=audit['pack_manifest_sha256']:raise ValueError('Reference HD manifest changed')
    group=next((g for g in json.loads(manifest)['textures'] if g['key']==a.key),None)
    if group is None or not audit['bindings'].get(a.key):raise ValueError('No verified archive source for this HD key')
    if group['origin'] not in ('offline-restored-world','offline-restored-masked','offline-restored-archive','scaled-authored-world','scaled-authored-ui'):
        raise ValueError('HD processing recipe is not implemented for this origin')
    ref=audit['bindings'][a.key][0]
    if remaster_policy.original_portrait(ref['name']):raise ValueError('Dialogue portrait must retain original artwork')
    rzl=(a.archives/'REGFILE.RZL').read_bytes();rzp=a.archives/'REGFILE.RZP'
    with rzp.open('rb') as stream:
        if sha(rzl)!=audit['index_sha256'] or hashlib.file_digest(stream,'sha256').hexdigest()!=audit['archive_sha256']:
            raise ValueError('Audited English archives changed')
        groups=parse_index(rzl,rzp.stat().st_size);source=groups[ref['group_index']];plain=read_group(stream,source);offset=0;raw=None
        for length,identity in source.entries:
            item=plain[offset:offset+length];offset+=length
            if identity==int(ref['resource_id'],16) and sha(item)==ref['source_sha256']:raw=item;break
    if raw is None:raise ValueError('Measured archive resource not found')
    xet=Xet.parse(raw);texture=xet.textures[ref['texture_index']]
    if texture.name!=ref['name'] or len(texture.mips)!=len(group['levels']):raise ValueError('Source texture/mip identity differs')
    restored=group['origin'].startswith('offline-restored-');model=group.get('model','realesrgan-x4plus');wrap=group['wrap'];levels=[]
    pins=neural_texture.processing_pins(neural_texture.verify_tool(a.neural_tool),model) if restored else None
    out.mkdir(parents=True);work=out/'work';work.mkdir();env=title.environment();gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk'
    scaler=work/'scale.exe';decoder=work/'decode.exe';compiler=str(title.SDK/'bin/gcc.exe')
    commands=[
        [compiler,'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-I'+str(gpu),'-I'+str(title.SDK/'include'),
         str(ROOT/'tools/scale-mip-texture.c'),str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),'-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(scaler)],
        [compiler,'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)]]
    sharp=None
    if group.get('detail_pass'):
        if group['detail_pass']!='gaussian5-detail25-cap6-alpha-preserved-v1':raise ValueError('Unknown player detail recipe')
        sharp=work/'sharpen.exe'
        commands.append([compiler,'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),str(ROOT/'tools/sharpen-model-texture.c'),'-o',str(sharp)])
    with (work/'build.log').open('w') as log:
        for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    spec=importlib.util.spec_from_file_location('chain_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)
    for level,expected in enumerate(group['levels']):
        w,h,pixels=xet.preview_mip(ref['texture_index'],level,limit=512)
        if sha(pixels)!=group['source_rgba_sha256'][level]:raise ValueError('HD source pixels changed')
        source_path=work/'input.rgba';source_path.write_bytes(pixels);baseline_path=work/'baseline.rgba'
        subprocess.run([str(scaler),str(source_path),str(baseline_path),str(w),str(h),'4',str(wrap&1),str((wrap>>8)&1)],env=env,check=True,timeout=30)
        baseline=baseline_path.read_bytes();result=baseline
        if restored and any(pixels[3::4]):
            padded=neural_texture.pad_opaque(neural_texture.masked_colours(pixels,w,h,wrap),w,h,64,wrap)
            source_png=work/'input.png';source_png.write_bytes(png.png(w+128,h+128,padded));restored_png=work/'restored.png';result_path=work/'restored.rgba'
            with (work/f'inference-{level}.log').open('w') as log:
                subprocess.run([str(a.neural_tool.resolve()/'realesrgan-ncnn-vulkan.exe'),'-i',str(source_png),'-o',str(restored_png),
                    '-m',str(a.neural_tool.resolve()/'models'),'-n',model,'-s','4','-t','128','-j','1:1:1'],env=env,cwd=work,
                    stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            subprocess.run([str(decoder),str(restored_png),str(result_path),str((w+128)*4),str((h+128)*4),'256','256',str(w*4),str(h*4)],env=env,check=True,timeout=30)
            result=neural_texture.merge_cutout_colours(result_path.read_bytes(),baseline)
        if len(result)!=w*h*64 or result[3::4]!=baseline[3::4]:raise ValueError('HD dimensions/alpha differ')
        target=out/f'level-{level}.png';target.write_bytes(png.png(w*4,h*4,result))
        if sharp:
            sharp_path=work/'sharpened.rgba';subprocess.run([str(sharp),str(target),str(sharp_path)],env=env,check=True,timeout=30)
            result=sharp_path.read_bytes()
            if len(result)!=len(baseline) or result[3::4]!=baseline[3::4]:raise ValueError('Player detail pass changed alpha')
            target.write_bytes(png.png(w*4,h*4,result))
        levels.append(dict(level=level,width=w*4,height=h*4,sha256=sha(target.read_bytes()),
            exact_reference_match=sha(target.read_bytes())==expected['sha256'],alpha_preserved=True))
        print('Rebuilt HD mip:',level,flush=True)
    report=dict(status='GENERATED',framework_revision=revision,key=a.key,source=ref,origin=group['origin'],model_pins=pins,
        levels=levels,all_reference_hashes_match=all(l['exact_reference_match'] for l in levels),
        pack_copied=False,active_pack_changed=False,HD_installer_complete=False)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
