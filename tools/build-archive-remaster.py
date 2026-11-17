"""Build private, sampler-aware HD artwork batches from exact archive exports.

Explicit name selection keeps text and unreviewed effects out of artwork batches.
Every selected wrap context is restored independently. Cache entries are bound to
the actual inference input, pinned model, alpha reference and processing sources.
"""
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
import neural_texture
import sampler_pack
import texture_pack
import title
import remaster_policy
import archive_identity


def sha(raw):return hashlib.sha256(raw).hexdigest()


def private(value):
    path=Path(value).resolve()
    if not path.is_relative_to(ROOT/'private'):raise ValueError('Artwork must remain private')
    return path


def signature(row):
    levels=row.get('authored_levels',[])
    if not levels or len(levels)!=row.get('mip_levels'):return None
    if any(not re.fullmatch('[0-9a-f]{64}',level.get('rgba_sha256','')) for level in levels):return None
    return tuple((level['width'],level['height'],level['rgba_sha256']) for level in levels)


def select(catalog,pattern,allow_alpha,alpha_only=False,minimum_dimension=32,allow_zero_source_hash=False):
    """Exclude key conflicts across the entire catalog, not just the selection."""
    identities={};chains={};excluded=[]
    for row in catalog:
        sig=signature(row)
        for key in row.get('candidate_keys',[]):identities.setdefault(key,set()).add(sig)
        if not pattern.fullmatch(row['name']):continue
        if sig is None:excluded.append(dict(name=row['name'],reason='incomplete decode'));continue
        w,h,_=sig[0]
        if not minimum_dimension<=min(w,h)<=max(w,h)<=512 or w&(w-1) or h&(h-1):
            excluded.append(dict(name=row['name'],reason='unsupported geometry'));continue
        if any((lw*4,lh*4)!=(max(1,w*4>>i),max(1,h*4>>i)) for i,(lw,lh,_) in enumerate(sig)):
            excluded.append(dict(name=row['name'],reason='thin-tail resampling required'));continue
        if not allow_alpha and not all(level.get('opaque') is True for level in row['authored_levels']):
            excluded.append(dict(name=row['name'],reason='alpha not admitted'));continue
        if alpha_only and all(level.get('opaque') is True for level in row['authored_levels']):
            excluded.append(dict(name=row['name'],reason='opaque asset outside alpha-only selection'));continue
        chains.setdefault(sig,[]).append(row)
    selected=[]
    resolved={key:archive_identity.longest_compatible(sigs) for key,sigs in identities.items()}
    for sig,rows in sorted(chains.items()):
        keys=set()
        for row in rows:
            for key in row['candidate_keys']:
                if not re.fullmatch('[0-9a-f]{24}',key) or (int(key[-8:],16)==0 and not allow_zero_source_hash) or resolved[key] is None:
                    excluded.append(dict(name=row['name'],key=key,reason='ambiguous or wildcard identity'))
                elif resolved[key]!=sig:
                    excluded.append(dict(name=row['name'],key=key,reason='compatible shorter mip alias uses full chain'))
                else:keys.add(key)
        if keys:selected.append((sig,rows,sorted(keys)))
    return selected,excluded


def uncovered(selected,base):
    """Protect every existing canonical and tagged identity from replacement."""
    owners={g['key'] for g in base['textures']};chosen=[];excluded=[]
    for entry in selected:
        keys=entry[2]
        if any(key in owners or any(sampler_pack.tagged_key(key,wrap) in owners for wrap in (0,1,256,257)) for key in keys):
            excluded.extend(dict(name=row['name'],reason='existing replacement retained') for row in entry[1])
        else:chosen.append(entry)
    return chosen,excluded


