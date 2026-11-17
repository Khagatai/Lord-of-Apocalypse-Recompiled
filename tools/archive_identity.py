"""Resolve archive identities only when all authored mip prefixes agree exactly."""


def longest_compatible(signatures):
    signatures=set(signatures)
    if not signatures or None in signatures:
        return None
    longest=max(signatures,key=len)
    return longest if all(longest[:len(sig)]==sig for sig in signatures) else None


def supplies(group, signature):
    """The renderer consumes the requested prefix of an available full chain."""
    if signature is None or (group['source_width'],group['source_height'])!=signature[0][:2]:
        return False
    if len(group['levels'])<len(signature):
        return False
    source=group.get('source_rgba_sha256')
    return source is None or source[:len(signature)]==[level[2] for level in signature]
