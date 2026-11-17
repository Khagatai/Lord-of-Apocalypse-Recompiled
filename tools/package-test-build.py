"""Create one local tester ZIP from an explicit runtime/source allowlist.

Never includes ISOs, user state, SDK headers, caches or compiler/build trees.
"""
import argparse,ast,hashlib,json,os,re,struct,subprocess,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SDK=ROOT/'private/toolchain/prerequisites/msys64/ucrt64/bin'
WORK=ROOT/'private/distribution-test'
TOP='LordOfApocalypse-Recomp/'
DYNAMIC_DLLS=('SDL3_ttf.dll',)
MENU_LICENSES=('SDL3_ttf','freetype','harfbuzz','graphite2','glib2','pcre2',
               'gettext-runtime','libiconv','gcc','libgcc','brotli','bzip2','libpng','zlib')

def player_tools():
    """Include imported helpers, subprocess entry points and integrity inputs."""
    # iso_edits loads survey-disc.py by filename, so normal AST import traversal
    # cannot discover this startup dependency.
    queue=['launch-preview','tester-start','tester_setup','launcher_settings','online_agent','coop_lobby','survey-disc']
    seen=set()
    while queue:
        name=queue.pop();path=ROOT/'tools'/(name+'.py')
        if name in seen or not path.is_file():continue
        seen.add(name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names=([a.name.split('.')[0] for a in node.names] if isinstance(node,ast.Import)
                   else [node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else [])
            queue.extend(n for n in names if (ROOT/'tools'/(n+'.py')).is_file())
    return {'tools/'+n+'.py' for n in seen}|{'tools/import_trace_codegen.py','tools/frame_rate_codegen.py','tools/steam_bridge.cpp','tools/steam_flat.h'}

def player_member(name,helpers):
    """Runtime files and licence notices, excluding developer-facing material."""
    if name in ('AGENTS.md','README.md','INSTALL-PARTS.txt') or name.startswith(('docs/','tests/')):return False
    if name.startswith('tools/'):return name in helpers
    prefix='external/nakagawa-recomp/'
    if name.startswith(prefix):
        relative=name[len(prefix):]
        return relative.startswith(('assets/fonts/ui/','assets/vfpu/','THIRD_PARTY_LICENSES/')) or relative in ('LICENSE','NOTICE.md','CREDITS.md')
    return True

def source_member(name):
    """Keep accompanying build/licence source, without issue/history documents."""
    if name.startswith(('private/','docs/','tests/')) or name=='AGENTS.md':return False
    if name.startswith('external/'):
        relative=name.split('/',2)[2]
        if relative.startswith(('docs/','tests/','.github/','assets/')):return False
    if name.lower().endswith('.md'):
        return any(word in Path(name).name.lower() for word in ('license','notice','credit','provenance','relink','copying'))
    return name!='LordOfApocalypse.exe'

def player_inventory(items):
    bundle=WORK/'player-licence-sources.zip';bundle.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(items.items()):
            if source_member(name):archive.write(path,name)
    helpers=player_tools()
    selected={n:p for n,p in items.items() if player_member(n,helpers)}
    selected['licenses/SOURCES.zip']=bundle
    return selected

def dll_closure(seeds,sdk,system):
    """Include explicit SDL_LoadObject dependencies as well as PE imports."""
    names={p.name.lower():p for p in sdk.iterdir() if p.is_file()}
    queue=list(seeds);seen=set()
    while queue:
        path=queue.pop()
        if path in seen:continue
        if not path.is_file():raise FileNotFoundError('Missing native dependency: '+str(path))
        seen.add(path)
        for name in pe_imports(path):
            if name.lower().startswith(('api-ms-','ext-ms-')):continue
            own=path.parent/name
            found=own if own.is_file() else names.get(name.lower())
            if found is not None:queue.append(found)
            elif not(system/name).is_file():raise FileNotFoundError('Missing native dependency: '+name)
    return seen
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def pe_imports(path):
    d=Path(path).read_bytes()
    if d[:2]!=b'MZ':raise ValueError('Not a Windows binary: '+str(path))
    pe=struct.unpack_from('<I',d,60)[0];count=struct.unpack_from('<H',d,pe+6)[0];opt=pe+24;size=struct.unpack_from('<H',d,pe+20)[0]
    magic=struct.unpack_from('<H',d,opt)[0];directory=opt+(112 if magic==0x20b else 96)
    rva=struct.unpack_from('<I',d,directory+8)[0];sections=[]
    for i in range(count):
        p=opt+size+40*i;vs,va,rs,raw=struct.unpack_from('<4I',d,p+8);sections.append((va,max(vs,rs),raw))
    def offset(r):
        for va,n,raw in sections:
            if va<=r<va+n:return raw+r-va
        raise ValueError('Invalid PE import RVA')
    names=[]
    if not rva:return names
    p=offset(rva)
    while any(d[p:p+20]):
        n=offset(struct.unpack_from('<I',d,p+12)[0]);end=d.index(0,n);names.append(d[n:end].decode('ascii'));p+=20
    return names
def allowed(name):
    parts=Path(name).parts;lower=name.lower()
    return not (Path(name).suffix.lower() in ('.iso','.cso','.chd','.pyc','.o','.d','.log') or any(p in ('.git','__pycache__') for p in parts) or lower.startswith(('private/settings/','private/memstick/','private/preview-','private/save-backups/')))

def verify_patch_proof(proof,name,source_sha,target,patch):
    """Refuse stale deltas even if the current target was rebuilt successfully."""
    rows=[r for r in proof.get('patches',[]) if r.get('name')==name]
    if proof.get('status')!='PASS' or len(rows)!=1:
        raise ValueError('Missing decoded-image verification for '+name)
    row=rows[0]
    expected=dict(source_sha256=source_sha,target_sha256=target['sha256'],
                  target_size=target['size'],patch_sha256=sha(patch),
                  patch_size=patch.stat().st_size,decoded_payload_hash_verified=True,
                  source_unchanged=True)
    if any(row.get(k)!=v for k,v in expected.items()):
        raise ValueError('Stale or unverified image patch: '+name)
    return expected['patch_sha256']
def inventory():
    items={}
    def add(path,name=None):
        path=Path(path);name=name or path.relative_to(ROOT).as_posix()
        if not path.is_file() or path.is_symlink() or not allowed(name):raise ValueError('Unapproved/missing package file: '+name)
        if name in items and items[name]!=path:raise ValueError('Duplicate package member: '+name)
        items[name]=path
    def tree(folder,predicate=lambda p:True):
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and predicate(p):add(p)
    for n in ('LICENSE','CREDITS.md','README.md','LordOfApocalypse.exe'):add(ROOT/n)
    for folder in ('tools','config','docs','tests'):
        tree(folder,lambda p:p.suffix in ('.py','.c','.cpp','.cs','.h','.mk','.ps1','.json','.toml','.manifest','.md','.txt'))
    # The pinned framework source and public assets keep provenance/build sources
    # beside the binary. Git database, local outputs and SDKs are never copied.
    framework=ROOT/'external/nakagawa-recomp'
    files=subprocess.check_output(['git','-c','safe.directory='+framework.as_posix(),'-C',str(framework),'ls-files','-z'],text=True).split('\0')
    for name in files:
        if name and allowed(name) and (framework/name).is_file():add(framework/name)
    release=ROOT/'private/native-release/lordofapocalypse'
    for n in ('lordofapocalypse.exe','lordofapocalypse_image.bin','host-ui-build.json','SDL3.dll','libiconv-2.dll','THIRD_PARTY_NOTICES.txt','RELINK.md','SOURCE.txt'):add(release/n)
    tree('private/native-release/lordofapocalypse/font')
    tree('private/native-release/lordofapocalypse/THIRD_PARTY_NOTICES')
    for n in ('EBOOT.elf','LIBFONT.elf'):add(ROOT/'private/modules'/n)
    add(ROOT/'private/oracle-prefix/entry-prefix.trace')
    tree('private/tools/python314',lambda p:p.parent==ROOT/'private/tools/python314' and p.suffix in ('.exe','.dll','.pyd','.zip','._pth','.txt'))
    for n in ('loa_steam_bridge.dll','steam_api64.dll','bridge.json'):add(ROOT/'private/steam-test'/n)
    add(ROOT/'private/online-deps/build/datachannel/libdatachannel.dll');add(ROOT/'private/online-deps/build.json')
    add(ROOT/'private/translation/text-pass-16-image/result.json')
    for n in ('captions.bin','result.json'):add(ROOT/'private/translation/movie-captions'/n)
    add(ROOT/'private/tools/xdelta/xdelta3.exe')
    add(framework/'THIRD_PARTY_LICENSES/GPL-2.0.txt','private/tools/xdelta/COPYING.txt')
    tree('private/hd-remaster-pack',lambda p:p.suffix.lower() in ('.png','.ini','.json'))
    # Resolve non-system native dependencies without packing an entire compiler.
    seeds=[release/'lordofapocalypse.exe',release/'SDL3.dll',release/'libiconv-2.dll',ROOT/'private/steam-test/loa_steam_bridge.dll',ROOT/'private/steam-test/steam_api64.dll',ROOT/'private/online-deps/build/datachannel/libdatachannel.dll',ROOT/'private/tools/xdelta/xdelta3.exe',SDK/'vulkan-1.dll']
    seeds.extend(SDK/name for name in DYNAMIC_DLLS)
    add(SDK/'SDL3.dll');add(SDK/'vulkan-1.dll')
    system=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'
    for path in dll_closure(seeds,SDK,system):add(path)
    for name in MENU_LICENSES:
        folder=SDK.parent/'share/licenses'/name
        if not folder.is_dir():raise FileNotFoundError('Missing menu dependency licence: '+name)
        tree(folder)
    return player_inventory(items)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();output=a.output.resolve()
    if output.exists():raise FileExistsError('Refusing to replace an existing tester ZIP')
    items=inventory();patcher=ROOT/'private/tools/xdelta/xdelta3.exe'
    proof=json.loads((WORK/'patch-verification.json').read_text(encoding='utf-8'))
    source_sha='3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93'
    images=[]
    for label,name,target in [('WIP English (work in progress)','english-wip','private/translation/text-pass-16-image/LordOfApocalypse-English-WIP.iso')]:
        patch=WORK/'patches'/(name+'.vcdiff')
        if not patch.is_file():raise FileNotFoundError('Generate and finish both image patches first')
        member='private/distribution/patches/'+patch.name;items[member]=patch
        original=ROOT/target
        image=dict(label=label,path=target,size=original.stat().st_size,sha256=sha(original),patch=member)
        image['patch_sha256']=verify_patch_proof(proof,name,source_sha,image,patch)
        images.append(image);source_sha=image['sha256']
    install=dict(schema=1,original=dict(size=1068498944,sha256='3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93'),images=images,patcher=dict(path='private/tools/xdelta/xdelta3.exe',sha256=sha(patcher)))
    manifest=WORK/'release.json';manifest.write_text(json.dumps(install,indent=2)+'\n');items['private/distribution/release.json']=manifest
    generated={
      'READ-ME-FIRST.txt':(ROOT/'config/PLAYER_README.txt').read_text(encoding='utf-8'),
      'private/tools/xdelta/SOURCE.txt':'xdelta 3.0.11 by Joshua MacDonald. GPL-2.0-or-later; see COPYING.txt. Source: https://github.com/jmacd/xdelta/tree/v3.0.11\n',
    }
    output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_suffix('.zip.part')
    if temporary.exists():raise FileExistsError('Unfinished ZIP already exists: '+str(temporary))
    started=time.monotonic();records=[]
    try:
        with zipfile.ZipFile(temporary,'w',allowZip64=True) as archive:
            for i,(name,path) in enumerate(sorted(items.items())):
                if not allowed(name):raise ValueError('Excluded state/image in package: '+name)
                # PNGs are already compressed. Store them directly, avoiding a
                # second full expanded HD pack as packaging scratch.
                compression=zipfile.ZIP_STORED if path.suffix.lower() in ('.png','.vcdiff','.zip') else zipfile.ZIP_DEFLATED
                info=zipfile.ZipInfo(TOP+name);info.compress_type=compression;info.external_attr=0o100644<<16;info.date_time=(2026,11,16,0,0,0)
                digest=hashlib.sha256();size=0
                with path.open('rb') as src,archive.open(info,'w',force_zip64=True) as dst:
                    for block in iter(lambda:src.read(1024*1024),b''):dst.write(block);digest.update(block);size+=len(block)
                records.append(dict(path=name,size=size,sha256=digest.hexdigest()))
                if (i+1)%2048==0:print(json.dumps(dict(packaged_files=i+1,total=len(items),seconds=round(time.monotonic()-started,1))),flush=True)
            for name,text in generated.items():archive.writestr(TOP+name,text,compress_type=zipfile.ZIP_DEFLATED)
            archive.writestr(TOP+'PACKAGE-MANIFEST.json',json.dumps(dict(schema=1,version='0.9.0-beta.1',framework_commit='8704fba98007fff6d6f930365f2b2142af1bfbba',files=records,excluded=['ISOs','saves','saved graphics/network preferences','logs','SDK headers','compiler objects'],gameplay_acceptance=False,public_distribution_review_complete=False),indent=2),compress_type=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(temporary) as archive:
            bad=archive.testzip()
            if bad:raise ValueError('ZIP CRC check failed: '+bad)
            assert not any(Path(n).suffix.lower()=='.iso' or '/private/settings/' in n or '/private/memstick/' in n for n in archive.namelist())
        os.replace(temporary,output)
    except BaseException:
        # Keep an interrupted owned .part for inspection; never remove unrelated files.
        raise
    report=dict(zip=str(output),size=output.stat().st_size,sha256=sha(output),files=len(records)+len(generated)+1,crc_verified=True,iso_files=0,saved_preferences=0,saves=0,framework_commit='8704fba98007fff6d6f930365f2b2142af1bfbba',seconds=round(time.monotonic()-started,1))
    (WORK/'package-result.json').write_text(json.dumps(report,indent=2)+'\n');output.with_suffix('.zip.sha256.txt').write_text(report['sha256']+'  '+output.name+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
