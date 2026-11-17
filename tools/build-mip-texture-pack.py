"""Build a private complete-chain pilot from measured captures and the pinned scaler.

This precomputes scaled original art; it does not invent missing HD detail.
Source textures, decoded bytes, native helpers and generated PNGs stay private.
"""
import argparse
import configparser
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import title
import texture_pack
import neural_texture
import art_capture


def sha(data):return hashlib.sha256(data).hexdigest()


def captured_chains(capture):
    capture=Path(capture).resolve()
    if not capture.is_relative_to(ROOT/'private'):raise ValueError('Use a private capture')
    rows=[json.loads(x) for x in (capture/'mip-capture.jsonl').read_text().splitlines()]
    groups={}
    for row in rows:
        if not re.fullmatch('[0-9a-f]{24}',row.get('key','')) or not re.fullmatch('[0-9a-f]{16}',row.get('content','')):
            raise ValueError('Invalid captured texture identity')
        if row.get('written') is not True or type(row.get('wrap')) is not int or row['wrap'] not in (0,1,256,257):raise ValueError('Incomplete capture or invalid wrap mode')
        if type(row.get('level')) is not int or not 0<=row['level']<8 or type(row.get('levels')) is not int or not 2<=row['levels']<=8 or row['level']>=row['levels']:
            raise ValueError('Invalid captured mip level')
        if any(type(row.get(k)) is not int or not 1<=row[k]<=512 for k in ('width','height')):raise ValueError('Invalid captured dimensions')
        name=row.get('file','')
        expected=f"mip-{row['key']}-{row['content']}-{row['wrap']:03x}-{row['level']}.rgba"
        if name!=expected:raise ValueError('Invalid captured filename')
        file=(capture/name).resolve()
        if not file.is_relative_to(capture):raise ValueError('Capture file escapes its folder')
        data=file.read_bytes()
        if len(data)!=row['width']*row['height']*4:raise ValueError('Captured RGBA extent differs')
        group=groups.setdefault((row['key'],row['content'],row['wrap']),{})
        if row['level'] in group:raise ValueError('Duplicate captured level')
        group[row['level']]={**row,'path':file,'sha256':sha(data)}
    aliases={}
    for (key,content,wrap),levels in groups.items():
        ordered=[levels[i] for i in sorted(levels)]
        if not ordered or list(sorted(levels))!=list(range(ordered[0]['levels'])):raise ValueError('Capture has a missing mip')
        if any(row['levels']!=ordered[0]['levels'] for row in ordered):raise ValueError('Capture has inconsistent level counts')
        w,h=ordered[0]['width'],ordered[0]['height']
        if any((r['width'],r['height'])!=(max(1,w>>l),max(1,h>>l)) for l,r in enumerate(ordered)):
            raise ValueError('Captured mips do not halve')
        aliases.setdefault('00000000'+key[8:],[]).append((wrap,ordered))
    chosen=[];ambiguous=[]
    for key,variants in aliases.items():
        signatures={(wrap,tuple((row['width'],row['height'],row['sha256']) for row in rows)) for wrap,rows in variants}
        if len(signatures)!=1:ambiguous.append(key);continue
        wrap,levels=variants[0]
        if min(levels[0]['width'],levels[0]['height'])<32:continue
        chosen.append((key,wrap,levels))
    chosen.sort(key=lambda item:(-item[2][0]['width']*item[2][0]['height'],item[0]))
    return chosen,ambiguous


