"""Generate a resumable HD pack locally from verified English archives and recipes.

No prepared game pixels or runtime capture is used. Process bounded batches;
keep one generated pack and remove inference scratch after each checkpoint.
"""
import argparse,collections,contextlib,hashlib,importlib.util,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,neural_texture,sampler_pack,texture_pack
import hd_native,hd_work,hd_checkpoint_cache
from graphics_settings import preference_lock
from rgf_archive import parse_index,read_group,resources
from xet_codec import Xet


def sha(raw):return hashlib.sha256(raw).hexdigest()
def write_json(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

def compatible_owner(owner,identity,compatibility):
    return (isinstance(owner,dict) and compatibility.get('schema')==1
        and owner.get('processing_sources') in compatibility.get('legacy_processing_sources',[])
        and all(owner.get(k)==v for k,v in identity.items() if k!='processing_sources'))


def clear_work(folder):
    # This directory is exclusively owned by this build; reject links or
    # unexpected subtrees before removing only named generated scratch files.
    for path in folder.iterdir():
        if path.is_symlink():raise ValueError('Linked HD scratch path')
        if path.is_dir():
            if path.name not in ('in-standard','out-standard','in-anime','out-anime'):raise ValueError('Unknown HD scratch folder')
            for child in path.iterdir():
                if child.is_symlink() or not child.is_file() or not re.fullmatch(r'i[0-9]+\.png',child.name):raise ValueError('Unknown HD inference file')
                child.unlink()
            path.rmdir()
        elif path.suffix in ('.png','.rgba') and re.fullmatch(r'(?:b[0-9]+|input|decoded|sharpened)\.(?:png|rgba)',path.name):path.unlink()
        elif path.name not in ('scale.exe','decode.exe','sharpen.exe','hd-native.dll','build.log','inference-standard.log','inference-anime.log'):
            raise ValueError('Unknown HD scratch file: '+path.name)


def compile_helpers(work,env):
    gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk';gcc=str(title.SDK/'bin/gcc.exe')
    commands=[
        [gcc,'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-I'+str(gpu),'-I'+str(title.SDK/'include'),
         str(ROOT/'tools/scale-mip-texture.c'),str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),'-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(work/'scale.exe')],
        [gcc,'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),str(ROOT/'tools/decode-private-png.c'),'-o',str(work/'decode.exe')],
        [gcc,'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),str(ROOT/'tools/sharpen-model-texture.c'),'-o',str(work/'sharpen.exe')]]
    with (work/'build.log').open('w') as log:
        for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)


def build(archives,recipe_path,pack,work,batch_size=64,limit=None,threads='1:2:2',*,batch_mib=256,cache_mib=64):
    with contextlib.ExitStack() as cleanup:
        return _build(archives,recipe_path,pack,work,batch_size,limit,threads,batch_mib=batch_mib,cache_mib=cache_mib,cleanup=cleanup)


def _build(archives,recipe_path,pack,work,batch_size,limit,threads,*,batch_mib,cache_mib,cleanup):
    archives,recipe_path,pack,work=map(lambda p:Path(p).resolve(),(archives,recipe_path,pack,work))
    for path in (archives,recipe_path,pack,work):
        if not path.is_relative_to(ROOT/'private'):raise ValueError('HD build data must remain private')
    if work.is_relative_to(pack) or pack.is_relative_to(work) or pack==archives:raise ValueError('Separate HD source, pack and scratch folders')
    if (not 1<=batch_size<=128 or threads not in ('1:1:1','1:2:2') or
            not 64<=batch_mib<=512 or not 16<=cache_mib<=96):
        raise ValueError('Use bounded HD batches, caches and threads')
    recipe_raw=recipe_path.read_bytes();recipe=json.loads(recipe_raw)
    if recipe.get('schema')!=1 or recipe.get('game_pixels_included') is not False:raise ValueError('Unknown HD recipe')
    index=(archives/'REGFILE.RZL').read_bytes();rzp=archives/'REGFILE.RZP'
    with rzp.open('rb') as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
    if sha(index)!=recipe['index_sha256'] or archive_sha!=recipe['archive_sha256']:raise ValueError('HD source archives differ')
    tool=ROOT/'private/tools/realesrgan-20220424/package';pins=neural_texture.verify_tool(tool)
    processing_sources=hd_work.processing_sources(ROOT)
    identity=dict(tool='ISO-local-HD-v1',recipe_sha256=sha(recipe_raw),archive_sha256=archive_sha,
        processing_sources=processing_sources,model_pins=pins['files'],framework_commit=title.CONFIG['runtime']['commit'])
    compatibility=json.loads((ROOT/'config/hd-compatible-pipelines.json').read_text())
    def cache_progress(checked,total,reused,wanted):
        print(f'Verifying cached HD textures: {checked} / {total} checkpoints',flush=True)
        print(f'Preparing HD textures: {reused} / {wanted} jobs complete',flush=True)
    cached=hd_checkpoint_cache.reconcile(recipe,pack,work,identity,compatibility,cache_progress)
    print(f"HD cache: reusing {cached['reused_jobs']} / {cached['total_jobs']} verified jobs; "
          f"{cached['pending_jobs']} need generation ({cached['repair_jobs']} need repair).",flush=True)
    tasks=recipe['jobs'];completed=work/'completed';completed.mkdir(exist_ok=True);scratch=work/'scratch';scratch.mkdir(exist_ok=True)
    wanted={(int(j['reference']['resource_id'],16),j['reference']['source_sha256']) for j in tasks.values()};locations={}
    groups=parse_index(index,rzp.stat().st_size)
    with rzp.open('rb') as stream:
        for number,group in enumerate(groups):
            offset=0;plain=None
            for length,rid in group.entries:
                if rid>>16==2:
                    if plain is None:plain=read_group(stream,group)
                    digest=sha(plain[offset:offset+length]);key=(rid,digest)
                    if key in wanted:locations[key]=(number,offset,length)
                offset+=length
    if set(locations)!=wanted:raise ValueError('Some HD source resources are absent')
    env=title.environment()
    png_spec=importlib.util.spec_from_file_location('local_pack_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(png_spec);png_spec.loader.exec_module(png)
    done={};files={};names={};next_file=0;level_cache={};checked_files=dict(cached['verified_files']);output_cache={};content_hits=0;inference_launches=0
    def level_token(job,level):
        return sha(json.dumps(dict(dimensions=job['dimensions'][level],source=job['source_rgba_sha256'][level],
            wrap=job['wrap'],method=job['method'],model=job['model'],detail=job.get('detail_pass')),sort_keys=True).encode())
    for record in completed.glob('*.json'):
        job=record.stem
        if job not in tasks:raise ValueError('Unexpected completed HD job')
        row=json.loads(record.read_text())
        if row['job']!=job:raise ValueError('Completed HD job identity differs')
        if len(row['levels'])!=len(tasks[job]['dimensions']):raise ValueError('Completed HD mip count differs')
        for number,level in enumerate(row['levels']):
            path=pack/level['file']
            if not path.resolve().is_relative_to(pack) or not re.fullmatch(r'tex-[0-9]{5}-[0-7]\.png',level['file']):raise ValueError('Unsafe completed HD path')
            if level['file'] in checked_files:
                if checked_files[level['file']]!=level['sha256']:raise ValueError('Conflicting completed HD aliases')
            else:
                if sha(path.read_bytes())!=level['sha256']:raise ValueError('Completed HD texture changed')
                checked_files[level['file']]=level['sha256']
            files[level['sha256']]=level['file'];names[level['file']]=level['sha256']
            level_cache[level_token(tasks[job],number)]=level
            tokens=row.get('result_tokens',[])
            if len(tokens)==len(row['levels']) and tokens[number]:output_cache[tokens[number]]=level
        done[job]=row
    def add_png(data,w,h,level):
        nonlocal next_file
        digest=sha(data);name=files.get(digest)
        if name is None:
            while (pack/f'tex-{next_file:05d}-{level}.png').exists():next_file+=1
            if next_file>99999:raise ValueError('HD PNG count exceeds filename limits')
            name=f'tex-{next_file:05d}-{level}.png';next_file+=1
            temp=pack/(name+'.tmp');temp.write_bytes(data);temp.replace(pack/name);files[digest]=name;names[name]=digest
        return dict(file=name,width=w,height=h,sha256=digest)
    pending=[j for j in tasks if j not in done];started=time.monotonic();processed=0
    print(f'Preparing HD textures: {len(done)} / {len(tasks)} jobs complete',flush=True)
    native=hd_native.Native(scratch) if pending else None
    if native:cleanup.callback(native.close)
    if limit is not None:pending=pending[:limit]
    decoded=hd_work.ByteCache(cache_mib*1024**2);archive_cache=hd_work.ByteCache(cache_mib*1024**2)
    with rzp.open('rb') as stream:
        start=0
        for batch in hd_work.batches(tasks,pending,batch_size,batch_mib*1024**2):
            clear_work(scratch);prepared={};inferences={}
            for job_id in batch:
                job=tasks[job_id];ref=job['reference'];loc=locations[int(ref['resource_id'],16),ref['source_sha256']]
                plain=archive_cache.get(loc[0],lambda:read_group(stream,groups[loc[0]]))
                raw=plain[loc[1]:loc[1]+loc[2]];xet=Xet.parse(raw);idx=ref['texture_index']
                if xet.textures[idx].name!=ref['name']:raise ValueError('HD source texture name differs')
                output=[];wrap=job['wrap']
                if wrap not in (0,1,256,257) or job['method'] not in ('scale','restore'):raise ValueError('Invalid HD processing method')
                for level,(w,h) in enumerate(job['dimensions']):
                    def decode():
                        aw,ah,pixels=xet.preview_mip(idx,level,limit=512)
                        if (aw,ah)!=(w,h):raise ValueError('HD source mip dimensions differ')
                        return pixels
                    pixels=decoded.get((ref['resource_id'],ref['source_sha256'],idx,level),decode)
                    if len(pixels)!=w*h*4 or sha(pixels)!=job['source_rgba_sha256'][level]:raise ValueError('HD source mip identity differs')
                    token=level_token(job,level)
                    if token in level_cache:
                        output.append(dict(reuse=level_cache[token],level=level));continue
                    baseline=native.scale(pixels,w,h,wrap)
                    item=dict(w=w,h=h,baseline=baseline,level=level,inference=None)
                    padded=None;model=None
                    if job['method']=='restore' and any(pixels[3::4]):
                        model=job['model'];neural_texture.processing_pins(pins,model)
                        padded=native.pad(pixels,w,h,wrap)
                    item['result_token']=hd_work.content_token(baseline,padded,model,job.get('detail_pass'),w,h)
                    if item['result_token'] in output_cache:
                        content_hits+=1;output.append(dict(reuse=output_cache[item['result_token']],level=level,result_token=item['result_token']));continue
                    if padded is not None:
                        data=png.png(w+128,h+128,padded);token=(model,sha(data));entry=inferences.get(token)
                        if entry is None:
                            tag='anime' if model.endswith('-anime') else 'standard';folder=scratch/('in-'+tag);folder.mkdir(exist_ok=True)
                            destination=scratch/('out-'+tag);destination.mkdir(exist_ok=True)
                            name=f'i{len(inferences):05}.png';(folder/name).write_bytes(data)
                            entry=dict(model=model,tag=tag,file=name,width=w,height=h);inferences[token]=entry
                        item['inference']=entry
                    output.append(item)
                prepared[job_id]=output
            for tag in ('standard','anime'):
                folder=scratch/('in-'+tag)
                if not folder.exists():continue
                model='realesrgan-x4plus'+('-anime' if tag=='anime' else '')
                print(f'Preparing HD textures: batch {start+1}-{start+len(batch)} / {len(pending)} ({model})',flush=True)
                with (scratch/('inference-'+tag+'.log')).open('w') as log:
                    subprocess.run([str(tool/'realesrgan-ncnn-vulkan.exe'),'-i',str(folder),'-o',str(scratch/('out-'+tag)),
                        '-m',str(tool/'models'),'-n',model,'-s','4','-t','128','-j',threads,'-f','png'],env=env,cwd=scratch,
                        stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180*len(inferences))
                inference_launches+=1
            for job_id,items in prepared.items():
                levels=[];job=tasks[job_id]
                for item in items:
                    if 'reuse' in item:
                        levels.append(item['reuse']);level_cache[level_token(job,item['level'])]=item['reuse'];continue
                    w,h=item['w'],item['h'];baseline=item['baseline'];pixels=baseline
                    if item['inference']:
                        inf=item['inference'];restored=scratch/('out-'+inf['tag'])/inf['file']
                        restored_pixels=native.crop(restored.read_bytes(),(w+128)*4,(h+128)*4,256,256,w*4,h*4)
                        pixels=native.merge(restored_pixels,baseline)
                    if len(pixels)!=w*h*64 or pixels[3::4]!=baseline[3::4]:raise ValueError('HD output dimensions/alpha differ')
                    if job.get('detail_pass'):
                        if job['detail_pass']!='gaussian5-detail25-cap6-alpha-preserved-v1':raise ValueError('Unknown player detail pass')
                        pixels=native.detail(pixels,w*4,h*4)
                        if len(pixels)!=len(baseline) or pixels[3::4]!=baseline[3::4]:raise ValueError('Player detail pass changed alpha')
                    entry=add_png(png.png(w*4,h*4,pixels),w*4,h*4,item['level']);levels.append(entry)
                    level_cache[level_token(job,item['level'])]=entry
                    output_cache[item['result_token']]=entry
                row=dict(job=job_id,levels=levels,result_tokens=[item.get('result_token') for item in items]);write_json(completed/(job_id+'.json'),row);done[job_id]=row
            processed+=len(batch)
            start+=len(batch)
            write_json(work/'progress.json',dict(state='GENERATING',completed_jobs=len(done),total_jobs=len(tasks),ready_to_play=False,
                elapsed_seconds=round(time.monotonic()-started,1),session_jobs=processed,inference_launches=inference_launches,
                decoded_cache_hits=decoded.hits,archive_cache_hits=archive_cache.hits,content_reuse_hits=content_hits))
            print(f'Preparing HD textures: {len(done)} / {len(tasks)} jobs complete',flush=True)
            clear_work(scratch)
    if len(done)!=len(tasks):
        return dict(state='GENERATING',completed_jobs=len(done),total_jobs=len(tasks),ready_to_play=False)
    textures=[]
    for group in recipe['groups']:
        job=tasks[group['job']];w,h=job['dimensions'][0]
        textures.append(dict(key=group['key'],source_width=w,source_height=h,factor=4,levels=done[group['job']]['levels'],
            wrap=job['wrap'],origin='ISO-local-'+job['method'],source_rgba_sha256=job['source_rgba_sha256']))
    lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
    for group in textures:
        lines.extend(f"{group['key']}_{level} = {entry['file']}" for level,entry in enumerate(group['levels']))
    ini=('\n'.join(lines)+'\n').encode('ascii');(pack/'textures.ini').write_bytes(ini)
    write_json(pack/'sample.json',dict(scope='verified-mip-texture-pack',textures=textures,ini_sha256=sha(ini),sampler_namespace=sampler_pack.NAMESPACE,
        complete_hd_pack=False,visual_quality_validated=False,local_recipe_sha256=sha(recipe_raw)))
    checked=texture_pack.verify_sample(pack)
    removed=hd_work.prune_orphans(pack,{level['file'] for group in textures for level in group['levels']})
    if removed:write_json(work/'orphan-cleanup.json',dict(removed=removed,bytes_removed=sum(row['size'] for row in removed)))
    result=dict(state='HD_GENERATED',completed_jobs=len(done),total_jobs=len(tasks),groups=len(textures),images=checked['images'],
        pack_manifest_sha256=checked['sample_manifest_sha256'],game_pixels_bundled=False,original_UI_and_portraits=True,complete_campaign_validation=False,
        inference_launches=inference_launches,reused_jobs=cached['reused_jobs'],generated_jobs=processed,repair_jobs=cached['repair_jobs'],
        decoded_cache_hits=decoded.hits,archive_cache_hits=archive_cache.hits,content_reuse_hits=content_hits,
        orphan_PNGs_removed=len(removed),GPU_threads=threads,batch_limit=batch_size,batch_mib=batch_mib,cache_mib=cache_mib)
    write_json(work/'result.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archives',type=Path,required=True);p.add_argument('--recipes',type=Path,required=True)
    p.add_argument('--pack',type=Path,default=ROOT/'private/hd-remaster-pack');p.add_argument('--work',type=Path,default=ROOT/'private/local-build/HD-work')
    p.add_argument('--batch-size',type=int,default=64);p.add_argument('--threads',choices=('1:1:1','1:2:2'),default='1:2:2')
    p.add_argument('--batch-mib',type=int,default=256);p.add_argument('--cache-mib',type=int,default=64)
    p.add_argument('--limit',type=int,help='Bounded development check; never marks a partial pack ready')
    a=p.parse_args()
    if a.limit is not None and a.limit<1:raise ValueError('Limit must be positive')
    with preference_lock(ROOT/'private/local-build/HD-generation.lock'):
        print(json.dumps(build(a.archives,a.recipes,a.pack,a.work,a.batch_size,a.limit,a.threads,
                               batch_mib=a.batch_mib,cache_mib=a.cache_mib),indent=2),flush=True)


if __name__=='__main__':main()
