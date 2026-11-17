"""Owned-window campaign exploration with copied saves and real input recording.

Local command files drive ordinary SDL keyboard events. No guest state, imports,
PSP results or saved source files are patched. This records exploration evidence;
it does not certify a route or campaign as passed.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import graphics_settings as settings
import runtime_assets
import sampler_pack
import save_storage
import texture_pack
import title
import translation_candidate
import window_settings

KEYS={'circle':0x5a,'cross':0x58,'square':0x41,'triangle':0x53,
      'start':0x0d,'select':0x10,'ltrigger':0x51,'rtrigger':0x57,
      'up':0x26,'down':0x28,'left':0x25,'right':0x27,
      'stick_up':0x49,'stick_down':0x4b,'stick_left':0x4a,'stick_right':0x4c,
      'pause':0x70,'back':0x1b}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--save-fixture',type=Path,required=True)
    parser.add_argument('--minutes',type=int,choices=range(1,121),default=60)
    parser.add_argument('--capture-mips',action='store_true',help='Record bounded private authored-mip captures for art coverage')
    parser.add_argument('--pack',type=Path,help='Explicit verified private HD candidate; never change normal preferences')
    parser.add_argument('--boot-padscript',type=Path,help='Private recorded boot input; later exploration still uses ordinary owned-window input')
    parser.add_argument('--net-profile',type=Path,help='Explicit private co-op test profile; normal network settings remain unchanged')
    parser.add_argument('--original-graphics',action='store_true',help='Isolated 2x original textures for a multi-instance networking check')
    parser.add_argument('--candidate-image',type=Path,help='Explicit private translation image for isolated asset review')
    parser.add_argument('--candidate-report',type=Path,help='Required verified build report for --candidate-image')
    parser.add_argument('--audio-diagnostics',action='store_true',help='Measure audio queues, PCM peaks and SAS saturation; no sample changes')
    parser.add_argument('--capture-audio',action='store_true',help='Private device PCM recording; requires --audio-diagnostics')
    args=parser.parse_args()
    if args.capture_audio and not args.audio_diagnostics:parser.error('--capture-audio requires --audio-diagnostics')
    output=args.output.resolve();fixture=args.save_fixture.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():parser.error('Use a fresh private session folder')
    if not fixture.is_relative_to(ROOT/'private') or not fixture.is_dir():parser.error('Use an existing private save fixture')
    boot=args.boot_padscript.resolve() if args.boot_padscript else None
    if boot and (not boot.is_relative_to(ROOT/'private') or not boot.is_file() or boot.stat().st_size>65536):
        parser.error('Use a bounded private boot padscript')
    revision=title.verify_inputs()
    if bool(args.candidate_image)!=bool(args.candidate_report):parser.error('Candidate image and report must be supplied together')
    image=args.candidate_image.resolve() if args.candidate_image else settings.WIP_FOLDER/'LordOfApocalypse-English-WIP.iso'
    candidate_report=args.candidate_report.resolve() if args.candidate_report else image.parent/'result.json'
    image_hash,report_hash=translation_candidate.verify(image,candidate_report)
    before=save_storage.tree_hashes(fixture)
    preferences=settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None
    output.mkdir(parents=True);(output/'commands').mkdir();(output/'answers').mkdir()
    shutil.copytree(fixture,output/'memstick',ignore=shutil.ignore_patterns('.preview.lock'))
    if before!=save_storage.tree_hashes(output/'memstick') or before!=save_storage.tree_hashes(fixture):raise RuntimeError('Save changed during copy')
    build=title.build_directory('release');executable=build/'lordofapocalypse.exe'
    env=title.environment()
    if args.audio_diagnostics:
        env.update(LOA_AUDIO_DIAGNOSTICS='1',SR_PERF='1',SR_AUDIOSTAT='1',SR_MPEGAV='1')
        if args.capture_audio:env['SR_AUDIODUMP']=str(output/'device.wav')
    for key in ('SR_HEADLESS','SR_WINDOW_HIDDEN','SR_PADSCRIPT','SR_PAD','SR_NOINPUT','SR_EXIT_AT_VBLANK',
                'SR_PAUSE_SCRIPT','SR_FBSNAP','SR_FBSNAP_WINDOWS','SR_SAMPLE_SPEC','SR_NOVBPACE'):
        env.pop(key,None)
    graphics=dict(settings.DEFAULTS,fullscreen=False,window_size=(1920,1080),vsync=False)
    if args.original_graphics:graphics=dict(settings.ORIGINAL,render_scale=2,window_size=(1920,1080),vsync=False)
    env.update(settings.environment(graphics))
    if args.net_profile:
        import network_settings
        network_profile=network_settings.load(args.net_profile)
        if network_profile['mode']=='host':raise ValueError('Use a separately owned loopback lobby and join profiles for campaign tests')
        env.update(network_settings.environment(network_profile,args.net_profile))
    if boot:env['SR_PADSCRIPT']=str(boot)
    env['LOA_MIP_CAPTURE']='1' if args.capture_mips else '0'
    pack=texture_pack.selected_folder(graphics,'vulkan','english-text-test',args.pack)
    pack_verified=texture_pack.verify_sample(pack) if pack else None
    if pack:
        sampler_pack.require_runtime(pack_verified.get('sampler_namespace'),
            json.loads((build/'host-ui-build.json').read_text()),hashlib.sha256(executable.read_bytes()).hexdigest())
        texture_pack.enable(env,pack)
    font_root,font_hashes=runtime_assets.configure_fonts(env,build)
    env.update(PSP_ISO=str(image),SR_MEMSTICK=str(output/'memstick'),SR_MODULE_DIR=str(ROOT/'private/modules'),
               SR_REAL_MODULE_START='1',SR_BOOT_PATH=title.CONFIG['module']['start_thread']['argument'],
               SR_VIDEO='vulkan',SR_GPU_GE='1',SR_PADWIDTH='0',SR_INLOG='1',
               NK_INPUT_PROFILE=str(ROOT/'config/controller-camera.json'))
    command=[str(executable),'--image',str(build/'lordofapocalypse_image.bin'),
             f"{title.CONFIG['module']['base']:08x}",f"{title.CONFIG['module']['entry']:08x}",
             str(ROOT/'private/oracle-prefix/entry-prefix.trace'),'none','--sched','--gui']
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.PostMessageW.argtypes=(w.HWND,w.UINT,w.WPARAM,w.LPARAM)
    user.GetWindowThreadProcessId.argtypes=(w.HWND,ctypes.POINTER(w.DWORD))
    user.GetClassNameW.argtypes=(w.HWND,w.LPWSTR,ctypes.c_int)
    user.MapVirtualKeyW.argtypes=(w.UINT,w.UINT)
    visit_type=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    user.EnumWindows.argtypes=(visit_type,w.LPARAM)
    report={'scope':'copied-save-campaign-exploration','framework_commit':revision,
            'image_sha256':image_hash,'candidate_report_sha256':report_hash,
            'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
            'save_fixture':str(fixture),'source_save_sha256':before,'graphics':graphics,
            'texture_pack':str(pack) if pack else None,'texture_pack_manifest_sha256':pack_verified['sample_manifest_sha256'] if pack else None,
            'route_validated':False,'campaign_validated':False,'capture_mips':args.capture_mips,
            'audio_diagnostics':args.audio_diagnostics,'audio_capture':args.capture_audio,'commands':[]}
    report['boot_input']=dict(file=str(boot),sha256=hashlib.sha256(boot.read_bytes()).hexdigest()) if boot else None
    started=time.monotonic();process=None;window=None;held=set()
    with (output/'native.log').open('wb') as log:
        try:
            process=subprocess.Popen(command,cwd=output,env=env,stdout=log,stderr=subprocess.STDOUT)
            report['window']=window_settings.apply(process.pid,(1920,1080))
            windows=[]
            @visit_type
            def visit(hwnd,_):
                owner=w.DWORD();name=ctypes.create_unicode_buffer(128)
                user.GetWindowThreadProcessId(hwnd,ctypes.byref(owner));user.GetClassNameW(hwnd,name,128)
                if owner.value==process.pid and name.value=='SDL_app':windows.append(hwnd)
                return True
            user.EnumWindows(visit,0)
            if len(windows)!=1:raise RuntimeError('Expected exactly one owned SDL window')
            window=windows[0]
            def owned():
                owner=w.DWORD();user.GetWindowThreadProcessId(window,ctypes.byref(owner))
                if owner.value!=process.pid or process.poll() is not None:raise RuntimeError('Owned game window no longer available')
            def key(code,down):
                owned();scan=user.MapVirtualKeyW(code,0)
                flags=1|(scan<<16)|((1<<24) if code in (0x25,0x26,0x27,0x28) else 0)
                if not user.PostMessageW(window,0x100 if down else 0x101,code,flags|(0 if down else (3<<30))):raise OSError(ctypes.get_last_error())
            (output/'ready.json').write_text(json.dumps({'pid':process.pid,'window':window,'ready':True},indent=2)+'\n')
            done=set();closing=False
            while process.poll() is None and time.monotonic()-started<args.minutes*60 and not closing:
                for path in sorted((output/'commands').glob('*.json')):
                    if path.name in done:continue
                    done.add(path.name);entry={'command':path.name,'elapsed_seconds':round(time.monotonic()-started,3)}
                    try:
                        request=json.loads(path.read_text());kind=request['type'];owned()
                        if kind=='keys':
                            names=request['keys'];duration=float(request.get('hold',0.12));settle=float(request.get('settle',0.5))
                            if not isinstance(names,list) or not 1<=len(names)<=6 or len(set(names))!=len(names) or any(n not in KEYS for n in names) or not 0.02<=duration<=5 or not 0<=settle<=30:raise ValueError('Invalid bounded key command')
                            try:
                                for name in names:key(KEYS[name],True);held.add(KEYS[name])
                                time.sleep(duration)
                            finally:
                                for code in tuple(held):key(code,False);held.remove(code)
                            time.sleep(settle)
                        elif kind=='wait':
                            duration=float(request['seconds'])
                            if not 0<=duration<=30:raise ValueError('Wait exceeds 30 seconds')
                            time.sleep(duration)
                        elif kind=='close':closing=True
                        elif kind!='snapshot':raise ValueError('Unknown command type')
                        entry['request']=request
                        if not closing:
                            owned();picture=output/(path.stem+'.png')
                            subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                                            '-Window',str(window),'-Owner',str(process.pid),'-Output',str(picture)],
                                           capture_output=True,check=True,timeout=10)
                            entry['screenshot']=picture.name;entry['screenshot_sha256']=hashlib.sha256(picture.read_bytes()).hexdigest()
                        entry['success']=True
                    except Exception as error:entry.update(success=False,error=str(error))
                    report['commands'].append(entry)
                    (output/'answers'/path.name).write_text(json.dumps(entry,indent=2)+'\n')
                time.sleep(0.1)
        except Exception as error:report['error']=str(error)
        finally:
            if process is not None:
                if process.poll() is None:
                    if window:
                        owner=w.DWORD();user.GetWindowThreadProcessId(window,ctypes.byref(owner))
                        if owner.value==process.pid:user.PostMessageW(window,0x10,0,0)
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10);report['forced_termination']=True
                report['returncode']=process.returncode
    report['source_save_unchanged']=before==save_storage.tree_hashes(fixture)
    report['font_files_unchanged']=font_hashes==save_storage.tree_hashes(font_root)
    report['preferences_unchanged']=preferences==(settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None)
    report['texture_pack_unchanged']=not pack or texture_pack.verify_sample(pack)['sample_manifest_sha256']==pack_verified['sample_manifest_sha256']
    report['elapsed_seconds']=round(time.monotonic()-started,3)
    replay=[str(title.PYTHON),str(title.FRAMEWORK/'tools/padscript_from_log.py'),str(output/'native.log'),
            '--minimum-width','1','--stick-min-width','1','--output',str(output/'recorded.pad')]
    run=subprocess.run(replay,capture_output=True,text=True)
    report['input_recording_returncode']=run.returncode
    (output/'input-recording.log').write_text(run.stdout+run.stderr)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_save_sha256','commands')},indent=2))
    if report.get('returncode')!=0 or report.get('error') or not all(report[k] for k in ('source_save_unchanged','font_files_unchanged','preferences_unchanged','texture_pack_unchanged')):raise SystemExit(1)

if __name__=='__main__':main()