def merged_chains(captures):
    """Union measured captures, excluding conflicts within or across runs."""
    variants={};excluded=set()
    for capture in captures:
        chains,ambiguous=captured_chains(capture);excluded.update(ambiguous)
        for key,wrap,levels in chains:
            variants.setdefault(key,[]).append((wrap,levels))
    chosen=[]
    for key,rows in variants.items():
        signatures={(wrap,tuple((r['width'],r['height'],r['sha256']) for r in levels)) for wrap,levels in rows}
        if len(signatures)!=1:excluded.add(key)
        if key not in excluded:
            wrap,levels=rows[0];chosen.append((key,wrap,levels))
    chosen.sort(key=lambda item:(-item[2][0]['width']*item[2][0]['height'],item[0]))
    return chosen,sorted(excluded)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--extra-capture',type=Path,action='append',default=[])
    parser.add_argument('--ui-pack',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--factor',type=int,choices=(2,3,4),default=4)
    parser.add_argument('--limit',type=int,choices=range(1,97),default=8)
    parser.add_argument('--reuse-pack',type=Path,help='Verified previous pack; reuse only identical sources, model pins and sampling context')
    parser.add_argument('--art-capture',type=Path,help='Observed single-level 3D artwork; requires exact archive matches')
    parser.add_argument('--catalog',type=Path,help='Private decoded archive catalog for --art-capture')
    parser.add_argument('--neural-tool',type=Path,help='Pinned private offline Real-ESRGAN package; opaque complete chains only')
    parser.add_argument('--restore-cutouts',action='store_true',help='Pilot: restore binary-cutout RGB while preserving pinned xBRZ alpha exactly')
    parser.add_argument('--restore-masked',action='store_true',help='Pilot: restore admitted masked-material RGB with exact pinned xBRZ alpha')
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():parser.error('Use a fresh private output directory')
    title.verify_inputs()
    neural_pins=neural_texture.verify_tool(args.neural_tool) if args.neural_tool else None
    if (args.restore_cutouts or args.restore_masked) and not neural_pins:parser.error('Alpha-constrained restoration requires the pinned offline model')
    mask_policy=None;mask_policy_hash=None
    if args.restore_masked:
        raw=(ROOT/'config/remaster-mask-policy.json').read_bytes();mask_policy=json.loads(raw);mask_policy_hash=sha(raw)
        if (mask_policy.get('schema')!=1 or type(mask_policy.get('minimum_dense_alpha')) is not int or
            not 128<=mask_policy['minimum_dense_alpha']<=255 or
            not isinstance(mask_policy.get('keys'),dict) or
            any(not re.fullmatch('[0-9a-f]{24}',k) for k in mask_policy['keys'])):
            raise ValueError('Invalid admitted masked-material policy')
    captures=[args.capture,*args.extra_capture]
    chosen,ambiguous=merged_chains(captures)
    selected=[x for x in chosen if max(x[2][0]['width'],x[2][0]['height'])*args.factor<=2048][:args.limit]
    art_report=None
    if args.art_capture:
        if not args.catalog:parser.error('--art-capture requires --catalog')
        art,art_report=art_capture.observed_art(args.art_capture,args.catalog)
        known={row[0] for row in selected}
        conflicts=set(art_report['ambiguous'])|set(ambiguous)
        selected=[row for row in selected if row[0] not in conflicts]
        selected.extend(row for row in art if row[0] not in known and row[0] not in conflicts)
    if not selected:raise ValueError('No unambiguous eligible world chains')
    ui=texture_pack.verify_sample(args.ui_pack)
    if ui['scope']!='verified-ui-texture-pack':raise ValueError('Use the verified base UI pack')
    reuse={};reuse_report=None;reuse_verified=None
    if args.reuse_pack:
        reuse_verified=texture_pack.verify_sample(args.reuse_pack)
        if reuse_verified['scope']!='verified-mip-texture-pack':raise ValueError('Reuse requires a verified mip pack')
        reuse_report=json.loads((args.reuse_pack/'sample.json').read_text())
        reuse={r['key']:r for r in reuse_report['textures']}
    output.mkdir(parents=True);pack=output/'pack';pack.mkdir();work=output/'work';work.mkdir()
    gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk';exe=output/'scale-texture.exe'
    command=[str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
             '-I'+str(gpu),'-I'+str(title.SDK/'include'),str(ROOT/'tools/scale-mip-texture.c'),
             str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),
             '-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(exe)]
    env=title.environment()
    with (output/'scale-build.log').open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    decoder=output/'decode-png.exe'
    if neural_pins:
        subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),
                        str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)],env=env,check=True)
    spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/inventory-textures.py')
    png_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(png_module)
    groups=[];lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
    def add(key,w,h,f,pngs,**extra):
        index=len(groups);entries=[]
        for level,data in enumerate(pngs):
            name=f'tex-{index:03d}-{level}.png';(pack/name).write_bytes(data)
            width,height=max(1,w*f>>level),max(1,h*f>>level)
            entries.append(dict(file=name,width=width,height=height,sha256=sha(data)))
            lines.append(key+'_'+str(level)+' = '+name)
        groups.append(dict(key=key,source_width=w,source_height=h,factor=f,levels=entries,**extra))
    ini=configparser.ConfigParser(interpolation=None);ini.read(args.ui_pack/'textures.ini',encoding='utf-8-sig')
    metadata={entry['file']:entry for entry in ui['textures']}
    for key,name in ini['hashes'].items():
        entry=metadata[name];factor=entry['factor']
        add(key,entry['width']//factor,entry['height']//factor,factor,[(args.ui_pack/name).read_bytes()],origin='base-ui')
    neural_count=0;reused_count=0;cutout_count=0;masked_count=0
    for index,(key,wrap,levels) in enumerate(selected):
        pngs=[]
        originals=[row['path'].read_bytes() for row in levels]
        if any(sha(data)!=row['sha256'] for data,row in zip(originals,levels)):
            raise ValueError('Captured source changed after validation')
        opaque=all(set(data[3::4])=={255} for data in originals)
        cutout=bool(neural_pins and args.restore_cutouts and not opaque and
                    all(255 in set(data[3::4]) and set(data[3::4]).issubset({0,255}) for data in originals))
        masked=bool(neural_pins and args.restore_masked and not opaque and
                    all(any(data[3::4]) for data in originals) and
                    (key in mask_policy['keys'] or all(min(data[3::4])>=mask_policy['minimum_dense_alpha'] for data in originals)))
        restore=bool(neural_pins and (opaque or cutout or masked))
        origin='offline-restored-masked' if masked else ('offline-restored-cutout' if cutout else ('offline-restored-world' if restore else 'scaled-authored-world'))
        if restore and args.factor!=4:raise ValueError('Pinned restoration model requires 4x output')
        previous=reuse.get(key,{})
        can_reuse=(previous.get('factor')==args.factor and previous.get('wrap')==wrap and
                   previous.get('source_width')==levels[0]['width'] and previous.get('source_height')==levels[0]['height'] and
                   previous.get('source_rgba_sha256')==[row['sha256'] for row in levels] and
                   previous.get('origin')==origin and
                   len(previous.get('levels',[]))==len(levels))
        if restore and can_reuse:
            settings=reuse_report.get('offline_restoration',{})
            try:same_pins=neural_texture.processing_pins(settings.get('pins',{}))==neural_texture.processing_pins(neural_pins)
            except ValueError:same_pins=False
            can_reuse=(same_pins and settings.get('model')=='realesrgan-x4plus' and
                       settings.get('context_border')==64 and settings.get('wrap_context') is True and
                       settings.get('every_authored_level_preserved') is True)
            if cutout or masked:can_reuse=can_reuse and settings.get('cutout_alpha_policy')=='exact-pinned-xbrz-alpha'
            if masked:can_reuse=can_reuse and settings.get('masked_material_policy_sha256')==mask_policy_hash
        if can_reuse:
            pngs=[(args.reuse_pack/entry['file']).read_bytes() for entry in previous['levels']]
            if any(sha(data)!=entry['sha256'] for data,entry in zip(pngs,previous['levels'])):
                raise ValueError('Reuse pack changed after verification')
            reused_count+=1
        for level,row in enumerate(levels):
            if can_reuse:break
            w,h=row['width'],row['height'];target=work/f'{index}-{level}.rgba'
            if restore:
                border=64;pw,ph=w+2*border,h+2*border
                input_rgba=originals[level];alpha_reference=None
                if cutout or masked:
                    subprocess.run([str(exe),str(row['path']),str(target),str(w),str(h),str(args.factor),str(wrap&1),str((wrap>>8)&1)],env=env,check=True)
                    alpha_reference=target.read_bytes()
                    input_rgba=neural_texture.masked_colours(input_rgba,w,h,wrap) if masked else neural_texture.cutout_colours(input_rgba,w,h,wrap)
                padded=neural_texture.pad_opaque(input_rgba,w,h,border,wrap)
                source=work/f'{index}-{level}-input.png';source.write_bytes(png_module.png(pw,ph,padded))
                restored=work/f'{index}-{level}-restored.png'
                command=[str(args.neural_tool.resolve()/'realesrgan-ncnn-vulkan.exe'),'-i',str(source),'-o',str(restored),
                         '-m',str(args.neural_tool.resolve()/'models'),'-n','realesrgan-x4plus','-s','4','-t','128','-j','1:1:1']
                with (work/f'{index}-{level}-inference.log').open('w') as log:
                    subprocess.run(command,env=env,cwd=work,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
                subprocess.run([str(decoder),str(restored),str(target),str(pw*4),str(ph*4),
                                str(border*4),str(border*4),str(w*4),str(h*4)],env=env,check=True,timeout=30)
                data=target.read_bytes()
                if len(data)!=w*h*4*16 or set(data[3::4])!={255}:raise ValueError('Opaque restoration dimensions/alpha differ')
                if cutout or masked:
                    data=neural_texture.merge_cutout_colours(data,alpha_reference)
                    if data[3::4]!=alpha_reference[3::4]:raise ValueError('Cutout alpha changed')
                    target.write_bytes(data)
            else:
                subprocess.run([str(exe),str(row['path']),str(target),str(w),str(h),str(args.factor),str(wrap&1),str((wrap>>8)&1)],env=env,check=True)
            width,height=w*args.factor,h*args.factor
            expected=(max(1,levels[0]['width']*args.factor>>level),max(1,levels[0]['height']*args.factor>>level))
            if (width,height)!=expected:raise ValueError('Pilot builder excludes thin-tail resampling')
            pngs.append(png_module.png(width,height,target.read_bytes()))
        if restore:neural_count+=1
        if masked:masked_count+=1
        elif cutout:cutout_count+=1
        add(key,levels[0]['width'],levels[0]['height'],args.factor,pngs,origin=origin,wrap=wrap,
            source_rgba_sha256=[row['sha256'] for row in levels],
            asset_role='observed-single-level-3d' if len(levels)==1 else 'observed-mip-chain',
            archive_references=levels[0].get('references',[]))
        print(json.dumps({'world_chain':index+1,'restored':restore,'masked':masked,'cutout':cutout,'reused':can_reuse}),flush=True)
    ini_bytes=('\n'.join(lines)+'\n').encode('ascii');(pack/'textures.ini').write_bytes(ini_bytes)
    report=dict(scope='verified-mip-texture-pack',textures=groups,ini_sha256=sha(ini_bytes),
                capture_sha256=sha((args.capture/'mip-capture.jsonl').read_bytes()),
                excluded_ambiguous=ambiguous,complete_hd_pack=False,visual_quality_validated=False)
    report['capture_inputs']=[dict(path=str(p.resolve()),metadata_sha256=sha((p/'mip-capture.jsonl').read_bytes())) for p in captures]
    report['reused_chains']=reused_count
    if art_report:report['observed_art']=art_report
    if reuse_verified:report['reuse_manifest_sha256']=reuse_verified['sample_manifest_sha256']
    if neural_pins:
        report['offline_restoration']={'pins':neural_pins,'model':'realesrgan-x4plus','opaque_chains':neural_count-cutout_count-masked_count,
                                       'cutout_chains':cutout_count,'masked_chains':masked_count,
                                       'masked_material_policy_sha256':mask_policy_hash,
                                       'cutout_alpha_policy':'exact-pinned-xbrz-alpha' if (args.restore_cutouts or args.restore_masked) else None,
                                       'context_border':64,'wrap_context':True,'every_authored_level_preserved':True,
                                       'transparency_policy':'admitted masked materials use exact pinned xBRZ alpha; other alpha chains retain xBRZ' if args.restore_masked else ('binary cutouts use exact pinned xBRZ alpha; soft-alpha chains retain xBRZ' if args.restore_cutouts else 'non-opaque chains retain the pinned xBRZ path'),
                                       'source_tool_sha256':sha((ROOT/'tools/build-mip-texture-pack.py').read_bytes())}
    (pack/'sample.json').write_text(json.dumps(report,indent=2)+'\n')
    checked=texture_pack.verify_sample(pack)
    print(json.dumps({'pack':str(pack),'world_chains':checked['mip_chains'],'images':checked['images'],'ini_sha256':checked['ini_sha256']},indent=2))


if __name__=='__main__':main()
