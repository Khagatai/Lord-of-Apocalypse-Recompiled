"""Unattended setup and supervised play through the existing title tools.

Only LordOfApocalypse.exe --recomplauncher enters this path. Personal settings,
gameplay and save formats are shared with the normal launcher, unchanged.
"""
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import graphics_settings,launcher_locations,setup_resources

STAGES=('Checking your disc','Preparing game inputs','Generating native code','Compiling native game',
        'Linking native game','Rendering English text','Preparing English archives','Preparing subtitles',
        'Preparing texture tools','Mapping textures','Building HD textures','Validating setup','Setup complete')
READY=ROOT/'private/recomplauncher/ready.json'

class Progress:
    def __init__(self):self.fraction=0.0
    def line(self,text):
        match=re.fullmatch(r'LOA_SETUP_PROGRESS (\d+) (\d+) (\d+) (\d+)\s*',text)
        if not match:return None
        stage,done,total,percent=map(int,match.groups())
        if not 0<=stage<len(STAGES) or not 0<=done<=total<=1000000 or not 0<=percent<=1000:return None
        # Completion means the supervised process exited successfully, not that
        # one intermediate stage happened to emit its own ready notification.
        self.fraction=max(self.fraction,min(percent/1000,.99))
        count=f' ({done}/{total})' if total else ''
        return f'progress {self.fraction:.3f} {STAGES[stage]}{count}'

def run(command,*,prepare=False,environment=None):
    folder=ROOT/'private/recomplauncher/logs';folder.mkdir(parents=True,exist_ok=True)
    # Rotate only this adapter's own previous logs; never game saves or caches.
    owned=sorted(folder.glob('run-*.log'),key=lambda p:p.stat().st_mtime_ns,reverse=True)
    for old in owned[7:]:
        if not old.is_symlink():old.unlink()
    path=folder/f'run-{time.time_ns()}.log';progress=Progress()
    env=dict(os.environ if environment is None else environment)
    env['RECOMPLAUNCHER']='1';env.setdefault('SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS','0')
    env['PYTHONUNBUFFERED']='1';env.pop('LOA_LAUNCHER_PID',None)
    with path.open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                 text=True,encoding='utf-8',errors='replace',bufsize=1)
        with process.stdout:
            for text in process.stdout:
                log.write(text);log.flush()
                output=progress.line(text) if prepare else None
                print(output if output is not None else text,end='\n' if output is not None else '',flush=True)
        return process.wait()

def output_files(root=ROOT):
    return [root/name for name in (
        'private/native-release/lordofapocalypse/lordofapocalypse.exe',
        'private/native-release/lordofapocalypse/lordofapocalypse_image.bin',
        'private/native-release/lordofapocalypse/host-ui-build.json',
        'private/translation/text-pass-16-image/LordOfApocalypse-English-WIP.iso',
        'private/translation/text-pass-16-image/result.json',
        'private/translation/movie-captions/captions.bin')]

def preparation_command(image,args):
    if (ROOT/'private/distribution/release.json').is_file():
        result=[sys.executable,str(ROOT/'tools/local_player_setup.py'),'--image',str(image)]
        for flag,key in (('--jobs','jobs'),('--memory-gib','memory_gib'),('--hd-profile','hd_profile')):
            value=getattr(args,key)
            if value is not None:result.extend((flag,str(value)))
        if args.with_hd:result.append('--with-hd')
        return result
    # A developer's already-built source tree can be added as a local build.
    # Fresh source builds still follow the documented title.py build workflow.
    if args.with_hd:raise ValueError('Use the player release ZIP to prepare optional HD textures.')
    return [sys.executable,str(ROOT/'tools/launch-preview.py'),'--variant','english-text-test','--check-cached']

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    action=p.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare',action='store_true');action.add_argument('--play',action='store_true')
    p.add_argument('--game',type=Path,required=True,help='Unmodified Japanese NPJH50503 disc 1.01 (ISO, CSO or DVD-layout CHD)')
    p.add_argument('--with-hd',action='store_true',help='Opt in to the existing optional local HD build')
    p.add_argument('--jobs',type=int,choices=setup_resources.OPTIONS['compiler_jobs'])
    p.add_argument('--memory-gib',type=int,choices=setup_resources.OPTIONS['memory_gib'])
    p.add_argument('--hd-profile',choices=setup_resources.OPTIONS['hd_profile'])
    p.add_argument('--check-cached',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args(argv)
    if args.play and any((args.with_hd,args.jobs is not None,args.memory_gib is not None,args.hd_profile is not None)):
        p.error('HD and compilation choices belong to --prepare.')
    from disc_images import normalize
    image=normalize(args.game)
    if args.prepare:
        print('progress 0 Checking your unmodified Japanese disc',flush=True)
        # Reuse the existing exact SHA256 validation and persisted ISO selection.
        launcher_locations.select_iso(image,ROOT)
        READY.unlink(missing_ok=True)
        code=run(preparation_command(image,args),prepare=True)
        if code:return code
        missing=[str(path.relative_to(ROOT)) for path in output_files() if not path.is_file()]
        if missing:raise ValueError('Setup did not produce required files: '+', '.join(missing))
        stat=image.stat()
        launcher_locations.atomic_json(READY,dict(schema=1,state='READY',HD_requested=args.with_hd,
            image=str(image),image_size=stat.st_size,image_mtime_ns=stat.st_mtime_ns))
        print('progress 1 Setup complete',flush=True);return 0
    if not READY.is_file() or any(not path.is_file() for path in output_files()):
        print('Game setup is incomplete. Choose Set Up Again in RecompLauncher.',file=sys.stderr);return 2
    ready=json.loads(READY.read_text(encoding='utf-8'));stat=image.stat()
    if any(ready.get(key)!=value for key,value in dict(schema=1,state='READY',image=str(image),
            image_size=stat.st_size,image_mtime_ns=stat.st_mtime_ns).items()):
        print('Your selected disc changed. Choose Set Up Again before Play.',file=sys.stderr);return 2
    import tester_setup
    graphics=graphics_settings.load()
    with_hd=graphics['hd_ui'] and graphics['variant']=='english-text-test'
    if tester_setup.iso_local_install() and not tester_setup.ready(with_hd=with_hd):
        print('The update or HD selection needs preparation. Choose Set Up Again before Play.',file=sys.stderr);return 2
    # The regular launch supervisor supplies the same settings/menu, storage
    # lock, save backups and native error reporting as the project's own GUI.
    command=[sys.executable,str(ROOT/'tools/launch-preview.py'),'--variant','saved']
    if args.check_cached:command.append('--check-cached')
    return run(command)

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as error:
        print('Lord of Apocalypse setup/launch failed: '+str(error),file=sys.stderr,flush=True)
        print('Use the complete Windows x64 player ZIP and your unmodified Japanese NPJH50503 disc 1.01; then choose Set Up Again.',file=sys.stderr,flush=True)
        raise SystemExit(1)
