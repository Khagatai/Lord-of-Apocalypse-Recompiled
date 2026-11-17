"""Keep literal promotional input keys separate from their display notifications."""
RESOURCE = 0x400e3
DISPLAY_INDICES = frozenset(range(10, 20)) | frozenset(range(24, 28))


def protected(resource_id, message_index):
    identity = int(resource_id, 16) if isinstance(resource_id, str) else resource_id
    return identity == RESOURCE and message_index not in DISPLAY_INDICES
