"""Capture a private save-screen texture sample or validate a local replacement pack."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import graphics_settings as settings
import title
import texture_pack


def helper(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),ROOT/'tools'/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checkpoint_route(name):
    raw=(ROOT/'config/validation-routes.json').read_bytes()
    config=json.loads(raw);route=config['routes'][name]
    count=route['boot_events']
    if type(count) is not int or not 0<=count<=len(config['boot_events']):
        raise ValueError('Invalid checkpoint boot event count')
    events=config['boot_events'][:count]+route['events'];previous=-1
    for event in events:
        if not isinstance(event,list) or len(event) not in (3,5):
            raise ValueError('Invalid checkpoint event')
        start,button,duration=event[:3]
        if (type(start) is not int or type(duration) is not int or
            not previous<start<9000 or not 0<duration<=9000-start or
            button not in ('0','CIRCLE','START','LEFT','RIGHT')):
            raise ValueError('Invalid bounded checkpoint input')
        if len(event)==5 and any(type(v) is not int or not 0<=v<=255 for v in event[3:]):
            raise ValueError('Invalid checkpoint analog input')
        previous=start
    script='\n'.join(' '.join(map(str,event)) for event in events)+'\n'
    return script,route['frame_window'],hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--image',type=Path,help='Explicit private WIP image with an adjacent verified result.json')
    parser.add_argument('--save-fixture',type=Path,help='Copy an existing private campaign save; never write the source')
    parser.add_argument('--probe',type=Path,help='Private diagnostic executable; default is the release executable')
    parser.add_argument('--pack',type=Path,help='Private local replacement pack; otherwise collect identities with an empty pack')
    parser.add_argument('--font-scene',action='store_true',help='Capture live font textures with the diagnostic observer executable')
    parser.add_argument('--gpu-font-upload',action='store_true',help='Capture actual small RGBA decodes returned to the GPU texture cache')
    parser.add_argument('--frame-window',help='Bounded capture range; defaults to the selected route or the save-loaded prompt')
    parser.add_argument('--quality',action='store_true',help='Also test FSR 1, 16x AF, mipmaps, full colour and 2x supersampling at 4x rendering')
    parser.add_argument('--texture-scale',type=int,choices=(1,2,3,4,5,6),default=1,help='Test real xBRZ texture scaling (1 is off)')
    parser.add_argument('--hd-ui',action='store_true',help='Resolve the HD UI through the same saved-toggle selection as normal launches')
    parser.add_argument('--mip-textures',action='store_true',help='Require mip-chain scaling in the release or diagnostic executable')
    parser.add_argument('--capture-mips',action='store_true',help='Capture private decoded mip chains and measured texture identities')
    parser.add_argument('--gameplay-fps',type=int,choices=(30,60),default=30,help='Select the title timing mode for this isolated check')
    parser.add_argument('--paced',action='store_true',help='Use the normal clock and vblank pacing instead of the deterministic work clock')
    parser.add_argument('--capture-art',action='store_true',help='Diagnostic observer: capture bound single-level 3D artwork')
    parser.add_argument('--capture-ui-art',action='store_true',help='Also inspect large 2D bindings; not automatically admitted as artwork')
    parser.add_argument('--require-mip-replacements',action='store_true',help='Require complete replacement mip chains to actually queue without rejection')
    parser.add_argument('--seconds',type=int,choices=range(30,181),help='Bounded host checkpoint timeout; allow diagnostic texture file writes extra time')
    route_group=parser.add_mutually_exclusive_group()
    route_group.add_argument('--padscript',type=Path,help='Private bounded gameplay input route; source saves remain copied')
    route_group.add_argument('--route',choices=('title','town','sanctuary','inventory'),help='Reproduce a source-configured checkpoint with copied saves')
    args=parser.parse_args()
    if args.route and not args.save_fixture:
        parser.error('Source checkpoint routes require a copied --save-fixture')
    route=checkpoint_route(args.route) if args.route else None
    args.frame_window=args.frame_window or ('-'.join(map(str,route[1])) if route else '990-1000')
    try:
        low,high=map(int,args.frame_window.split('-'))
    except ValueError:
        parser.error('Use a LOW-HIGH frame window')
    if not 0<=low<=high<=9000:
        parser.error('Frame window must be within 0-9000')
    if (args.font_scene or args.gpu_font_upload) and not args.probe:
        parser.error('Font observations require the diagnostic observer executable')
    if args.capture_mips and not args.mip_textures:
        parser.error('Mip capture requires --mip-textures')
    if args.capture_art and not args.probe:
        parser.error('Single-level artwork capture requires the diagnostic observer')
    if args.capture_ui_art and not args.capture_art:parser.error('--capture-ui-art requires --capture-art')
    if args.require_mip_replacements and (not args.mip_textures or not args.pack):
        parser.error('Replacement checks require --mip-textures and an explicit --pack')
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    for path in (args.probe,args.pack,args.padscript,args.image,args.save_fixture):
        if path and (not path.resolve().is_relative_to(ROOT/'private') or not path.exists()):
            parser.error('Probe and pack must exist under private/')
    title.verify_inputs()
    preferences=settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None
    image=args.image.resolve() if args.image else settings.WIP_FOLDER/'LordOfApocalypse-English-WIP.iso'
    from translation_candidate import verify
    verify(image,image.parent/'result.json')
    output.mkdir(parents=True)
    if route:
        args.padscript=output/'route.pad'
        args.padscript.write_text(route[0],encoding='ascii',newline='\n')
    pack=args.pack.resolve() if args.pack else texture_pack.selected_folder({'hd_ui':args.hd_ui},'vulkan','english-text-test')
    supplied=pack is not None
    verified_pack=None
    if supplied:
        verified_pack=texture_pack.verify_sample(pack)
    else:
        pack=output/'empty-pack'
        pack.mkdir()
        (pack/'textures.ini').write_text('[options]\nhash = quick\n[hashes]\n')
    env=title.environment()
    graphics=dict(settings.ORIGINAL,render_scale=4,vsync=False,texture_scale=args.texture_scale,hd_ui=args.hd_ui,gameplay_fps=args.gameplay_fps)
    if args.quality:
        graphics.update(anisotropy=16,mipmaps=True,full_color=True,supersampling=2,upscale='fsr1')
    env.update(settings.environment(graphics))
    env['LOA_MIP_TEXTURES']='1' if args.mip_textures else '0'
    env['LOA_MIP_CAPTURE']='1' if args.capture_mips else '0'
    env['LOA_ART_CAPTURE']='1' if args.capture_art else '0'
    env['LOA_ART_CAPTURE_UI']='1' if args.capture_ui_art else '0'
    texture_pack.enable(env,pack)
    if args.font_scene:
        env['LOA_FONT_SCENE']='1'
    if args.gpu_font_upload:
        env['LOA_GPU_FONT_UPLOAD']='1'
    result=helper('check-text-sharpening').window_check(output/'run',image,env,args.probe.resolve() if args.probe else None,(low,high),args.padscript,args.seconds,args.save_fixture,deterministic=not args.paced)
    log=(output/'run/native.log').read_text(errors='replace')
    png=helper('inventory-textures').png
    metadata=output/'run/texture-probe.jsonl'
    rows=[json.loads(line) for line in metadata.read_text().splitlines()] if metadata.exists() else []
    for row in rows:
        if not row['decoded']:
            continue
        raw=output/'run'/('texture-'+row['key']+'.rgba')
        pixels=raw.read_bytes()
        if len(pixels)!=row['width']*row['height']*4:
            raise ValueError('Decoded texture size mismatch')
        preview=raw.with_suffix('.png')
        preview.write_bytes(png(row['width'],row['height'],pixels))
        row['preview']=preview.name
        row['rgba_sha256']=hashlib.sha256(pixels).hexdigest()
    font_metadata=output/'run/font-scene.jsonl'
    fonts=[json.loads(line) for line in font_metadata.read_text().splitlines()] if font_metadata.exists() else []
    for row in fonts:
        if row['decoded']:
            raw=output/'run'/('font-scene-'+row['address']+'-'+row['fingerprint']+'.rgba')
            preview=raw.with_suffix('.png')
            preview.write_bytes(png(row['width'],row['height'],raw.read_bytes()))
            row['preview']=preview.name
    upload_metadata=output/'run/gpu-font-upload.jsonl'
    uploads=[json.loads(line) for line in upload_metadata.read_text().splitlines()] if upload_metadata.exists() else []
    for row in uploads:
        if row['decoded']:
            raw=output/'run'/('gpu-font-'+row['address']+'-'+row['fingerprint']+'.rgba')
            preview=raw.with_suffix('.png')
            preview.write_bytes(png(row['width'],row['height'],raw.read_bytes()))
            row['preview']=preview.name
    unchanged=preferences==(settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None)
    pack_unchanged=not supplied or texture_pack.verify_sample(pack)['sample_manifest_sha256']==verified_pack['sample_manifest_sha256']
    exit_line=next((line for line in log.splitlines() if 'TEX_REPLACE: exit' in line),'')
    counters={key:int(value) for key,value in re.findall(r'(hits|bound_draws|loaded|load_failed|skipped|bad_factor)=(\d+)',exit_line)}
    used=counters.get('hits',0)>0 and counters.get('bound_draws',0)>0 and counters.get('loaded',0)>0
    scale_match=re.search(r'TEX_SCALE: draws \(scaled_binds=(\d+)',log)
    scale_used=bool(scale_match and int(scale_match.group(1))>0 and f'TEX_SCALE: on (xbrz={args.texture_scale},' in log)
    mip_exit=next((line for line in log.splitlines() if line.startswith('LOA_MIPS: exit')),'')
    mip_counters={k:int(v) for k,v in re.findall(r'\b(queued|uploaded|levels|bound|failed|replacement_queued|replacement_rejected)=(\d+)',mip_exit)}
    report={'scope':'private-hd-ui-checkpoint','frame_window':[low,high],'native':result,'preferences_unchanged':unchanged,
            'input_route':dict(name=args.route,config_sha256=route[2],padscript_sha256=hashlib.sha256(args.padscript.read_bytes()).hexdigest()) if route else None,
            'graphics_settings':graphics,'enhancement_spec':env['SR_ACE'],
            'texture_pack_log':[line for line in log.splitlines() if 'TEX_REPLACE:' in line],
            'texture_scaling_log':[line for line in log.splitlines() if 'TEX_SCALE:' in line],
            'replacement_counters':counters,'pack_used':used,
            'texture_scaling_used':scale_used,
            'mip_texture_log':[line for line in log.splitlines() if line.startswith('LOA_MIPS:')],
            'sampler_namespace_log':[line for line in log.splitlines() if line.startswith('LOA_SAMPLER_PACK:')],
            'mip_texture_counters':mip_counters,
            'texture_pack_manifest_sha256':verified_pack['sample_manifest_sha256'] if verified_pack else None,
            'texture_pack_unchanged':pack_unchanged,
            'textures':rows,'font_scene':fonts,'gpu_font_upload':uploads,'visual_quality_validated':False,'gameplay_fps_validated':False}
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    printable={key:value for key,value in report.items() if key not in ('textures','font_scene','gpu_font_upload')}
    printable['native']={key:value for key,value in result.items() if key!='font_files_sha256'}
    printable['native']['font_files_recorded']=len(result.get('font_files_sha256',{}))
    print(json.dumps(printable,indent=2))
    print('Unique observed textures:',len(rows))
    if result['returncode']!=0 or result['timed_out'] or not result['save_fixture_source_unchanged'] or not result['font_files_unchanged'] or not unchanged or not pack_unchanged:
        raise SystemExit(1)
    if 'TEX_REPLACE: refused' in log or 'TEX_REPLACE: on' not in log:
        raise SystemExit('Replacement pack was not accepted; inspect native.log')
    if supplied and (not used or any(counters.get(key,0)>0 for key in ('load_failed','skipped','bad_factor'))):
        raise SystemExit('The supplied pack did not draw successfully; inspect actual replacement counters')
    if args.texture_scale>1 and not scale_used:
        raise SystemExit('Requested texture scaling did not actually draw; inspect native.log')
    if args.mip_textures and (not mip_counters.get('uploaded',0) or not mip_counters.get('bound',0) or mip_counters.get('failed',0)):
        raise SystemExit('Mip scaling did not draw successfully; inspect native.log')
    if args.require_mip_replacements and (not mip_counters.get('replacement_queued',0) or mip_counters.get('replacement_rejected',0)):
        raise SystemExit('Replacement mip chains did not draw without rejection; inspect native.log')
    if verified_pack and verified_pack.get('sampler_namespace') and 'LOA_SAMPLER_PACK: on' not in log:
        raise SystemExit('This executable did not enable the required sampler namespace')


if __name__=='__main__':
    main()
