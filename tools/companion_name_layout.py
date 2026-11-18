"""Keep translated roster names within the game's measured 18-byte fields.

The quest-start routine converts a roster name into two adjacent 9-word stack
buffers before copying 18 bytes into party records. Eight characters plus the
FFFF terminator fit; a ninth overwrites the next buffer or a saved pointer.
Dialogue and speaker-name resources retain their full names.
"""
from mes_codec import Bundle, Message

RESOURCE_ID = 0x400f9
NAME_COUNT = 120
BUFFER_BYTES = 18
MAX_CHARACTERS = BUFFER_BYTES // 2 - 1

# Explicit compact roster labels; never truncate arbitrary translated content.
COMPACT = {
    'Dolfstein': 'Dolfst.', 'Lauralone': 'Laura', 'Alexander': 'Alex',
    'Christine': 'Christin', 'Dieterich': 'Dietrich', 'Wilhelmine': 'Wilhelm.',
    'Anne-loze': 'Anne-L.', 'Beartrice': 'Beatrice', 'Elza=Marie': 'Elza-M.',
    'Augustine': 'Augustin', 'seat belt': 'Seatbelt', 'Friedrich': 'Friedr.',
    'Hieronimus': 'Hieron.', 'Christina': 'Christa', 'Charlotte': 'Charlott',
    'Christian': 'Christ.', 'Marie-Louise': 'Marie-L.', 'Frederica': 'Freder.',
    'Hanne=Loire': 'Hanne-L.', 'Margherita': 'Margher.', 'Benedictus': 'Benedict',
    'Cornealia': 'Cornelia', 'Henriette': 'Henriet.', 'Maria = Matren': 'Maria-M.',
    'Constantine': 'Constan.', 'Francesca': 'Frances.', 'Bonifatius': 'Boniface',
}


def fit_companion_names(raw, table):
    bundle = Bundle.parse(raw)
    if len(bundle.offsets) != 363:
        raise ValueError('Unmeasured companion-name directory')
    replacements = {}
    for index, block in enumerate(bundle.offsets[:NAME_COUNT]):
        message = Message.parse(bundle.blocks[block])
        if len(message.lines) != 1 or not message.editable(table):
            raise ValueError(f'Companion name {index} has unmeasured framing or controls')
        if len(message.lines[0]) * 2 <= BUFFER_BYTES:
            continue
        text = table.decode(message.lines[0][:-1])
        if text not in COMPACT:
            raise ValueError(f'Companion name {index} exceeds its 18-byte field; review required')
        fixed = message.replace_line(0, COMPACT[text], table)
        if len(fixed.lines[0]) * 2 > BUFFER_BYTES:
            raise ValueError('Compact companion name exceeds its field')
        if block in replacements and replacements[block] != fixed:
            raise ValueError('Conflicting companion-name aliases')
        replacements[block] = fixed
    return bundle.build(replacements)
