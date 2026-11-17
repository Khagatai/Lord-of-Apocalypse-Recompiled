"""Bounded native boot of an ISO-built installation, with isolated empty saves.

This verifies real execution and displayed pixels, not full gameplay, audio,
campaign progression or multiplayer acceptance. No PPSSPP runtime is launched.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,runtime_assets,ui_runtime,translation_candidate,texture_pack,sampler_pack


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fps',type=int,choices=(30,60),default=30);p.add_argument('--with-HD',action='store_true');a=p.parse_args()
    out=a.output.resolve()
    if not out.is_relative_to(ROOT/'private') or out.exists():raise ValueError('Use a fresh private boot diagnostic folder')
    revision=title.verify_launch_inputs('release');menu=ui_runtime.verify(ROOT);build=title.build_directory('release')
    image=ROOT/'private/translation/text-pass-16-image/LordOfApocalypse-English-WIP.iso'
    translation_candidate.verify(image,image.parent/'result.json')
    flat=sha(build/'lordofapocalypse_image.bin')
    if flat!='b0d370ebcfb33df3517a40c97c1b5c0ef0f6d7ed71a1efc6a4fce7e73c46dfb0':raise ValueError('ISO-built flat memory image differs')
    env=title.environment();runtime_assets.configure_fonts(env,build)
    env.update(PSP_ISO=str(image),SR_MEMSTICK=str(out/'memstick'),SR_MODULE_DIR=str(ROOT/'private/modules'),SR_REAL_MODULE_START='1',
        SR_BOOT_PATH=title.CONFIG['module']['start_thread']['argument'],SR_HEADLESS='1',SR_WINDOW_HIDDEN='1',SR_VIDEO='vulkan',SR_GPU_GE='1',
        SR_PADWIDTH='0',SR_EXIT_AT_VBLANK='360',SR_FIRST_FRAME_DUMP='1',SR_FBSNAP='120',SR_FBSNAP_WINDOWS='1-360',
        SR_RESOLUTION_SCALE='1',SR_GPU_SCALE='1',SR_TEX_REPLACE='',SR_ACE='off',LOA_MIP_TEXTURES='0',LOA_SAMPLER_PACK='0',
        LOA_GAMEPLAY_FPS=str(a.fps),LOA_MOVIE_CAPTIONS=str(ROOT/'private/translation/movie-captions/captions.bin'))
    if a.with_HD:
        pack=ROOT/'private/hd-remaster-pack';checked=texture_pack.verify_sample(pack)
        sampler_pack.require_runtime(checked['sampler_namespace'],json.loads((build/'host-ui-build.json').read_text()),sha(build/'lordofapocalypse.exe'))
        texture_pack.enable(env,pack);env['LOA_MIP_TEXTURES']='1'
    out.mkdir(parents=True)
    command=[str(build/'lordofapocalypse.exe'),'--image',str(build/'lordofapocalypse_image.bin'),f"{title.CONFIG['module']['base']:08x}",
        f"{title.CONFIG['module']['entry']:08x}",str(ROOT/'private/oracle-prefix/entry-prefix.trace'),'none','--sched','--gui']
    with (out/'native.log').open('wb') as log:
        result=subprocess.run(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    frames=[]
    for path in out.glob('*.ppm'):
        raw=path.read_bytes();parts=raw.split(b'\n',3)
        if len(parts)!=4 or parts[0]!=b'P6' or parts[2]!=b'255':raise ValueError('Unrecognized captured framebuffer')
        w,h=map(int,parts[1].split());pixels=parts[3]
        if len(pixels)!=w*h*3:raise ValueError('Captured framebuffer is truncated')
        colours=len({pixels[i:i+3] for i in range(0,len(pixels),3)})
        frames.append(dict(file=path.name,width=w,height=h,colours=colours,sha256=sha(path)))
    if result.returncode or not any(row['colours']>1 for row in frames):raise RuntimeError('Native boot failed or produced no nonblank frame; inspect '+str(out/'native.log'))
    log=(out/'native.log').read_text(errors='replace');execution=re.search(r'^EXEC_SHARE (.+)$',log,re.MULTILINE)
    if not execution:raise RuntimeError('Native execution counters were not reported')
    fields=dict(re.findall(r'(\w+)=([^ ]+)',execution.group(1)))
    counters={key:int(fields[key]) for key in ('interp_entries','interp_instructions','entries_dispatch_miss','miss_targets')}
    if any(counters.values()):raise RuntimeError('Native boot entered interpreter/fallback dispatch; inspect native.log')
    report=dict(status='PASS',scope='360-vblank native boot with isolated empty save storage',fps_setting=a.fps,HD_enabled=a.with_HD,
        native_exit=result.returncode,framework_commit=revision,flat_image_sha256=flat,frames=frames,menu_dependency_preflight=menu,
        PPSSPP_launched=False,prepared_game_outputs_copied_in=False,audio_audited=False,menu_interaction_tested=False,
        gameplay_tested=False,multiplayer_tested=False,full_campaign_tested=False)
    report['execution_counters']=counters
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
