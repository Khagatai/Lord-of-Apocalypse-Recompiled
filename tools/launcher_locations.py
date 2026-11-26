"""Select existing ISO/installation paths without moving or regenerating files."""
import argparse,contextlib,ctypes,hashlib,json,os,subprocess,sys,tempfile,tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name);json.dump(value,stream,indent=2);stream.write('\n')
        os.replace(temporary,path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)

def game_directory(root=ROOT):
    state=root/'private/launcher/locations.json'
    if not state.exists():return root.resolve()
    record=json.loads(state.read_text(encoding='utf-8'))
    if set(record)!={'schema','game_directory'} or record['schema']!=1 or not isinstance(record['game_directory'],str):
        raise ValueError('Invalid launcher location settings. Select the game folder again.')
    path=Path(record['game_directory'])
    if not path.is_absolute():raise ValueError('The game folder must be an absolute path.')
    return path.resolve()

def validate_game_directory(path):
    path=Path(path).resolve(strict=True)
    if not path.is_dir():raise ValueError('Select an existing game installation folder.')
    if os.name=='nt' and (not str(path).isascii() or str(path).startswith('\\\\')):
        raise ValueError('Select a local ASCII-only game folder, such as D:\\Games\\LordOfApocalypse-Recomp.')
    required=('tools/launch-preview.py','tools/launcher_settings.py','config/lordofapocalypse.toml',
              'config/controller-camera.json','private/tools/python314/python.exe')
    missing=[name for name in required if not (path/name).is_file()]
    if missing:raise ValueError('Select the game folder containing tools, config and private. Missing: '+', '.join(missing))
    config=tomllib.loads((path/'config/lordofapocalypse.toml').read_text(encoding='utf-8'))
    if config.get('disc',{}).get('id')!='NPJH50503':raise ValueError('This folder is not a supported Lord of Apocalypse installation.')
    if (path/'private/launcher/update-in-progress.json').exists():raise ValueError('Finish or recover the update in that game folder first.')
    return path

@contextlib.contextmanager
def target_session(target,root=ROOT):
    """Prevent a second launcher/update using the selected installation."""
    if os.name!='nt' or target.resolve()==root.resolve():
        yield;return
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=(ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p)
    kernel.CreateFileW.restype=ctypes.c_void_p;kernel.CloseHandle.argtypes=(ctypes.c_void_p,)
    folder=target/'private/launcher';folder.mkdir(parents=True,exist_ok=True)
    handle=kernel.CreateFileW(str(folder/'session.lock'),0xc0000000,0,None,4,0x80,None)
    if handle==ctypes.c_void_p(-1).value:raise OSError('The selected game folder is in use by another launcher or update, or is read-only.')
    try:yield
    finally:kernel.CloseHandle(handle)

def select_game_directory(path,root=ROOT):
    target=validate_game_directory(path)
    with target_session(target,root):
        atomic_json(root/'private/launcher/locations.json',dict(schema=1,game_directory=str(target)))
    return target

def iso_path(target):
    state=target/'private/distribution/local-image.json'
    if state.exists():
        record=json.loads(state.read_text(encoding='utf-8'))
        if set(record)!={'schema','path'} or record['schema']!=1 or not isinstance(record['path'],str):raise ValueError('Invalid saved ISO location.')
        path=Path(record['path'])
        if not path.is_absolute():raise ValueError('The saved ISO location must be absolute.')
        return str(path)
    fallback=target.parent/'Lord of Apocalypse (Japan).iso'
    return str(fallback) if fallback.is_file() else ''

def select_iso(path,target,expected=None):
    image=Path(path).resolve(strict=True)
    if not image.is_file() or image.suffix.lower()!='.iso':raise ValueError('Select your unmodified Japanese PSP ISO.')
    if expected is None:
        disc=tomllib.loads((ROOT/'config/lordofapocalypse.toml').read_text(encoding='utf-8'))['disc']
        expected=dict(size=disc['iso_size'],sha256=disc['iso_sha256'])
    if image.stat().st_size!=expected['size']:raise ValueError('Wrong ISO size. Requires unmodified NPJH50503 disc 1.01.')
    with image.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=expected['sha256']:raise ValueError('Wrong ISO SHA256. Select the unmodified Japanese dump, not a patched image.')
    atomic_json(target/'private/distribution/local-image.json',dict(schema=1,path=str(image)))
    return image

def choose(kind):
    # Use the same Windows dialog mechanism as first setup. No user path is
    # interpolated into the PowerShell command, and no execution policy changes.
    if kind=='iso':
        body="$d=[Windows.Forms.OpenFileDialog]::new(); $d.Title='Select your unmodified Lord of Apocalypse Japanese PSP ISO'; $d.Filter='PSP ISO (*.iso)|*.iso'"
    else:
        body="$d=[Windows.Forms.FolderBrowserDialog]::new(); $d.Description='Select the existing game folder containing tools, config and private'; $d.ShowNewFolderButton=$false"
    prop='FileName' if kind=='iso' else 'SelectedPath'
    command="[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); Add-Type -AssemblyName System.Windows.Forms; "+body+f"; if($d.ShowDialog() -eq [Windows.Forms.DialogResult]::OK){{[Console]::Write($d.{prop})}}; $d.Dispose()"
    result=subprocess.run(['powershell','-NoProfile','-STA','-Command',command],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:raise OSError('Could not open the location picker: '+result.stderr.strip())
    return Path(result.stdout) if result.stdout else None

def emit(root=ROOT,message=''):
    target=game_directory(root)
    try:image=iso_path(target)
    except (ValueError,OSError):image=''
    print('LOA_LOCATIONS 1');print(str(target));print(image);print(message)

def dispatch(kind,arguments,root=ROOT):
    target=validate_game_directory(game_directory(root))
    python=target/'private/tools/python314/python.exe'
    if kind=='settings':script=target/'tools/launcher_settings.py'
    else:
        packaged=(target/'private/distribution/release.json').is_file()
        script=target/'tools'/('tester-start.py' if packaged else 'launch-preview.py')
        if not packaged:arguments=['--variant','saved',*arguments]
    with target_session(target,root):
        return subprocess.call([str(python),'-u',str(script),*arguments],cwd=target)

def main(argv=None):
    arguments=list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in ('--launch','--settings'):
        return dispatch(arguments[0][2:],arguments[1:])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('read','iso','game'));args=parser.parse_args(arguments)
    message=''
    if args.action!='read':
        selected=choose(args.action)
        if selected is None:message='Selection cancelled. Locations are unchanged.'
        elif args.action=='game':
            select_game_directory(selected);message='Game folder selected. Files were not moved. Its saves and settings will be used.'
        else:
            target=validate_game_directory(game_directory())
            with target_session(target):select_iso(selected,target)
            message='Verified ISO location saved. Existing game and HD files are kept.'
    emit(message=message);return 0

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError) as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
