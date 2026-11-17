"""Verify exact pinned source contents in a player source drop without Git metadata."""
import hashlib,json
from pathlib import Path,PurePosixPath

def verify(root,kind):
    root=Path(root).resolve()
    pins=json.loads((root/'config/local-build-inputs.json').read_text())
    if pins.get('schema')!=1 or kind not in ('framework','decryptor'):raise ValueError('Unknown local build source')
    pin=pins[kind];manifest=(root/pin['manifest']).resolve()
    if not manifest.is_relative_to(root/'config'):raise ValueError('Source manifest escapes config')
    raw=manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Pinned source manifest hash differs')
    data=json.loads(raw)
    if data.get('schema')!=1 or data.get('commit')!=pin['commit'] or not data.get('files'):raise ValueError('Invalid source manifest identity')
    folder=root/('external/nakagawa-recomp' if kind=='framework' else 'private/tools/pspdecrypt')
    for name,digest in data['files'].items():
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:raise ValueError('Unsafe source path')
        path=(folder/name).resolve()
        if not path.is_relative_to(folder.resolve()):raise ValueError('Source path escapes checkout')
        if not path.is_file():raise FileNotFoundError('Missing pinned '+kind+' source: '+name)
        with path.open('rb') as stream:observed=hashlib.file_digest(stream,'sha256').hexdigest()
        if observed!=digest:raise ValueError('Pinned '+kind+' source changed: '+name)
    return data['commit']
