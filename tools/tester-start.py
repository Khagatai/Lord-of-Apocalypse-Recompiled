"""First-run image selection followed by the unchanged normal launch path."""
import os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import tester_setup
def main():
    arguments=sys.argv[1:];image=None
    if arguments and not arguments[0].startswith('--'):image=Path(arguments.pop(0))
    if tester_setup.iso_local_install():
        launcher_pid = os.environ.get('LOA_LAUNCHER_PID', '')
        if (os.environ.get('RECOMPLAUNCHER')!='1' and launcher_pid.isdecimal()
                and not any(flag in arguments for flag in ('--check','--check-cached'))):
            import player_update
            if player_update.offer(tester_setup.ROOT, int(launcher_pid)):
                return 0
        if image:arguments.extend(['--setup-iso',str(image)])
    elif image or not tester_setup.ready():tester_setup.prepare(image)
    return subprocess.call([sys.executable,str(tester_setup.ROOT/'tools/launch-preview.py'),'--variant','saved',*arguments])
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as error:
        print('Cannot start Lord of Apocalypse: '+str(error),file=sys.stderr);raise SystemExit(1)
