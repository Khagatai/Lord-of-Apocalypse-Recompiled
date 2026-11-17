"""Re-render English UI from original ISO textures and text-only plans.

Nothing is promoted to the active translation.
"""
import argparse,collections,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from iso_archive import original_archive
from rgf_archive import parse_index,resources
from xet_codec import Xet
from texture_text import reconstruct,digest
import setup_progress

def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--resume',action='store_true')
    parser.add_argument('--limit',type=int,default=10000)
    parser.add_argument('--recipes',type=Path,help='Portable text/layout instructions; no developer image paths required')
    parser.add_argument('--allow-local-rasterization',action='store_true',help='Record platform font-rasterization variants; source identity and edit-region guards remain strict')
    args=parser.parse_args()
    out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private'):raise ValueError('Keep local pixel outputs private')
    if args.recipes:
        portable=json.loads(args.recipes.read_text(encoding='utf-8'))
        if portable.get('schema')!=1 or portable.get('source_pixels_included') is not False or portable.get('rendered_pixels_included') is not False:
            raise ValueError('Unknown portable text recipe')
        recipes=portable['resources'];specifications={}
        for job_id,job in portable['render_jobs'].items():
            canonical=json.dumps(job,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
            if hashlib.sha256(canonical).hexdigest()!=job_id:raise ValueError('Portable rendering job identity differs')
            specifications['recipe:'+job_id]=(job['plan'],None,job['renderer'],job['operation'])
        identity=dict(tool='build-local-text-images-portable-v1',recipes_sha256=file_hash(args.recipes))
    else:
        recipes_path=ROOT/'private/local-build/japanese-textures.json';index_path=ROOT/'private/local-build/render-spec-audit.json'
        recipes=json.loads(recipes_path.read_text())['resources'];index=json.loads(index_path.read_text())
        specifications={item['pixels']:(row['path'],row['spec_sha256'],'regular','none') for row in index['found'] for item in row['outputs']}
        for special in index['special']:
            path=Path(special['pixels']);candidate=path.parent.with_suffix('.json');operation='none'
            if path.name=='logo-wordmark.rgba':
                specifications[str(path)]=(None,None,'neutral-wordmark','none');continue
            if path.parent.name=='conq09-english':candidate=path.parent/'letters.json';operation='zero-transparent'
            elif path.name=='composite.rgba':operation='thumbnail-plate'
            if candidate.is_file():specifications[str(path)]=(str(candidate),file_hash(candidate),'caption',operation)
        identity=dict(tool='build-local-text-images-v1',recipes_sha256=file_hash(recipes_path),spec_index_sha256=file_hash(index_path))
    if out.exists():
        if not args.resume or json.loads((out/'owner.json').read_text())!=identity:raise ValueError('Existing render work does not match this recipe')
    else:out.mkdir(parents=True);(out/'owner.json').write_text(json.dumps(identity,indent=2)+'\n')
    spec=importlib.util.spec_from_file_location('local_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)
    wanted={int(row['resource_id'],16) for row in recipes};source={};occurrence=collections.Counter()
    with original_archive(args.image) as (raw,stream):
        for group,rid,data in resources(stream,parse_index(raw,stream.size)):
            which=occurrence[group,rid];occurrence[group,rid]+=1
            if rid in wanted:source[group,rid,which]=data
    generated={};verified=[];unresolved=[];count=0;variants=[]
    powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    from text_render_worker import Renderer
    with Renderer(ROOT) as render_worker:
        for row in recipes:
            raw=source[row['group_index'],int(row['resource_id'],16),row['occurrence']]
            if digest(raw)!=row['source_sha256']:raise ValueError('Original resource hash differs')
            translated=json.loads(json.dumps(row));supported=True
            for edit in translated.get('edits',[]):
                old=edit['rgba_path'];key=old+'|'+row['source_sha256']
                if args.recipes:key+='|texture:'+str(edit['texture_index'])
                cleanup={('0002030c',0):(256,32,[(27,11)]),('000210f8',1):(512,128,[(287,8),(324,8)])}.get((row['resource_id'],edit['texture_index']))
                if cleanup:key+='|source-ink-cleanup-v1'
                if old not in specifications:
                    unresolved.append(dict(resource_id=row['resource_id'],reason='Special caption/composite renderer not yet wired',input=old));supported=False;break
                if key not in generated:
                    if count>=args.limit:supported=False;break
                    job=out/('job-'+hashlib.sha256(key.encode()).hexdigest()[:16]);job.mkdir(exist_ok=True)
                    record=job/'result.json'
                    if record.exists():
                        prior=json.loads(record.read_text());pixels=Path(prior['pixels'])
                        if not pixels.resolve().is_relative_to(job) or file_hash(pixels)!=prior['sha256']:raise ValueError('Existing rendered pixels changed')
                    else:
                        specification,expected,renderer,operation=specifications[old]
                        width,height,rgba=Xet.parse(raw).preview(edit['texture_index'],limit=1024)
                        if cleanup:
                            if (width,height)!=cleanup[:2]:raise ValueError('Measured source-ink cleanup geometry differs')
                            clean=bytearray(rgba)
                            for x,y in cleanup[2]:
                                if not any(a<=x<a+w and b<=y<b+h for a,b,w,h in edit['regions']):raise ValueError('Source-ink cleanup escapes translated region')
                                clean[(y*width+x)*4:(y*width+x)*4+4]=bytes(4)
                            rgba=bytes(clean)
                        target=job/'rendered'
                        if target.exists():raise ValueError('Interrupted local render requires inspection: '+str(target))
                        if renderer=='neutral-wordmark':
                            output=bytearray(rgba)
                            for x0,y0,w,h in edit['regions']:
                                for y in range(y0,y0+h):
                                    for x in range(x0,x0+w):
                                        offset=(y*width+x)*4;colour=output[offset:offset+3]
                                        if max(colour)-min(colour)<=30:output[offset:offset+4]=bytes((0,0,0,255))
                            target.mkdir();pixels=target/'pixels.rgba';pixels.write_bytes(output)
                        else:
                            if isinstance(specification,dict):plan=json.loads(json.dumps(specification))
                            else:
                                if file_hash(specification)!=expected:raise ValueError('Text rendering specification changed')
                                plan=json.loads(Path(specification).read_text(encoding='utf-8-sig'))
                            if renderer=='regular':
                                base=job/'source.png';base.write_bytes(png.png(width,height,rgba));plan['source_png']=base.relative_to(ROOT).as_posix()
                            plan_path=job/'plan.json';plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                            script='render-texture-text.ps1' if renderer=='regular' else 'render-caption-atlas.ps1'
                            render_worker.render(script,plan_path,target)
                            pixels=target/'pixels.rgba'
                            if operation=='zero-transparent':
                                output=bytearray(pixels.read_bytes())
                                for offset in range(0,len(output),4):
                                    if not output[offset+3]:output[offset:offset+4]=bytes(4)
                                pixels=target/'composite.rgba';pixels.write_bytes(output)
                            elif operation=='thumbnail-plate':
                                letters=pixels.read_bytes();output=bytearray(rgba)
                                for x0,y0,w,h in edit['regions']:
                                    for y in range(y0,y0+h):
                                        for x in range(x0,x0+w):
                                            offset=(y*width+x)*4;alpha=letters[offset+3]
                                            output[offset:offset+4]=bytes((*((v*alpha+127)//255 for v in letters[offset:offset+3]),255))
                                pixels=target/'composite.rgba';pixels.write_bytes(output)
                        prior=dict(pixels=str(pixels),sha256=file_hash(pixels),source_resource_sha256=row['source_sha256'])
                        record.write_text(json.dumps(prior,indent=2)+'\n')
                    if cleanup:
                        # These measured, isolated source-ink pixels lie inside the
                        # translated erase regions. Apply the measured correction
                        # after rasterization as well as during source preparation.
                        clean=bytearray(Path(prior['pixels']).read_bytes())
                        width,height=cleanup[:2]
                        if len(clean)!=width*height*4:raise ValueError('Final ink-cleanup extent differs')
                        for x,y in cleanup[2]:clean[(y*width+x)*4:(y*width+x)*4+4]=bytes(4)
                        if hashlib.sha256(clean).hexdigest()!=prior['sha256']:
                            pixels=job/'source-ink-cleaned.rgba'
                            if pixels.exists() and pixels.read_bytes()!=clean:raise ValueError('Existing source-ink cleanup differs')
                            pixels.write_bytes(clean)
                            prior=dict(prior,pixels=str(pixels),sha256=file_hash(pixels))
                            record.write_text(json.dumps(prior,indent=2)+'\n')
                    generated[key]=prior;count+=1
                    if count%12==0:print('Locally rendered text images:',count,flush=True)
                edit.update(rgba_path=generated[key]['pixels'],rgba_sha256=generated[key]['sha256'])
            if not supported:continue
            target=reconstruct(raw,translated,ROOT/'private')
            if digest(target)!=row['target_sha256']:
                if not args.allow_local_rasterization:
                    unresolved.append(dict(resource_id=row['resource_id'],reason='Local rendering differs from current WIP pixels'));continue
                variants.append(dict(group_index=row['group_index'],resource_id=row['resource_id'],occurrence=row['occurrence'],
                    reference_sha256=row['target_sha256'],actual_sha256=digest(target)))
                translated['reference_target_sha256']=row['target_sha256'];translated['target_sha256']=digest(target)
            verified.append(translated)
            setup_progress.emit('text',len(verified),len(recipes))
    report=dict(status='PASS' if len(verified)==len(recipes) else 'INCOMPLETE',source='verified original Japanese ISO',
                locally_rendered_images=count,verified_resources=len(verified),total_resources=len(recipes),resources=verified,unresolved=unresolved,
                active_translation_changed=False,ISO_only_texture_generation_complete=len(verified)==len(recipes))
    report.update(platform_rasterization_variants=variants,byte_identical_reference_resources=len(verified)-len(variants),
        local_rasterization_allowed=args.allow_local_rasterization,source_identity_and_edit_region_guards=True)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('resources','unresolved')},indent=2),flush=True)
if __name__=='__main__':main()
