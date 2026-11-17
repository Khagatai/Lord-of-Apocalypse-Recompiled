"""Precompute pinned xBRZ UI replacements without neural changes to text."""
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
import remaster_policy


def sha(raw):return hashlib.sha256(raw).hexdigest()


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def missing_contexts(keys,owners):
    return {wrap:[key for key in keys if key not in owners and sampler_pack.tagged_key(key,wrap) not in owners]
            for wrap in (0,1,256,257)}


def main():
    builder=module('archive_builder','build-archive-remaster.py');png_module=module('inventory','inventory-textures.py')
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','base-pack','output'):parser.add_argument('--'+name,type=builder.private,required=True)
    parser.add_argument('--pattern',required=True)
    parser.add_argument('--copy-base',action='store_true',help='Explicit legacy full-pack export; default updates the working pack in place')
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a fresh private output')
    revision=title.verify_inputs();base=texture_pack.verify_sample(args.base_pack)
    if base['scope']!='verified-mip-texture-pack':raise ValueError('Complete-chain base pack required')
    catalog_raw=(args.catalog/'catalog.json').read_bytes()
    if json.loads((args.catalog/'result.json').read_text()).get('exported_rgba') is not True:raise ValueError('RGBA exports required')
    catalog=json.loads(catalog_raw)
    # Only tagged, nonzero pack keys are emitted below. A zero source hash is
    # legitimate PSP data; its XOR-tagged identity is not an INI wildcard.
    chosen,excluded=builder.select(catalog,re.compile(args.pattern),True,minimum_dimension=1,allow_zero_source_hash=True)
    chosen,originals=remaster_policy.exclude_portraits(chosen,catalog);excluded.extend(originals)
    if not chosen:raise ValueError('No supported unambiguous selected UI artwork')
    if args.output.is_relative_to(args.base_pack) or args.base_pack.is_relative_to(args.output):
        parser.error('Keep report/work output separate from the working pack')
    args.output.mkdir(parents=True);pack=args.output/'pack' if args.copy_base else args.base_pack
    if args.copy_base:pack.mkdir()
    work=args.output/'work';work.mkdir()
    env=title.environment();gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk';scaler=work/'scale.exe'
    command=[str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
        '-I'+str(gpu),'-I'+str(title.SDK/'include'),str(ROOT/'tools/scale-mip-texture.c'),str(gpu/'tex_scale.c'),
        str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),'-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(scaler)]
    with (work/'build.log').open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    groups=json.loads(json.dumps(base['textures']));files={}
    for group in groups:
        for entry in group['levels']:
            if entry['file'] not in files:
                if args.copy_base:shutil.copyfile(args.base_pack/entry['file'],pack/entry['file'])
                files[entry['file']]=entry['sha256']
    owners={group['key'] for group in groups};assets=[];next_file=0
    for sig,rows,keys in chosen:
        pending=missing_contexts(keys,owners)
        existing=[key for key in keys if any(key not in pending[w] for w in pending)]
        if existing:excluded.append(dict(name=rows[0]['name'],keys=existing,reason='Existing replacements retained; only missing contexts generated'))
        keys=[key for key in keys if any(key in pending[w] for w in pending)]
        if not keys:continue
        refs=[{k:r[k] for k in ('resource_id','source_sha256','texture_index','name')} for r in rows]
        asset=dict(references=refs,canonical_keys=keys,contexts=[])
        for wrap in (0,1,256,257):
            if not pending[wrap]:continue
            entries=[]
            for level,(w,h,digest) in enumerate(sig):
                source=args.catalog/'rgba'/(digest+'.rgba');raw=source.read_bytes()
                if len(raw)!=w*h*4 or sha(raw)!=digest:raise ValueError('Source export changed')
                target=work/'scaled.rgba'
                subprocess.run([str(scaler),str(source),str(target),str(w),str(h),'4',str(wrap&1),str((wrap>>8)&1)],env=env,check=True,timeout=30)
                data=target.read_bytes()
                if len(data)!=w*h*64:raise ValueError('Scaled output extent differs')
                png=png_module.png(w*4,h*4,data);png_sha=sha(png)
                name=next((name for name,digest in files.items() if digest==png_sha),None)
                if name is None:
                    while (pack/f'tex-{next_file:05d}-{level}.png').exists():next_file+=1
                    name=f'tex-{next_file:05d}-{level}.png';next_file+=1
                    (pack/name).write_bytes(png);files[name]=png_sha
                entries.append(dict(file=name,width=w*4,height=h*4,sha256=png_sha))
            for key in pending[wrap]:
                tagged=sampler_pack.tagged_key(key,wrap)
                if tagged in owners:raise ValueError('Existing texture identity would be replaced: '+tagged)
                owners.add(tagged)
                groups.append(dict(key=tagged,canonical_key=key,wrap=wrap,source_width=sig[0][0],source_height=sig[0][1],
                    factor=4,levels=entries,origin='scaled-authored-ui',source_rgba_sha256=[l[2] for l in sig],
                    archive_references=refs,neural_restoration=False,text_translation=False))
            asset['contexts'].append(dict(wrap=wrap,levels=entries,method='exact-pinned-xbrz'))
        assets.append(asset)
        if len(assets)%16==0:
            print(json.dumps(dict(completed_assets=len(assets),new_images=len(files)-base['images'])),flush=True)
    if not assets:raise ValueError('All selected UI keys already have replacements')
    lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
    for group in groups:lines.extend(f"{group['key']}_{level} = {entry['file']}" for level,entry in enumerate(group['levels']))
    ini=('\n'.join(lines)+'\n').encode('ascii')
    report=dict(scope='verified-mip-texture-pack',textures=groups,ini_sha256=sha(ini),sampler_namespace=sampler_pack.NAMESPACE,
        complete_hd_pack=False,visual_quality_validated=False,base_manifest_sha256=base['sample_manifest_sha256'],
        source_tool_sha256=sha(Path(__file__).read_bytes()))
    if args.copy_base:
        (pack/'textures.ini').write_bytes(ini)
        (pack/'sample.json').write_text(json.dumps(report,indent=2)+'\n');verified=texture_pack.verify_sample(pack)
    else:
        import pack_update
        verified=pack_update.commit(pack,report,ini)
    result=dict(scope='archive-original-hd-generation',framework_revision=revision,catalog_sha256=sha(catalog_raw),
        storage_mode='full-copy' if args.copy_base else 'in-place',pack_folder=pack.relative_to(ROOT).as_posix(),
        pattern=args.pattern,complete=True,neural_restoration=False,text_translation=False,assets=assets,exclusions=excluded,
        pack_manifest_sha256=verified['sample_manifest_sha256'],images=verified['images'],mip_chains=verified['mip_chains'])
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ('assets','exclusions')},indent=2))


if __name__=='__main__':main()
