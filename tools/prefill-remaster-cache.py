"""Run exact archive restoration inputs in one local model process.

This produces no installable pack. The ordinary builder still verifies every
cache identity, PNG hash, decoded extent and alpha plane before consuming it.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import neural_texture
import title


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    builder=load('archive_builder','build-archive-remaster.py')
    png_module=load('inventory','inventory-textures.py')
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','neural-tool','output','cache'):parser.add_argument('--'+name,type=builder.private,required=True)
    parser.add_argument('--pattern',required=True)
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--limit',type=int,default=128)
    parser.add_argument('--allow-alpha',action='store_true')
    parser.add_argument('--alpha-only',action='store_true')
    parser.add_argument('--base-pack',type=builder.private,help='Skip existing identities exactly as the pack builder does')
    parser.add_argument('--model',choices=('realesrgan-x4plus','realesrgan-x4plus-anime'),default='realesrgan-x4plus')
    args=parser.parse_args()
    if args.output.exists() or args.offset<0 or not 1<=args.limit<=8192:parser.error('Use fresh output and bounded selection')
    title.verify_inputs();pins=neural_texture.verify_tool(args.neural_tool)
    model_pins=neural_texture.processing_pins(pins,args.model)
    raw_catalog=(args.catalog/'catalog.json').read_bytes()
    if json.loads((args.catalog/'result.json').read_text()).get('exported_rgba') is not True:raise ValueError('RGBA exports required')
    selected,excluded=builder.select(json.loads(raw_catalog),re.compile(args.pattern),args.allow_alpha or args.alpha_only,args.alpha_only)
    base=builder.texture_pack.verify_sample(args.base_pack) if args.base_pack else None
    if base:
        selected,retained=builder.uncovered(selected,base);excluded.extend(retained)
    chosen=selected[args.offset:args.offset+args.limit]
    if not chosen:raise ValueError('No admissible artwork')
    args.output.mkdir(parents=True);args.cache.mkdir(parents=True,exist_ok=True)
    work=args.output/'work';work.mkdir();inputs=args.output/'input';inputs.mkdir();outputs=args.output/'output';outputs.mkdir()
    env=title.environment();gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk';scaler=work/'scale.exe';decoder=work/'decode.exe'
    commands=[
        [str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-Wl,--no-insert-timestamp',
         '-I'+str(gpu),'-I'+str(title.SDK/'include'),str(ROOT/'tools/scale-mip-texture.c'),
         str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),
         '-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(scaler)],
        [str(title.SDK/'bin/gcc.exe'),'-O2','-Wl,--no-insert-timestamp','-I'+str(title.FRAMEWORK/'third_party/stb'),
         str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)]]
    with (work/'build.log').open('w') as log:
        for command in commands:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    source_pins={name:sha((ROOT/name).read_bytes()) for name in (
        'tools/build-archive-remaster.py','tools/neural_texture.py','tools/scale-mip-texture.c','tools/decode-private-png.c')}
    source_pins.update(scaler=sha(scaler.read_bytes()),decoder=sha(decoder.read_bytes()))
    result=dict(scope='private-batched-restoration-cache',producer_sha256=sha(Path(__file__).read_bytes()),
        catalog_sha256=sha(raw_catalog),model_pins=model_pins,processing_source_pins=source_pins,
        pattern=args.pattern,offset=args.offset,selected_assets=len(chosen),prepared_assets=0,
        alpha_only=args.alpha_only,base_manifest_sha256=base['sample_manifest_sha256'] if base else None,
        jobs=0,existing_cache_hits=0,committed_cache_entries=0,complete=False,pack_created=False)
    jobs={}
    def checkpoint():
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    checkpoint()
    for sig,rows,keys in chosen:
        for wrap in (0,1,256,257):
            for w,h,digest in sig:
                raw_path=args.catalog/'rgba'/(digest+'.rgba');raw=raw_path.read_bytes()
                if sha(raw)!=digest or len(raw)!=w*h*4:raise ValueError('Source RGBA differs')
                if not any(raw[3::4]):continue
                baseline_path=work/'baseline.rgba'
                subprocess.run([str(scaler),str(raw_path),str(baseline_path),str(w),str(h),'4',
                                str(wrap&1),str((wrap>>8)&1)],env=env,check=True,timeout=30)
                baseline=baseline_path.read_bytes()
                if len(baseline)!=w*h*64:raise ValueError('Reference extent differs')
                coloured=neural_texture.masked_colours(raw,w,h,wrap)
                padded=neural_texture.pad_opaque(coloured,w,h,64,wrap)
                input_png=png_module.png(w+128,h+128,padded)
                identity=dict(input_sha256=sha(input_png),baseline_sha256=sha(baseline),model=model_pins,
                              sources=source_pins,width=w,height=h,border=64)
                cache_id=sha(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())
                cache_png=args.cache/(cache_id+'.png');cache_json=args.cache/(cache_id+'.json')
                if cache_png.exists() and cache_json.exists():
                    saved=json.loads(cache_json.read_text())
                    if saved.get('identity')!=identity or saved.get('sha256')!=sha(cache_png.read_bytes()):
                        raise ValueError('Existing cache identity differs')
                    result['existing_cache_hits']+=1;continue
                if cache_id not in jobs:
                    (inputs/(cache_id+'.png')).write_bytes(input_png)
                    (work/(cache_id+'.rgba')).write_bytes(baseline)
                    jobs[cache_id]=identity
        result['prepared_assets']+=1;result['jobs']=len(jobs);checkpoint()
        print(json.dumps({k:result[k] for k in ('prepared_assets','selected_assets','jobs','existing_cache_hits')}),flush=True)
    (args.output/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')
    process_error=None
    if jobs:
        command=[str(args.neural_tool/'realesrgan-ncnn-vulkan.exe'),'-i',str(inputs),'-o',str(outputs),
                 '-m',str(args.neural_tool/'models'),'-n',args.model,'-s','4','-t','128','-j','1:1:1']
        try:
            with (args.output/'inference.log').open('w') as log:
                completed=subprocess.run(command,env=env,cwd=work,stdout=log,stderr=subprocess.STDOUT,
                                         timeout=max(180,len(jobs)*30))
            result['inference_returncode']=completed.returncode
            if completed.returncode:process_error='Local batch inference exited '+str(completed.returncode)
        except subprocess.TimeoutExpired:process_error='Local batch inference timed out'
    for cache_id,identity in jobs.items():
        image=outputs/(cache_id+'.png');w,h=identity['width'],identity['height']
        if not image.is_file():continue
        rgba=work/'decoded.rgba'
        try:
            subprocess.run([str(decoder),str(image),str(rgba),str((w+128)*4),str((h+128)*4),
                            '256','256',str(w*4),str(h*4)],env=env,check=True,timeout=30)
            baseline=(work/(cache_id+'.rgba')).read_bytes()
            if sha(baseline)!=identity['baseline_sha256']:raise ValueError('Alpha reference changed')
            restored=neural_texture.merge_cutout_colours(rgba.read_bytes(),baseline)
            if restored[3::4]!=baseline[3::4]:raise ValueError('Alpha reference differs')
            png=png_module.png(w*4,h*4,restored);temporary=args.cache/(cache_id+'.partial')
            temporary.write_bytes(png);temporary.replace(args.cache/(cache_id+'.png'))
            temporary.write_text(json.dumps(dict(identity=identity,sha256=sha(png),
                producer_sha256=result['producer_sha256']),sort_keys=True));temporary.replace(args.cache/(cache_id+'.json'))
            result['committed_cache_entries']+=1;checkpoint()
        except Exception as error:
            result.setdefault('refused_outputs',[]).append(dict(job=cache_id,error=str(error)));checkpoint()
    if result['committed_cache_entries']!=len(jobs) or process_error:
        result['error']=process_error or 'Some batch outputs were missing or refused';checkpoint();raise ValueError(result['error'])
    result['complete']=True;checkpoint();print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
