"""Prepare a tester's verified local images from bundled binary differences."""
import argparse,contextlib,ctypes,hashlib,json,os,shutil,subprocess,sys,tempfile,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'private/distribution/local-image.json'
MANIFEST=ROOT/'private/distribution/release.json'
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def private_path(name):
    path=(ROOT/name).resolve()
    if not path.is_relative_to((ROOT/'private').resolve()):raise ValueError('Installer output escapes private storage')
    return path
def matches(path,record):return path.is_file() and path.stat().st_size==record['size'] and sha(path)==record['sha256']

@contextlib.contextmanager
def patcher_paths(*paths):
    """Give the ANSI-only patcher ASCII aliases without copying any input.

    DefineDosDevice mappings belong to this Windows logon session, use unique
    names, and are removed on success or failure. They can refer to files on
    other volumes or UNC shares, unlike hardlinks. No admin/global mapping is
    requested. Python continues to verify the real Unicode filenames.
    """
    if os.name!='nt':
        yield [str(p) for p in paths];return
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    define=kernel.DefineDosDeviceW
    define.argtypes=(ctypes.c_uint32,ctypes.c_wchar_p,ctypes.c_wchar_p)
    define.restype=ctypes.c_int
    mappings=[];aliases=[]
    try:
        for path in paths:
            full=str(Path(path).resolve())
            native='\\??\\'+('UNC\\'+full[2:] if full.startswith('\\\\') else full)
            name='LOA-patch-'+uuid.uuid4().hex
            if not define(0x1|0x8,name,native):raise ctypes.WinError(ctypes.get_last_error())
            mappings.append((name,native));aliases.append('\\\\.\\'+name)
        yield aliases
    finally:
        failures=[]
        for name,native in reversed(mappings):
            if not define(0x1|0x2|0x4|0x8,name,native):failures.append(ctypes.get_last_error())
        if failures:raise OSError('Could not remove temporary patcher filename mapping: '+str(failures))
def choose_image():
    command="[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); Add-Type -AssemblyName System.Windows.Forms; $d=[Windows.Forms.OpenFileDialog]::new(); $d.Title='Select your unmodified Lord of Apocalypse Japanese PSP ISO'; $d.Filter='PSP ISO (*.iso)|*.iso'; if($d.ShowDialog() -eq [Windows.Forms.DialogResult]::OK){[Console]::Write($d.FileName)}; $d.Dispose()"
    result=subprocess.run(['powershell','-NoProfile','-STA','-Command',command],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:raise RuntimeError('Could not open the ISO picker. Drag your ISO onto LordOfApocalypse.exe instead.')
    if not result.stdout:raise RuntimeError('Setup cancelled; no game files were changed.')
    return Path(result.stdout)
def prepare(image=None):
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('schema')==2:
        import local_player_setup
        if image is None and STATE.is_file():image=Path(json.loads(STATE.read_text())['path'])
        return local_player_setup.prepare(image or choose_image())
    if manifest.get('schema')!=1:raise ValueError('Unsupported tester release manifest')
    if image is None and STATE.is_file():image=Path(json.loads(STATE.read_text())['path'])
    image=Path(image or choose_image()).resolve(strict=True)
    if not matches(image,manifest['original']):
        raise ValueError('Wrong game image. Requires unmodified NPJH50503 Japan, disc 1.01: SHA256 '+manifest['original']['sha256'])
    tool=private_path(manifest['patcher']['path'])
    if sha(tool)!=manifest['patcher']['sha256']:raise ValueError('Bundled patcher hash differs; extract the tester ZIP again')
    source=image;made=[]
    for item in manifest['images']:
        target=private_path(item['path']);patch=private_path(item['patch'])
        if image==target:raise ValueError('The original ISO must be separate from generated images')
        if sha(patch)!=item['patch_sha256']:raise ValueError('Bundled image patch is corrupt')
        if target.exists():
            if not matches(target,item):raise ValueError('Existing generated image differs; move it aside before running setup: '+str(target))
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            if shutil.disk_usage(target.parent).free<item['size']+64*1024*1024:raise OSError('Not enough free space to prepare '+target.name)
            fd,temp=tempfile.mkstemp(prefix='loa-image-',suffix='.tmp',dir=target.parent);os.close(fd);temporary=Path(temp);temporary.unlink()
            try:
                print('Preparing '+item['label']+' from your local dump...',flush=True)
                with patcher_paths(source,patch,temporary) as (src,delta,out):
                    result=subprocess.run([str(tool),'-d','-s',src,delta,out],capture_output=True,text=True)
                if result.returncode:raise RuntimeError('Image preparation failed: '+result.stderr.strip())
                if not matches(temporary,item):raise ValueError('Prepared image hash differs; original image was left unchanged')
                os.replace(temporary,target);made.append(item['path'])
            finally:temporary.unlink(missing_ok=True)
        source=target
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(dict(schema=1,path=str(image)),indent=2)+'\n',encoding='utf-8')
    return dict(status='PASS',images_prepared=made,original_unchanged=matches(image,manifest['original']))
def ready():
    if not STATE.is_file() or not MANIFEST.is_file():return False
    manifest=json.loads(MANIFEST.read_text())
    if manifest.get('schema')==2:
        import local_player_setup
        return local_player_setup.ready()
    return all(private_path(r['path']).is_file() for r in manifest['images'])
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',type=Path);a=parser.parse_args()
    print(json.dumps(prepare(a.image),indent=2))
if __name__=='__main__':main()
