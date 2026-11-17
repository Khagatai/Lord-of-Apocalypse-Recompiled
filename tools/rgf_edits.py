"""Append rebuilt RGF groups, preserving existing archive bytes and other variants."""
import hashlib
import struct
import zlib
from collections import Counter
from rgf_archive import parse_index, read_group


def digest(data):
    return hashlib.sha256(data).hexdigest()


def append_edits(index, source, target, replacements):
    """Target must be an identical, separately opened archive copy at EOF.

    Global keys are (resource ID, original payload SHA-256). Scoped keys are
    (group index, occurrence within that group for this ID, ID, source SHA-256).
    Scoped keys preserve distinct translated copies of originally identical text.
    """
    source.seek(0, 2)
    original_size = source.tell()
    target.seek(0, 2)
    if target.tell() != original_size or original_size % 2048:
        raise ValueError("Expected a sector-aligned archive copy")
    if not replacements:
        raise ValueError("No replacements supplied")
    if any(not isinstance(key,tuple) or len(key) not in (2,4) for key in replacements):raise ValueError('Invalid replacement key')
    groups = parse_index(index, original_size)
    output = bytearray(index)
    hits = {key: 0 for key in replacements}
    records = struct.unpack_from(f"<{len(groups)}I", index, 24)
    changed = []
    for number, group in enumerate(groups):
        plain = read_group(source, group)
        cursor, parts, entries, modified = 0, [], [], False
        occurrences=Counter()
        for size, identity in group.entries:
            raw = plain[cursor:cursor + size]
            cursor += size
            key = identity, digest(raw)
            scoped=number,occurrences[identity],identity,key[1];occurrences[identity]+=1
            if scoped in replacements:
                if key in replacements:raise ValueError('Ambiguous global and scoped replacement')
                key=scoped
            if key in replacements:
                replacement = replacements[key]
                if replacement == raw:
                    raise ValueError("Replacement is identical to source")
                hits[key] += 1
                modified = True
            else:
                replacement = raw
            parts.append(replacement)
            entries.append((len(replacement), identity))
        if not modified:
            continue
        raw = b"".join(parts)
        if len(raw) > 128 * 1024 * 1024:
            raise ValueError("Rebuilt group exceeds decoder bound")
        packed = zlib.compress(raw, level=9)
        packed += b"\0" * (-len(packed) % 2048)
        start = target.tell()
        if start + len(packed) > 0xffffffff:
            raise ValueError("Archive offset exceeds 32-bit format")
        target.write(packed)
        record = records[number]
        struct.pack_into("<3I", output, record + 4, start, len(packed), len(raw))
        for entry, (size, identity) in enumerate(entries):
            struct.pack_into("<II", output, record + 16 + entry * 8, size, identity)
        changed.append(number)
    if not all(hits.values()):
        raise ValueError("Requested resource variant was not found")
    target.flush()
    rebuilt = parse_index(output, target.tell())
    # Independent decompression checks every descriptor, including aliases and
    # same-ID variants that must not be changed merely because their ID matches.
    for number,(before, after) in enumerate(zip(groups, rebuilt)):
        old, new = read_group(source, before), read_group(target, after)
        old_cursor = new_cursor = 0
        occurrences=Counter()
        if len(before.entries) != len(after.entries):
            raise ValueError("Descriptor count changed")
        for (old_size, identity), (new_size, new_identity) in zip(before.entries, after.entries):
            raw = old[old_cursor:old_cursor + old_size]
            digest_raw=digest(raw);scoped=number,occurrences[identity],identity,digest_raw;occurrences[identity]+=1
            expected = replacements.get(scoped,replacements.get((identity,digest_raw),raw))
            actual = new[new_cursor:new_cursor + new_size]
            if identity != new_identity or actual != expected:
                raise ValueError("Resource verification failed")
            old_cursor += old_size
            new_cursor += new_size
    return bytes(output), {"changed_groups": changed,
                           "replacement_instances": sum(hits.values()),
                           "all_resource_payloads_verified": True}
