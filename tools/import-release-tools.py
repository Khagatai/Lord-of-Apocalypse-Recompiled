"""Import hash-pinned public build dependencies/recipes into a fresh source clone.

Never imports prepared game outputs, saves, settings, generated C or modules.
Existing differing files are preserved. Use the matching release payload, not a
private tester ZIP. The original ISO is selected by the later local build stage.
"""
import argparse,hashlib,json,os,sys,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
PREFIX='LordOfApocalypse-Recomp/'
ALLOWED=('private/tools/python314/','private/tools/pspdecrypt/','private/tools/realesrgan-20220424/package/',
    'private/toolchain/prerequisites/msys64/ucrt64/','private/steam-test/','private/online-deps/',
    'private/distribution/recipes/','licenses/')


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def allowed(name):
    if Path(name).suffix.lower() in ('.iso','.cso','.chd','.elf','.prx','.vcdiff','.trace','.ppm','.rgba') or Path(name).name=='lordofapocalypse_image.bin':return False
    return name in ('config/player-build.json','private/distribution/release.json') or name.startswith(ALLOWED)


def safe_path(root,name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:raise ValueError('Unsafe dependency path')
    path=(root/name).resolve()
    if not path.is_relative_to(root):raise ValueError('Dependency path escapes source clone')
    return path


def import_payload(archive,metadata,root=ROOT,check_only=False):
    root=Path(root).resolve();archive=Path(archive)
    if archive.stat().st_size!=metadata['size'] or sha(archive)!=metadata['sha256']:
        raise ValueError('Release dependency archive hash/size differs; no files imported')
    with zipfile.ZipFile(archive) as bundle:
        manifest=json.loads(bundle.read(PREFIX+'PACKAGE-MANIFEST.json'))
        if manifest.get('schema')!=2 or manifest.get('game_payloads_included') is not False or manifest.get('builds_native_game_locally') is not True:
            raise ValueError('Requires an ISO-only source/tools payload, not a prepared tester package')
        selected=[];seen=set()
        for row in manifest['files']:
            name=row['path'];path=safe_path(root,name)
            if name.casefold() in seen:raise ValueError('Duplicate dependency manifest path')
            seen.add(name.casefold())
            if not allowed(name):continue
            info=bundle.getinfo(PREFIX+name)
            if info.file_size!=row['size'] or ((info.external_attr>>16)&0xf000)==0xa000:raise ValueError('Invalid dependency ZIP member')
            if path.exists() and (not path.is_file() or path.stat().st_size!=row['size'] or sha(path)!=row['sha256']):
                raise ValueError('Existing dependency differs; use a fresh source clone. Preserved: '+name)
            selected.append((row,path))
        if not selected:raise ValueError('No public source-build dependencies in archive')
        imported=0
        if not check_only:
            for row,path in selected:
                if path.exists():continue
                path.parent.mkdir(parents=True,exist_ok=True)
                fd,name=tempfile.mkstemp(prefix='loa-dependency-',suffix='.tmp',dir=path.parent);temporary=Path(name)
                try:
                    digest=hashlib.sha256();length=0
                    with os.fdopen(fd,'wb') as target,bundle.open(PREFIX+row['path']) as source:
                        for data in iter(lambda:source.read(1024*1024),b''):
                            length+=len(data)
                            if length>row['size']:raise ValueError('Dependency expands past expected size')
                            target.write(data);digest.update(data)
                    if length!=row['size'] or digest.hexdigest()!=row['sha256']:raise ValueError('Dependency content hash differs')
                    os.link(temporary,path);imported+=1
                finally:temporary.unlink(missing_ok=True)
    return dict(status='DEPENDENCIES_VERIFIED',selected_files=len(selected),imported_files=imported,
        check_only=check_only,game_outputs_imported=False,ready_to_play=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path);p.add_argument('--check-only',action='store_true');a=p.parse_args()
    metadata_path=ROOT/'config/release-download.json'
    if not metadata_path.is_file():raise FileNotFoundError('Pinned release-download.json is not present; use the matching published installer payload')
    metadata=json.loads(metadata_path.read_text())
    if metadata.get('schema')!=1 or not metadata['url'].startswith('https://github.com/Khagatai/Lord-of-Apocalypse-Recompiled/releases/download/'):
        raise ValueError('Unexpected source dependency download location')
    archive=a.archive
    if archive is None:
        cache=ROOT/'private/downloads';cache.mkdir(parents=True,exist_ok=True);archive=safe_path(cache,metadata['name'])
        if not archive.exists():
            temporary=archive.with_suffix('.part')
            if temporary.exists():raise FileExistsError('Interrupted dependency download preserved: '+str(temporary))
            try:
                request=urllib.request.Request(metadata['url'],headers={'User-Agent':'LordOfApocalypse-source-builder/1'})
                with urllib.request.urlopen(request,timeout=60) as source,temporary.open('xb') as target:
                    count=0
                    for data in iter(lambda:source.read(1024*1024),b''):
                        count+=len(data)
                        if count>metadata['size']:raise ValueError('Dependency download larger than pinned size')
                        target.write(data)
                if count!=metadata['size'] or sha(temporary)!=metadata['sha256']:raise ValueError('Dependency download verification failed')
                temporary.replace(archive)
            finally:temporary.unlink(missing_ok=True)
    print(json.dumps(import_payload(archive,metadata,check_only=a.check_only),indent=2))


if __name__=='__main__':main()
