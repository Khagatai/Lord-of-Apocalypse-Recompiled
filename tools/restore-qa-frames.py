"""Verify or restore one approved historical frame archive; never overwrite data.

Example: python tools/restore-qa-frames.py hd-default-town-04 --restore
Without --restore this only verifies the ZIP and prints its frame count.
"""
import argparse,hashlib,json,os,stat,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'private'
def safe_target(name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or relative.as_posix()!=name or '..' in relative.parts or ':' in name or '\\' in name or not relative.parts or relative.parts[0]!='private':raise ValueError('Unsafe restore path.')
    path=ROOT.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(PRIVATE.resolve()):raise ValueError('Restore target escaped private/.')
    for item in (path,*path.parents):
        if item==ROOT:break
        if item.exists() and (item.is_symlink() or getattr(item.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse point in restore path.')
    return path
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('group');parser.add_argument('--restore',action='store_true');args=parser.parse_args()
    if args.group in ('.','..') or Path(args.group).name!=args.group or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.group):parser.error('Use one historical capture folder name.')
    raw=(PRIVATE/'storage-cleanup-proposal.json').read_bytes();plan=json.loads(raw);plan_hash=hashlib.sha256(raw).hexdigest()
    rows={r['path']:r for r in plan['lossless_archive_candidates'] if PurePosixPath(r['path']).parts[1]==args.group}
    if not rows:raise ValueError('Folder is not in the approved archive list.')
    archive_path=safe_target('private/historical-frame-archives/'+args.group+'.zip')
    with zipfile.ZipFile(archive_path) as archive:
        manifest=json.loads(archive.read('MANIFEST.json'))
        if manifest['proposal_sha256']!=plan_hash or set(archive.namelist())!=set(rows)|{'MANIFEST.json'}:raise ValueError('Archive differs from the approved proposal.')
        entries={r['path']:r for r in manifest['files']}
        if set(entries)!=set(rows):raise ValueError('Archive manifest differs.')
        for name,row in rows.items():
            entry=entries[name]
            if entry['bytes']!=row['bytes'] or entry['mtime_ns']!=row['mtime_ns'] or archive.getinfo(name).file_size!=row['bytes']:raise ValueError('Archive metadata differs.')
            data=archive.read(name)
            if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Archive checksum differs.')
            target=safe_target(name)
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Existing file would be overwritten: '+name)
        restored=0
        if args.restore:
            for name,row in rows.items():
                target=safe_target(name)
                if target.exists():continue
                target.parent.mkdir(parents=True,exist_ok=True)
                # Exclusive creation refuses a racing existing file. A failed
                # write is left visible; no unrelated file is ever overwritten.
                with target.open('xb') as stream:stream.write(archive.read(name))
                os.utime(target,ns=(row['mtime_ns'],row['mtime_ns']));restored+=1
    print(json.dumps(dict(scope='verified-lossless-QA-archive',group=args.group,verified_files=len(rows),restored_files=restored,archive_retained=True)))
if __name__=='__main__':main()
