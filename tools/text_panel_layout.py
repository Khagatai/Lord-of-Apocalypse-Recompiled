"""Recorded panel checks shared by English generation and the private audit."""
import json
from pathlib import Path

from item_description_layout import width
from mes_codec import Bundle, Message
from mes_tokens import message_template


def measurements(message, table):
    lines, commands = message_template(message, table)
    uncertain = [f'{command[0]:04x}' for command in commands
                 if command[0] not in (0xfffa, 0xfff9, 0xfff4)]
    advances = []
    for line in lines:
        advance = width(line)
        for index, command in enumerate(commands):
            if command[0] == 0xfff4:
                advance += line.count(f'<cmd:{index}>') * 12
        advances.append(advance)
    return lines, advances, uncertain


def profile_for(profiles, resource_id, index, lines):
    for profile in profiles:
        if profile['resource_id'] != resource_id:
            continue
        if len(lines) < profile.get('minimum_rows', 1):
            continue
        if any(low <= index <= high for low, high in profile['ranges']):
            return profile
    return None


def validate(raw, table, resource_id, profiles=None):
    if profiles is None:
        path = Path(__file__).resolve().parents[1] / 'config/text-panel-layout.json'
        config = json.loads(path.read_text(encoding='utf-8'))
        if config['schema'] != 1:
            raise ValueError('Unsupported text-panel geometry schema')
        profiles = config['profiles']
    identity = f'{resource_id:08x}'
    profiles = [profile for profile in profiles if profile['resource_id'] == identity]
    if not profiles:
        return 0
    bundle = Bundle.parse(raw)
    checked = 0
    for index, block in enumerate(bundle.offsets):
        # Select by the pinned slot before decoding, so a new line count cannot
        # silently remove a description from validation.
        candidates = [profile for profile in profiles
                      if any(low <= index <= high for low, high in profile['ranges'])]
        if not candidates:
            continue
        message = Message.parse(bundle.blocks[block])
        lines, advances, uncertain = measurements(message, table)
        for profile in candidates:
            if uncertain:
                raise ValueError(f'{identity}:{index} needs measured runtime control widths')
            if max(advances) > profile['width'] or len(lines) > profile['rows']:
                raise ValueError(f"{identity}:{index} exceeds {profile['name']} "
                                 f"({max(advances)}/{profile['width']} pixels, "
                                 f"{len(lines)}/{profile['rows']} rows)")
            checked += 1
    return checked
