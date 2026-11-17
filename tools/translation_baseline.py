"""Materialize the upstream build baseline only for translation work, then discard it.

Normal WIP play uses pinned per-file metadata and never calls this module.
The small original patch is retained as an authoring input, not a playable version.
"""
import atexit,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OWNED={}
sys.path.insert(0,str(ROOT/'tools'))

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def cleanup():
    removed=[]
    for path,digest in reversed(list(OWNED.items())):
        try:
            if not path.exists():continue
            if not path.resolve().is_relative_to(ROOT/'private') or path.is_symlink() or sha(path)!=digest:
                print('Temporary baseline changed; retained for inspection: '+str(path),file=sys.stderr);continue
            size=path.stat().st_size;path.unlink();removed.append(dict(path=str(path.relative_to(ROOT)),bytes=size,sha256=digest))
            try:path.parent.rmdir()
            except OSError:pass
        except OSError as error:print('Could not remove temporary translation baseline: '+str(error),file=sys.stderr)
    if OWNED:
        report=ROOT/'private/translation/baseline-last-session.json';report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(dict(temporary_build_inputs_removed=removed),indent=2)+'\n')
    OWNED.clear()
atexit.register(cleanup)

def prepare_image():
    import title
    from tester_setup import patcher_paths
    expected=title.CONFIG['translations']['english_v16'];image=ROOT/expected['file']
    if image.is_file():
        if image.stat().st_size!=expected['size'] or sha(image)!=expected['sha256']:raise ValueError('Translation build baseline differs')
        return image
    source=title.disc_image('japanese');title.verify_disc_image(source,'japanese')
    patch=ROOT.parent/'v1.6_2020.12.28/v1.6_2020.12.28.xdelta3';tool=ROOT/'private/tools/xdelta/xdelta3.exe'
    if sha(patch)!=expected['patch_sha256']:raise ValueError('Original upstream patch identity differs')
    if sha(tool)!='d81f59b2fe5e8589c0ee9782e231c805084f4d23dfade413903a4cad63b4e342':raise ValueError('Translation decoder identity differs')
    image.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='baseline-',suffix='.tmp',dir=image.parent);os.close(fd);temporary=Path(name);temporary.unlink()
    try:
        print('Preparing a temporary translation build baseline...',file=sys.stderr,flush=True)
        with patcher_paths(source,patch,temporary) as (src,delta,target):
            result=subprocess.run([str(tool),'-d','-s',src,delta,target],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        if temporary.stat().st_size!=expected['size'] or sha(temporary)!=expected['sha256']:raise ValueError('Reconstructed translation baseline hash differs')
        os.replace(temporary,image);OWNED[image]=expected['sha256']
    finally:temporary.unlink(missing_ok=True)
    return image

def prepare_archives():
    from translation_candidate import baseline_manifest
    from iso_edits import survey
    metadata=baseline_manifest();folder=ROOT/'private/translation/archives/english-v16'
    missing=[]
    for name in ('REGFILE.RZL','REGFILE.RZP'):
        target=folder/name;record=metadata['files']['PSP_GAME/USRDIR/UPDATA/'+name]
        if target.exists():
            if target.stat().st_size!=record['size'] or sha(target)!=record['sha256']:raise ValueError('Translation source archive differs: '+name)
        else:missing.append((target,record))
    if missing:
        image=prepare_image();folder.mkdir(parents=True,exist_ok=True)
        with image.open('rb') as source:
            files=survey.ISO(source).files()
            for target,record in missing:
                extent=files['PSP_GAME/USRDIR/UPDATA/'+target.name];source.seek(extent['lba']*2048);remaining=extent['size']
                fd,name=tempfile.mkstemp(prefix='archive-',suffix='.tmp',dir=folder);os.close(fd);temporary=Path(name)
                try:
                    with temporary.open('wb') as output:
                        while remaining:
                            block=source.read(min(remaining,1024*1024))
                            if not block:raise ValueError('Truncated translation baseline archive')
                            output.write(block);remaining-=len(block)
                    if sha(temporary)!=record['sha256']:raise ValueError('Extracted baseline archive hash differs')
                    os.replace(temporary,target);OWNED[target]=record['sha256']
                finally:temporary.unlink(missing_ok=True)
    return folder

def ensure_archives(path):
    path=Path(path)
    return prepare_archives() if path.resolve()==ROOT/'private/translation/archives/english-v16' else path

if __name__=='__main__':
    image=prepare_image();archives=prepare_archives()
    print(json.dumps(dict(status='PASS',image_sha256=sha(image),archive_sha256={p.name:sha(p) for p in archives.iterdir() if p.is_file()},temporary_files=len(OWNED)),indent=2))
