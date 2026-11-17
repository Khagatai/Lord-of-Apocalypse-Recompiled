"""Strict, read-only RGF1 index and zlib-group reader. No game bytes belong in source."""
from dataclasses import dataclass
import struct
import zlib

@dataclass(frozen=True)
class Group:
    offset: int
    packed: int
    plain: int
    entries: tuple

def parse_index(data, archive_size):
    if len(data) < 24:
        raise ValueError("Truncated RGF1 header")
    magic, version_count, unique_count, table, records, end = struct.unpack_from("<6I", data)
    count, version = version_count >> 16, version_count & 65535
    if magic != 0x31464752 or version != 1 or table != 24:
        raise ValueError("Unsupported RGF1 header")
    if not count or records != table + count * 4 or not records <= end <= len(data):
        raise ValueError("Invalid index bounds")
    offsets = struct.unpack_from(f"<{count}I", data, table)
    groups, ids, previous_end = [], set(), records
    for index, offset in enumerate(offsets):
        if offset != previous_end or offset + 16 > end:
            raise ValueError("Invalid group record boundary")
        n, start, packed, plain = struct.unpack_from("<4I", data, offset)
        previous_end = offset + 16 + n * 8
        if previous_end > end or start + packed > archive_size or plain > 128 * 1024 * 1024:
            raise ValueError("Group span out of bounds")
        entries = tuple(struct.unpack_from("<II", data, offset + 16 + i * 8) for i in range(n))
        if sum(size for size, _ in entries) != plain:
            raise ValueError("Resource sizes differ from decompressed group length")
        ids.update(identity for _, identity in entries)
        groups.append(Group(start, packed, plain, entries))
    # Retail index declares an aligned end with four zero bytes after its last record.
    if not 0 <= end - previous_end < 8 or any(data[previous_end:end]) or len(ids) != unique_count:
        raise ValueError("Index end or distinct resource count differs")
    return groups

def read_group(stream, group):
    stream.seek(group.offset)
    packed = stream.read(group.packed)
    if len(packed) != group.packed:
        raise ValueError("Truncated packed group")
    if not group.plain and not group.packed:
        return b""
    decoder = zlib.decompressobj()
    try:
        plain = decoder.decompress(packed, group.plain + 1)
    except zlib.error as error:
        raise ValueError("Invalid zlib group") from error
    if not decoder.eof or decoder.unconsumed_tail or len(plain) != group.plain:
        raise ValueError("Incomplete zlib stream or decompressed size differs")
    # unused_data is the group's preserved allocation padding, never another resource.
    return plain

def resources(stream, groups):
    for group_index, group in enumerate(groups):
        plain = read_group(stream, group)
        offset = 0
        for size, identity in group.entries:
            yield group_index, identity, plain[offset:offset + size]
            offset += size
