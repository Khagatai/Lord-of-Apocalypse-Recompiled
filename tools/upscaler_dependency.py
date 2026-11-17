"""Fetch the pinned public texture tool from its publisher; never send game files.

Only the small required tool/model allowlist is extracted. Demo media and SDKs
are not installed. Inference itself is entirely local.
"""
import hashlib,json,os,shutil,sys,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def install(archive,folder,pins):
    archive,folder=Path(archive),Path(folder).resolve()
    if not folder.is_relative_to(ROOT/'private'):raise ValueError('Texture tool must remain private')
    if sha(archive)!=pins['archive_sha256']:raise ValueError('Public texture-tool archive hash differs')
    if folder.exists():raise FileExistsError('Existing texture-tool folder preserved')
    for name in pins['files']:
        rel=PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:raise ValueError('Unsafe texture-tool member')
    folder.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='realesrgan-local-',dir=folder.parent))
    try:
        with zipfile.ZipFile(archive) as bundle:
            names=[i.filename for i in bundle.infolist()]
            if len(names)!=len(set(names)):raise ValueError('Duplicate public tool archive member')
            for name,digest in pins['files'].items():
                info=bundle.getinfo(name)
                if info.file_size>200*1024**2 or ((info.external_attr>>16)&0xf000)==0xa000:raise ValueError('Invalid public tool member')
                path=stage/name;path.parent.mkdir(parents=True,exist_ok=True)
                with bundle.open(info) as source,path.open('xb') as target:shutil.copyfileobj(source,target,1024*1024)
                if sha(path)!=digest:raise ValueError('Public tool member hash differs: '+name)
        stage.rename(folder)
    finally:
        if stage.exists():
            # A fresh, exclusively owned extraction directory. Check every path
            # before deleting individual generated files, never caller folders.
            paths=list(stage.rglob('*'))
            if any(p.is_symlink() or not p.resolve().is_relative_to(stage) for p in paths):raise ValueError('Linked public-tool extraction scratch')
            for path in paths:
                if path.is_file():path.unlink()
            for path in sorted((p for p in paths if p.is_dir()),key=lambda p:len(p.parts),reverse=True):path.rmdir()
            stage.rmdir()


def ensure(folder=None,cache=None):
    import neural_texture
    folder=Path(folder or ROOT/'private/tools/realesrgan-20220424/package').resolve()
    if not folder.is_relative_to(ROOT/'private'):raise ValueError('Texture tool must remain private')
    if folder.is_dir():neural_texture.verify_tool(folder);return dict(status='VERIFIED',downloaded=False)
    pins=json.loads((ROOT/'config/remaster-upscaler.json').read_text())
    if not pins['archive_url'].startswith('https://github.com/xinntao/Real-ESRGAN/releases/download/'):
        raise ValueError('Unexpected public texture-tool publisher URL')
    cache=Path(cache or ROOT/'private/downloads/texture-tools.zip').resolve()
    if not cache.is_relative_to(ROOT/'private'):raise ValueError('Texture-tool download cache must remain private')
    cache.parent.mkdir(parents=True,exist_ok=True)
    downloaded=not cache.exists()
    if downloaded:
        temporary=cache.with_suffix('.part')
        if temporary.exists():raise FileExistsError('Interrupted public-tool download preserved: '+str(temporary))
        print('Preparing HD tools: downloading the pinned public tool from its publisher...',flush=True)
        try:
            request=urllib.request.Request(pins['archive_url'],headers={'User-Agent':'LordOfApocalypse-local-builder/1'})
            with urllib.request.urlopen(request,timeout=60) as source,temporary.open('xb') as target:
                if not source.geturl().startswith('https://'):raise ValueError('Public tool download redirected without HTTPS')
                size=0
                for data in iter(lambda:source.read(1024*1024),b''):
                    size+=len(data)
                    if size>300*1024**2:raise ValueError('Public texture-tool download exceeds its size bound')
                    target.write(data)
            if sha(temporary)!=pins['archive_sha256']:raise ValueError('Public texture-tool download hash differs')
            temporary.replace(cache)
        finally:temporary.unlink(missing_ok=True)
    archive_sha256=sha(cache);install(cache,folder,pins);neural_texture.verify_tool(folder)
    if downloaded:cache.unlink()
    return dict(status='VERIFIED',downloaded=downloaded,archive_sha256=archive_sha256,tool_files=len(pins['files']),archive_retained=not downloaded)


if __name__=='__main__':print(json.dumps(ensure(),indent=2))
