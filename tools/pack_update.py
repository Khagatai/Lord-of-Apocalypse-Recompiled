"""Validate and commit working-pack metadata without copying unchanged PNG assets."""
import hashlib
import json
import os
from pathlib import Path
import uuid

import texture_pack


def atomic_write(path, data):
    temporary=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_bytes(data)
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)


def commit(folder, report, ini, private_root=texture_pack.ROOT/'private'):
    folder=Path(folder).resolve();private_root=Path(private_root).resolve()
    if not folder.is_relative_to(private_root) or folder==private_root:
        raise ValueError('Working pack must remain inside private storage')
    manifest=folder/'sample.json';current_ini=folder/'textures.ini'
    if any(path.resolve().parent!=folder for path in (manifest,current_ini)):
        raise ValueError('Working metadata must remain inside the pack folder')
    old_manifest=manifest.read_bytes();old_ini=current_ini.read_bytes()
    # Preserve existing formatting/Windows line endings on a semantic no-op.
    # A published manifest's base hash describes its previous version.
    if report==json.loads(old_manifest) and ini==old_ini:
        return texture_pack.verify_mip_pack(folder,report,manifest)
    expected=report.get('base_manifest_sha256')
    if expected is not None and expected!=hashlib.sha256(old_manifest).hexdigest():
        raise ValueError('Working pack changed since the batch started')
    encoded=(json.dumps(report,indent=2)+'\n').encode('utf-8')
    token=uuid.uuid4().hex
    next_manifest=folder/('.sample-'+token+'.json')
    next_ini=folder/('.textures-'+token+'.ini')
    try:
        next_manifest.write_bytes(encoded)
        next_ini.write_bytes(ini)
        checked=texture_pack.verify_mip_pack(folder,report,next_manifest,ini_override=next_ini)
        if manifest.read_bytes()!=old_manifest or current_ini.read_bytes()!=old_ini:
            raise ValueError('Working pack changed during validation')
        # One compact metadata rollback, overwritten on the next successful update.
        # Unchanged PNG files are never copied or rewritten.
        rollback=(folder/'.metadata-rollback').resolve()
        if rollback.parent!=folder:
            raise ValueError('Metadata rollback must remain inside the pack folder')
        rollback.mkdir(exist_ok=True)
        atomic_write(rollback/'sample.json',old_manifest)
        atomic_write(rollback/'textures.ini',old_ini)
        os.replace(next_ini,current_ini)
        try:
            os.replace(next_manifest,manifest)
        except BaseException:
            atomic_write(current_ini,old_ini)
            atomic_write(manifest,old_manifest)
            raise
        return checked
    finally:
        next_ini.unlink(missing_ok=True)
        next_manifest.unlink(missing_ok=True)