def incomplete_contexts(selected,base,contexts=(0,1,256,257)):
    """Add precise sampler variants while retaining existing legacy fallbacks."""
    owners={g['key'] for g in base['textures']}
    return [entry for entry in selected if any(sampler_pack.tagged_key(key,wrap) not in owners
            for key in entry[2] for wrap in contexts)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','base-pack','neural-tool','output'):
        parser.add_argument('--'+name,type=private,required=True)
    parser.add_argument('--cache',type=private,help='Optional existing verified inference cache')
    parser.add_argument('--keep-cache',action='store_true',help='Explicitly retain newly inferred PNG cache copies')
    parser.add_argument('--copy-base',action='store_true',help='Legacy full-pack export; ordinary edits update the base pack in place')
    parser.add_argument('--pattern',required=True,help='Full-match archive texture name expression')
    parser.add_argument('--model',choices=('realesrgan-x4plus','realesrgan-x4plus-anime'),default='realesrgan-x4plus')
    parser.add_argument('--contexts',nargs='+',type=int,choices=(0,1,256,257),default=[0,1,256,257])
    parser.add_argument('--allow-alpha',action='store_true',help='Restore RGB with exact pinned xBRZ alpha')
    parser.add_argument('--alpha-only',action='store_true',help='Select only nonopaque source chains; implies --allow-alpha')
    parser.add_argument('--skip-existing',action='store_true',help='Protect existing canonical and sampler-context replacements')
    parser.add_argument('--complete-contexts',action='store_true',help='Add only missing sampler variants, retaining existing canonical fallback images')
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--limit',type=int,default=2048)
    args=parser.parse_args()
    if args.offset<0 or not 1<=args.limit<=8192 or len(set(args.contexts))!=len(args.contexts):
        parser.error('Use nonnegative offset, bounded limit and distinct contexts')
    if args.output==args.base_pack or args.output.is_relative_to(args.base_pack) or args.base_pack.is_relative_to(args.output):
        parser.error('The report/work folder must be separate from the working pack')
    if args.output.exists():
        previous=args.output/'result.json'
        if args.copy_base or not previous.is_file() or json.loads(previous.read_text()).get('storage_mode')!='in-place':
            parser.error('Reuse only an owned in-place report/work folder; full exports require fresh output')
    args.cache=args.cache or args.output/'cache'
    revision=title.verify_inputs();pins=neural_texture.verify_tool(args.neural_tool)
    model_pins=neural_texture.processing_pins(pins,args.model)
    base=texture_pack.verify_sample(args.base_pack)
    if base['scope']!='verified-mip-texture-pack':raise ValueError('Use a verified complete-chain base pack')
    catalog_raw=(args.catalog/'catalog.json').read_bytes()
    if json.loads((args.catalog/'result.json').read_text()).get('exported_rgba') is not True:
        raise ValueError('Catalog has no exact RGBA exports')
    catalog=json.loads(catalog_raw)
    selected,excluded=select(catalog,re.compile(args.pattern),args.allow_alpha or args.alpha_only,args.alpha_only)
    selected,originals=remaster_policy.exclude_portraits(selected,catalog);excluded.extend(originals)
    if args.complete_contexts:
        if args.copy_base:parser.error('Complete missing contexts in the working pack only')
        selected=incomplete_contexts(selected,base,args.contexts)
    elif args.skip_existing or not args.copy_base:
        selected,retained=uncovered(selected,base);excluded.extend(retained)
    chosen=selected[args.offset:args.offset+args.limit]
    if not chosen:raise ValueError('No admissible artwork at requested offset')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.keep_cache:args.cache.mkdir(parents=True,exist_ok=True)
    work=args.output/'work';work.mkdir(exist_ok=True)
    pack=args.output/'pack' if args.copy_base else args.base_pack
    if args.copy_base:pack.mkdir()
    env=title.environment();gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk'
    scaler=work/'scale.exe';decoder=work/'decode.exe'
    commands=[
        [str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-Wl,--no-insert-timestamp',
         '-I'+str(gpu),'-I'+str(title.SDK/'include'),str(ROOT/'tools/scale-mip-texture.c'),
         str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),
         '-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(scaler)],
        [str(title.SDK/'bin/gcc.exe'),'-O2','-Wl,--no-insert-timestamp','-I'+str(title.FRAMEWORK/'third_party/stb'),
         str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)]]
    with (work/'build.log').open('w') as log:
        for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/inventory-textures.py')
    png_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(png_module)
    source_pins={name:sha((ROOT/name).read_bytes()) for name in (
        'tools/build-archive-remaster.py','tools/neural_texture.py','tools/scale-mip-texture.c',
        'tools/decode-private-png.c')}
    source_pins.update(scaler=sha(scaler.read_bytes()),decoder=sha(decoder.read_bytes()))
    groups=json.loads(json.dumps(base['textures']));files={}
    for group in groups:
        for level in group['levels']:
            name=level['file']
            if name not in files:
                if args.copy_base:shutil.copyfile(args.base_pack/name,pack/name)
                files[name]=level['sha256']
    owners={group['key']:None for group in groups};next_file=0
    def add_png(data,w,h,level):
        nonlocal next_file
        digest=sha(data)
        name=next((name for name,value in files.items() if value==digest),None)
        if name is None:
            while (pack/f'tex-{next_file:05d}-{level}.png').exists():next_file+=1
            name=f'tex-{next_file:05d}-{level}.png';next_file+=1
            (pack/name).write_bytes(data);files[name]=digest
        return dict(file=name,width=w,height=h,sha256=digest)
    result=dict(scope='archive-hd-batch-generation',framework_revision=revision,
        storage_mode='full-copy' if args.copy_base else 'in-place',pack_folder=pack.relative_to(ROOT).as_posix(),
        catalog_sha256=sha(catalog_raw),base_manifest_sha256=base['sample_manifest_sha256'],
        pattern=args.pattern,offset=args.offset,eligible_assets=len(selected),selected_assets=len(chosen),
        contexts=args.contexts,model=args.model,processing_pins=model_pins,source_pins=source_pins,
        alpha_only=args.alpha_only,skip_existing=args.skip_existing,complete_contexts=args.complete_contexts,
        exclusions=excluded,completed_assets=0,inferences=0,cache_hits=0,alpha_planes_checked=0,
        complete=False,complete_hd_pack=False,visual_quality_validated=False,assets=[])
    def checkpoint():
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    checkpoint()
    try:
        for index,(sig,rows,keys) in enumerate(chosen,args.offset):
            references=[{k:row[k] for k in ('resource_id','source_sha256','texture_index','name')} for row in rows]
            asset=dict(index=index,references=references,canonical_keys=keys,contexts=[])
            for wrap in args.contexts:
                pending_keys=[key for key in keys if sampler_pack.tagged_key(key,wrap) not in owners] if args.complete_contexts else keys
                if not pending_keys:continue
                entries=[]
                for level,(w,h,digest) in enumerate(sig):
                    raw_path=args.catalog/'rgba'/(digest+'.rgba');raw=raw_path.read_bytes()
                    if sha(raw)!=digest or len(raw)!=w*h*4:raise ValueError('Source export changed')
                    baseline_path=work/'baseline.rgba'
                    subprocess.run([str(scaler),str(raw_path),str(baseline_path),str(w),str(h),'4',
                                    str(wrap&1),str((wrap>>8)&1)],env=env,check=True,timeout=30)
                    baseline=baseline_path.read_bytes()
                    if len(baseline)!=w*h*64:raise ValueError('Scaled alpha reference extent differs')
                    if not any(raw[3::4]):
                        pixels=baseline;method='fully-transparent-original'
                    else:
                        coloured=neural_texture.masked_colours(raw,w,h,wrap)
                        padded=neural_texture.pad_opaque(coloured,w,h,64,wrap)
                        input_png=png_module.png(w+128,h+128,padded)
                        identity=dict(input_sha256=sha(input_png),baseline_sha256=sha(baseline),
                                      model=model_pins,sources=source_pins,width=w,height=h,border=64)
                        cache_id=sha(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())
                        cache_png=args.cache/(cache_id+'.png');cache_json=args.cache/(cache_id+'.json')
                        pixels_path=work/'result.rgba'
                        if cache_png.exists() and cache_json.exists():
                            saved=json.loads(cache_json.read_text())
                            if saved.get('identity')!=identity or saved.get('sha256')!=sha(cache_png.read_bytes()):
                                raise ValueError('Cached artwork identity differs')
                            subprocess.run([str(decoder),str(cache_png),str(pixels_path),str(w*4),str(h*4),
                                            '0','0',str(w*4),str(h*4)],
                                           env=env,check=True,timeout=30)
                            pixels=pixels_path.read_bytes();result['cache_hits']+=1
                        else:
                            source=work/'input.png';source.write_bytes(input_png);restored=work/'restored.png'
                            with (work/f'{index}-{wrap}-{level}.log').open('w') as log:
                                subprocess.run([str(args.neural_tool/'realesrgan-ncnn-vulkan.exe'),'-i',str(source),
                                    '-o',str(restored),'-m',str(args.neural_tool/'models'),'-n',args.model,
                                    '-s','4','-t','128','-j','1:1:1'],env=env,cwd=work,
                                    stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
                            subprocess.run([str(decoder),str(restored),str(pixels_path),str((w+128)*4),str((h+128)*4),
                                            '256','256',str(w*4),str(h*4)],env=env,check=True,timeout=30)
                            pixels=neural_texture.merge_cutout_colours(pixels_path.read_bytes(),baseline)
                            png=png_module.png(w*4,h*4,pixels)
                            if args.keep_cache:
                                temporary=args.cache/(cache_id+'.partial');temporary.write_bytes(png);temporary.replace(cache_png)
                                temporary.write_text(json.dumps(dict(identity=identity,sha256=sha(png)),sort_keys=True))
                                temporary.replace(cache_json)
                            result['inferences']+=1
                        method='offline-restored-exact-xbrz-alpha'
                    if len(pixels)!=len(baseline) or pixels[3::4]!=baseline[3::4]:raise ValueError('Restored alpha differs')
                    result['alpha_planes_checked']+=1
                    entries.append(add_png(png_module.png(w*4,h*4,pixels),w*4,h*4,level))
                for key in pending_keys:
                    tagged=sampler_pack.tagged_key(key,wrap)
                    if tagged in owners:raise ValueError('Sampler namespace collides with an existing key: '+tagged)
                    owners[tagged]=(sig,wrap)
                    groups.append(dict(key=tagged,canonical_key=key,wrap=wrap,source_width=sig[0][0],
                        source_height=sig[0][1],factor=4,levels=entries,origin='offline-restored-archive',
                        source_rgba_sha256=[entry[2] for entry in sig],archive_references=references,
                        model=args.model,alpha_policy='exact-pinned-xbrz-alpha'))
                asset['contexts'].append(dict(wrap=wrap,levels=entries,method=method))
            result['assets'].append(asset);result['completed_assets']+=1;checkpoint()
            print(json.dumps({k:result[k] for k in ('completed_assets','selected_assets','inferences','cache_hits')}),flush=True)
        lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
        for group in groups:
            lines.extend(f"{group['key']}_{level} = {entry['file']}" for level,entry in enumerate(group['levels']))
        ini=('\n'.join(lines)+'\n').encode('ascii')
        manifest=dict(scope='verified-mip-texture-pack',textures=groups,ini_sha256=sha(ini),
            sampler_namespace=sampler_pack.NAMESPACE,complete_hd_pack=False,visual_quality_validated=False,
            archive_batch={k:v for k,v in result.items() if k!='assets'},base_manifest_sha256=base['sample_manifest_sha256'])
        if args.copy_base:
            (pack/'textures.ini').write_bytes(ini)
            (pack/'sample.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
            checked=texture_pack.verify_sample(pack)
        else:
            import pack_update
            checked=pack_update.commit(pack,manifest,ini)
        result.update(complete=True,pack_manifest_sha256=checked['sample_manifest_sha256'],images=checked['images'],
                      groups=len(groups),mip_chains=checked['mip_chains']);checkpoint()
    except Exception as error:
        result['error']=str(error);checkpoint();raise
    print(json.dumps({k:v for k,v in result.items() if k not in ('assets','exclusions','source_pins','processing_pins')},indent=2))


if __name__=='__main__':main()
