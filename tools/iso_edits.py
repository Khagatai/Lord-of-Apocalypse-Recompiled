"""Append files to a separate single-volume ISO9660 candidate copy."""
import hashlib
import importlib.util
from pathlib import Path
import shutil
import struct

_spec = importlib.util.spec_from_file_location("iso_survey", Path(__file__).with_name("survey-disc.py"))
survey = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(survey)


def extent_hash(stream, offset, size):
    stream.seek(offset)
    result = hashlib.sha256()
    while size:
        data = stream.read(min(size, 1024 * 1024))
        if not data:
            raise ValueError("Truncated extent")
        result.update(data)
        size -= len(data)
    return result.hexdigest()


def append_files(source, target, replacements):
    """Source and identical target copy are separately opened binary streams.

    Replacement values are seekable streams. Only primary descriptor sizes and
    selected directory records change in the copied original region. The old
    extents remain intact; raw-LBN references to replaced files need validation.
    """
    iso = survey.ISO(source)
    files = iso.files()
    target.seek(0, 2)
    if target.tell() != iso.size or iso.size % 2048:
        raise ValueError("Expected a sector-aligned ISO copy")
    primary = iso.read(16 * 2048, 2048)
    blocks_le = struct.unpack_from("<I", primary, 80)[0]
    blocks_be = struct.unpack_from(">I", primary, 84)[0]
    if blocks_le != blocks_be or blocks_le * 2048 != iso.size:
        raise ValueError("Volume length differs from source size")
    if iso.read(17 * 2048, 7) != b"\xffCD001\x01":
        raise ValueError("Only a primary descriptor followed by a terminator is supported")
    if not replacements or set(replacements) - set(files):
        raise ValueError("Missing or unknown replacement path")
    replacement_hashes = {}
    for name, stream in replacements.items():
        stream.seek(0, 2)
        size = stream.tell()
        if size > 0xffffffff:
            raise ValueError("Replacement exceeds ISO9660 file size")
        stream.seek(0)
        target.seek(0, 2)
        start = target.tell()
        shutil.copyfileobj(stream, target)
        target.write(b"\0" * (-size % 2048))
        if target.tell() // 2048 > 0xffffffff:
            raise ValueError("ISO exceeds volume size field")
        location = files[name]["record_offset"]
        target.seek(location + 2)
        target.write(struct.pack("<I", start // 2048) + struct.pack(">I", start // 2048))
        target.seek(location + 10)
        target.write(struct.pack("<I", size) + struct.pack(">I", size))
        replacement_hashes[name] = extent_hash(stream, 0, size)
    target.seek(0, 2)
    blocks = target.tell() // 2048
    target.seek(16 * 2048 + 80)
    target.write(struct.pack("<I", blocks) + struct.pack(">I", blocks))
    target.flush()
    rebuilt = survey.ISO(target)
    new_files = rebuilt.files()
    if set(new_files) != set(files):
        raise ValueError("ISO file list changed")
    for name, before in files.items():
        after = new_files[name]
        expected = replacement_hashes.get(name)
        if expected is None:
            if before != after:
                raise ValueError("Unchanged file placement differs")
            expected = extent_hash(source, before["lba"] * 2048, before["size"])
        if extent_hash(target, after["lba"] * 2048, after["size"]) != expected:
            raise ValueError("ISO content verification failed")
    return {"file_count": len(files), "all_file_payloads_verified": True,
            "replaced_files": sorted(replacements), "volume_blocks": blocks}
