"""Apply the user-approved exact storage proposal; verify before each file removal.

No recursive deletion or game-asset conversion is performed. Historical raw
frames are archived byte-for-byte, with SHA-256 manifests, before removal.
"""
import hashlib,json,os,stat,sys,time,zipfile
from collections import defaultdict
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'private'
PROPOSAL=PRIVATE/'storage-cleanup-proposal.json'
ARCHIVES=PRIVATE/'historical-frame-archives'
REPORT=PRIVATE/'storage-cleanup-completed.json'
RECOVERY='private/release-backups/15ed54979675ee1ead541d7c43b6863ed48a171f5db0448aa85c07fd7d07463f.exe'
PREFIXES=('hd-','mip-','sampler-','neural-','campaign-','character-','environment-','title-ui-','menu-art-','background-','portrait-','quality-','text-sharpening-','texture-settings-','ui-original-','ui-player-')
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def atomic_json(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');os.replace(temporary,path)
def safe_path(relative):
    if not isinstance(relative,str):raise ValueError('Invalid relative path.')
    parts=PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or ':' in relative or '\\' in relative or relative!=parts.as_posix() or not parts.parts or parts.parts[0]!='private':raise ValueError('Unsafe proposal path: '+relative)
    path=ROOT.joinpath(*parts.parts)
    if not path.resolve().is_relative_to(PRIVATE.resolve()):raise ValueError('Proposal escaped private/: '+relative)
    for item in (path,*path.parents):
        if item==ROOT:break
        if item.exists():
            info=item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ValueError('Reparse point in proposal path: '+relative)
    return path
def validate_row(row,kind):
    path=safe_path(row['path']);parts=PurePosixPath(row['path']).parts
    if kind=='delete':
        allowed=(len(parts)==3 and path.name=='mip-gpu-check.exe' and parts[1].startswith(('mip-','sampler-')))
        allowed=allowed or row['path']=='private/mip-prototype-build-04/mip-prototype.exe'
        allowed=allowed or (len(parts)==3 and parts[1]=='release-backups' and path.suffix=='.exe' and len(path.stem)==64 and all(c in '0123456789abcdef' for c in path.stem))
        if not allowed or row['path']==RECOVERY:raise ValueError('Not an approved historical executable: '+row['path'])
    elif path.suffix.lower()!='.ppm' or len(parts)<3 or not parts[1].startswith(PREFIXES):raise ValueError('Not a historical QA frame: '+row['path'])
    if path.exists():
        info=path.stat()
        if not path.is_file() or info.st_size!=row['bytes'] or info.st_mtime_ns!=row['mtime_ns']:raise ValueError('Candidate changed since approval: '+row['path'])
    return path
def protect_snapshot():
    paths=[ROOT.parent/'Lord of Apocalypse (Japan).iso',ROOT.parent/'v1.6_2020.12.28',
           PRIVATE/'hd-remaster-pack',PRIVATE/'translation',PRIVATE/'memstick',PRIVATE/'save-backups',PRIVATE/'settings',
           PRIVATE/'modules',PRIVATE/'native-release',PRIVATE/'steam-test',PRIVATE/'original-portraits',PRIVATE/'player-clarity',
           PRIVATE/'remaster-coverage-08',PRIVATE/'tools/qwen-translator',PRIVATE/'tools/translation-engine',
           PRIVATE/'tools/steamworks-sdk',PRIVATE/'tools/python314',PRIVATE/'online-deps/build/datachannel/libdatachannel.dll',
           PRIVATE/'online-deps/build.json',PRIVATE/'oracle-prefix',ROOT/RECOVERY]
    snapshot={}
    for base in paths:
        if not base.exists():raise FileNotFoundError('Required protected path missing: '+str(base))
        files=[base] if base.is_file() else sorted(p for p in base.rglob('*') if p.is_file() and not p.is_symlink())
        print(f'Hashing protected {base.name}: {len(files)} files',flush=True)
        for index,path in enumerate(files):
            if getattr(path.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Reparse point in protected data.')
            key=os.path.relpath(path,ROOT).replace('\\','/')
            snapshot[key]=dict(bytes=path.stat().st_size,sha256=digest(path))
            if index and index%5000==0:print(f'  {base.name}: {index} protected files hashed',flush=True)
    return snapshot
def verify_archive(path,rows,plan_hash):
    with zipfile.ZipFile(path) as archive:
        manifest=json.loads(archive.read('MANIFEST.json'))
        if manifest['proposal_sha256']!=plan_hash:raise ValueError('Archive belongs to a different proposal.')
        expected={row['path']:row for row in rows};members={row['path']:row for row in manifest['files']}
        if set(archive.namelist())!=set(expected)|{'MANIFEST.json'} or set(members)!=set(expected):raise ValueError('Archive member list differs.')
        for name,row in expected.items():
            data=archive.read(name);entry=members[name]
            if len(data)!=row['bytes'] or entry['bytes']!=row['bytes'] or entry['mtime_ns']!=row['mtime_ns'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Archive verification failed: '+name)
        return manifest
def apply_group(group,rows,plan_hash):
    archive_path=ARCHIVES/(group+'.zip');temporary=ARCHIVES/(group+'.partial')
    if not archive_path.resolve().is_relative_to(ARCHIVES.resolve()):raise ValueError('Unsafe archive output.')
    if not archive_path.exists():
        if temporary.exists():raise ValueError('Partial archive exists; inspect before continuing: '+str(temporary))
        manifest=dict(proposal_sha256=plan_hash,files=[])
        with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
            for row in rows:
                source=validate_row(row,'archive')
                if not source.is_file():raise FileNotFoundError(source)
                data=source.read_bytes()
                if len(data)!=row['bytes']:raise ValueError('Frame changed during archiving.')
                manifest['files'].append(dict(row,sha256=hashlib.sha256(data).hexdigest()))
                archive.writestr(row['path'],data)
            archive.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
        verify_archive(temporary,rows,plan_hash)
        os.replace(temporary,archive_path)
    manifest=verify_archive(archive_path,rows,plan_hash)
    for row in manifest['files']:
        source=validate_row(row,'archive')
        if source.exists():
            if digest(source)!=row['sha256']:raise ValueError('Source no longer matches verified archive: '+row['path'])
            source.unlink()
    return dict(path=archive_path.relative_to(ROOT).as_posix(),files=len(rows),raw_bytes=sum(r['bytes'] for r in rows),
                archive_bytes=archive_path.stat().st_size,sha256=digest(archive_path),verified=True)
def main():
    if sys.argv[1:]!=['--apply-approved']:raise SystemExit('Use --apply-approved only for the already reviewed proposal.')
    raw=PROPOSAL.read_bytes();plan=json.loads(raw);plan_hash=hashlib.sha256(raw).hexdigest()
    if plan.get('scope')!='proposal-only-awaiting-user-review' or len(plan['delete_candidates'])!=18 or len(plan['lossless_archive_candidates'])!=875 or plan['delete_bytes']!=575300764:raise ValueError('Proposal differs from the approved scope.')
    if ARCHIVES.exists() and (ARCHIVES.is_symlink() or getattr(ARCHIVES.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Archive folder is a reparse point.')
    all_rows=plan['delete_candidates']+plan['lossless_archive_candidates']
    if len({r['path'] for r in all_rows})!=len(all_rows):raise ValueError('Repeated proposal target.')
    for kind,key in [('delete','delete_candidates'),('archive','lossless_archive_candidates')]:
        for row in plan[key]:validate_row(row,kind)
    ARCHIVES.mkdir(exist_ok=True)
    owner=ARCHIVES/'ownership.json'
    if owner.exists() and json.loads(owner.read_text()).get('proposal_sha256')!=plan_hash:raise ValueError('Existing archives have another owner.')
    atomic_json(owner,dict(proposal_sha256=plan_hash,scope='user-approved-byte-exact-historical-QA-frames'))
    baseline=PRIVATE/'storage-protected-before.json'
    if baseline.exists():
        saved=json.loads(baseline.read_text())
        if saved.get('proposal_sha256')!=plan_hash:raise ValueError('Protected snapshot belongs to another proposal.')
        before=saved['files']
    else:
        before=protect_snapshot();atomic_json(baseline,dict(proposal_sha256=plan_hash,files=before))
    result=dict(scope='user-approved-storage-cleanup',proposal_sha256=plan_hash,complete=False,archives=[],deleted=[],git_commit_created=False)
    if REPORT.exists():
        old=json.loads(REPORT.read_text())
        if old.get('proposal_sha256')!=plan_hash:raise ValueError('Cleanup report belongs to another proposal.')
        result=old
        if result.get('complete'):raise SystemExit('This proposal has already been applied; no files changed.')
    try:
        groups=defaultdict(list)
        for row in plan['lossless_archive_candidates']:groups[PurePosixPath(row['path']).parts[1]].append(row)
        done={r['path'] for r in result['archives']}
        for group,rows in sorted(groups.items()):
            target=(ARCHIVES/(group+'.zip')).relative_to(ROOT).as_posix()
            print(f'Archiving and verifying {group}: {len(rows)} frames',flush=True)
            record=apply_group(group,rows,plan_hash)
            if target not in done:result['archives'].append(record);done.add(target)
            atomic_json(REPORT,result)
        deleted={r['path'] for r in result['deleted']}
        for row in plan['delete_candidates']:
            if row['path'] in deleted:continue
            path=validate_row(row,'delete')
            if not path.is_file():raise FileNotFoundError('Unrecorded missing candidate: '+row['path'])
            fingerprint=digest(path)
            if path.parent.name=='release-backups' and fingerprint!=path.stem:raise ValueError('Backup filename/hash mismatch.')
            path.unlink();result['deleted'].append(dict(row,sha256=fingerprint));atomic_json(REPORT,result)
        after=protect_snapshot()
        if before!=after:
            atomic_json(PRIVATE/'storage-protected-mismatch.json',dict(changed=[p for p in set(before)|set(after) if before.get(p)!=after.get(p)]))
            raise ValueError('Protected data changed; inspect mismatch report.')
        result.update(complete=True,protected_files_unchanged=len(before),deleted_bytes=sum(r['bytes'] for r in result['deleted']),
                      raw_frame_bytes=sum(r['raw_bytes'] for r in result['archives']),archive_bytes=sum(r['archive_bytes'] for r in result['archives']))
        result['net_bytes_reclaimed']=result['deleted_bytes']+result['raw_frame_bytes']-result['archive_bytes']
        atomic_json(REPORT,result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('archives','deleted')},indent=2),flush=True)
    except BaseException as error:
        result['error']=str(error);atomic_json(REPORT,result);raise
if __name__=='__main__':main()
