"""First-run image selection followed by the unchanged normal launch path."""
import subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import tester_setup
def main():
    arguments=sys.argv[1:];image=None
    if arguments and not arguments[0].startswith('--'):image=Path(arguments.pop(0))
    if image or not tester_setup.ready():tester_setup.prepare(image)
    return subprocess.call([sys.executable,str(tester_setup.ROOT/'tools/launch-preview.py'),'--variant','saved',*arguments])
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as error:
        print('Cannot start Lord of Apocalypse: '+str(error),file=sys.stderr);raise SystemExit(1)
