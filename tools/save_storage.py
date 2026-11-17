"""Persistent preview storage and copy-only recovery with hashed backups."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
import re


def snapshot_saves(root, namespace, folder=None, keep=5):
    """Called under save_session before the child starts; retain distinct saves only."""
    if type(keep) is not int or not 1 <= keep <= 20:
        raise ValueError('Invalid save backup retention')
    folder = Path(folder) if folder is not None else memstick_path(root, namespace)
    memstick_path(root, namespace)  # Validate the namespace even with a fixture.
    source = folder/'PSP/SAVEDATA'
    for path in (folder, folder/'PSP', source):
        if path.is_symlink() or path.is_junction():
            raise ValueError('Save backup refuses redirected folders')
    hashes = tree_hashes(source)
    if not hashes:
        return {'status': 'no-saves', 'files': 0}
    signature = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    backups = root/'private/save-backups/automatic'/namespace
    backups.mkdir(parents=True, exist_ok=True)
    if backups.resolve() != (root.resolve()/'private/save-backups/automatic'/namespace):
        raise ValueError('Save backup directory is redirected')
    owned = []
    for path in backups.glob('save-*.zip'):
        if not re.fullmatch(r'save-[0-9a-f]{64}\.zip', path.name) or path.is_symlink():
            continue
        with zipfile.ZipFile(path) as archive:
            metadata = json.loads(archive.read('backup.json'))
            if metadata.get('owner') != 'loa-automatic-save-backup-v1' or metadata.get('namespace') != namespace:
                continue
            # Never rotate a previous snapshot without checking its complete payload.
            expected = metadata['files_sha256']
            if set(archive.namelist()) != {'backup.json', *expected}:
                raise ValueError('Automatic save backup has unexpected members')
            for name, digest in expected.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                    raise ValueError('Automatic save backup is corrupt: '+path.name)
            owned.append(path)
    destination = backups/('save-'+signature+'.zip')
    if destination.exists():
        if destination not in owned:
            raise ValueError('Save backup name is already occupied')
        return {'status': 'unchanged', 'files': len(hashes), 'backup': str(destination)}
    fd, temporary_name = tempfile.mkstemp(prefix='snapshot-', suffix='.tmp', dir=backups)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, digest in hashes.items():
                data = (source/name).read_bytes()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise RuntimeError('Save changed while preparing backup')
                archive.writestr(name, data)
            archive.writestr('backup.json', json.dumps({'owner': 'loa-automatic-save-backup-v1',
                'namespace': namespace, 'created_utc': datetime.now(timezone.utc).isoformat(),
                'files_sha256': hashes}, indent=2))
        if tree_hashes(source) != hashes:
            raise RuntimeError('Save changed while preparing backup')
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise RuntimeError('Save backup CRC verification failed')
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    # New snapshot is committed and verified before pruning only owned snapshots.
    for old in sorted(owned, key=lambda p:p.stat().st_mtime_ns, reverse=True)[keep-1:]:
        old.unlink()
    return {'status': 'created', 'files': len(hashes), 'backup': str(destination)}

def memstick_path(root, language):
    if language not in ("japanese", "english-v16", "english-text-test"):
        raise ValueError("Unknown save namespace")
    return root / "private/memstick" / language

def tree_hashes(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or path.is_junction():
            raise ValueError("Save recovery refuses symbolic links")
        if path.relative_to(folder) == Path(".preview.lock"):
            continue  # Process coordination metadata is not saved game data.
        if path.is_file():
            with path.open("rb") as stream:
                result[path.relative_to(folder).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result

def recover(root, source, language):
    source = source.resolve()
    if not source.is_relative_to(root / "private"):
        raise ValueError("Recover from a local private run folder")
    hashes = tree_hashes(source)
    if not hashes:
        raise ValueError("No save files found in source")
    destination = memstick_path(root, language)
    if destination.exists():
        raise ValueError("Persistent destination already exists; refusing to overwrite saves")
    backup_root = root / "private/save-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="recovery-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-", dir=backup_root))
    snapshot = backup / "memstick"
    shutil.copytree(source, snapshot, ignore=shutil.ignore_patterns(".preview.lock"))
    if tree_hashes(snapshot) != hashes or tree_hashes(source) != hashes:
        raise RuntimeError("Backup mismatch or source changed during backup")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(snapshot, destination)
    if tree_hashes(destination) != hashes or tree_hashes(source) != hashes:
        raise RuntimeError("Recovered files differ from source")
    report = {"source": str(source), "destination": str(destination), "backup": str(snapshot),
              "files_sha256": hashes, "source_unchanged": True, "copied_files_verified": True,
              "in_game_load_validated": False}
    (backup / "recovery.json").write_text(json.dumps(report, indent=2) + "\n")
    return report

@contextmanager
def save_session(folder):
    """Prevent concurrent preview writers sharing one Windows memstick."""
    import msvcrt
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".preview.lock").open("a+b") as lock:
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RuntimeError("Another preview is using this save folder; close it first") from error
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
