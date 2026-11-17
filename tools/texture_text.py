"""Reconstruct hash-bound text pixels and explicitly declared caption layouts."""
import hashlib
from pathlib import Path
from xet_codec import Xet


def digest(data):
    return hashlib.sha256(data).hexdigest()


def reconstruct(source, record, private_root):
    kind=int(record['resource_id'],16)>>16
    if kind not in (2,10):
        raise ValueError('Only XET textures or explicitly declared caption layouts may have text edits')
    if digest(source) != record['source_sha256']:
        raise ValueError('Texture source hash differs')
    if kind==10:
        from unm2_layout import replace_caption_fields
        if record.get('caption_layout') is not True:raise ValueError('Caption layout edits require an explicit caption manifest')
        return replace_caption_fields(source,*record['texture_size'],record['node_edits'])
    target = source
    for edit in record['edits']:
        path = Path(edit['rgba_path']).resolve()
        if not path.is_relative_to(private_root.resolve()):
            raise ValueError('Translated texture pixels must remain private')
        pixels = path.read_bytes()
        if digest(pixels) != edit['rgba_sha256']:
            raise ValueError('Translated texture pixels differ from reviewed hash')
        target = Xet.parse(target).replace_text_regions(edit['texture_index'], pixels, edit['regions'])
    return target


def verify(source, target, record, private_root):
    if digest(target) != record['target_sha256'] or reconstruct(source, record, private_root) != target:
        raise ValueError('Texture differs from its approved text regions')
