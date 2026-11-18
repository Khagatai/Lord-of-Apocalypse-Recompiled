"""Source-reviewed race Mark/Ward descriptions for the crafting sidebar."""
import hashlib
import json
from pathlib import Path
from mes_codec import Bundle, Message
from mes_tokens import message_template
from item_description_layout import wrap, replace, width, WIDTH

MAXIMUM_ROWS = 4
ORB_RANGES = ((63, 269), (382, 413), (425, 489), (556, 682))


def descriptions():
    result = {}
    races = (
        ('beast', 'beasts', "a beast's"),
        ('god', 'gods', 'divine'),
        ('daemon', 'daemons', "a daemon's"),
        ('seabeast', 'seabeasts', "a seabeast's"),
        ('undead', 'the undead', 'an undead'),
    )
    for offset, (race, plural, blessing) in enumerate(races):
        article = 'an' if race == 'undead' else 'a'
        result[83 + offset * 4] = (
            f'An orb with {article} {race}-slaying mark. '
            f'Boosts physical damage against {plural}.')
        result[85 + offset * 4] = (
            f'A holy {race}-slaying orb. '
            f'Greatly boosts physical damage against {plural}.')
        result[155 + offset * 4] = (
            f'An orb with {blessing} blessing. '
            f'Reduces physical damage from {plural}.')
        result[157 + offset * 4] = (
            f"A {race}-repelling guardian's orb. "
            f'Further reduces physical damage from {plural}.')
    return result


def fit_orb_descriptions(raw, table):
    bundle = Bundle.parse(raw)
    if len(bundle.offsets) != 683 or len(bundle.blocks) != 683:
        raise ValueError('Unmeasured crafting/orb message directory')
    replacements = {}
    plan = json.loads((Path(__file__).resolve().parents[1] /
                       'config/orb-panel-wording.json').read_text(encoding='utf-8'))
    if plan['schema'] != 1 or plan['resource_id'] != '00040da0' or (plan['width'], plan['rows']) != (WIDTH, MAXIMUM_ROWS):
        raise ValueError('Unsupported crafting/orb layout plan')
    race_descriptions = descriptions()
    for index, block in enumerate(bundle.offsets):
        if not any(low <= index <= high for low, high in ORB_RANGES):
            continue
        message = Message.parse(bundle.blocks[block])
        lines, commands = message_template(message, table)
        if commands:
            raise ValueError('Orb description contains unmeasured commands')
        if len(lines) <= 1:
            continue
        text = ' '.join(' '.join(lines).split())
        entry = plan['entries'].get(str(index))
        concise = index in race_descriptions or entry is not None
        if index in race_descriptions:
            proposed = race_descriptions[index]
        elif entry:
            if text != entry['text'] and hashlib.sha256(text.encode('utf-8')).hexdigest() != entry['source_text_sha256']:
                raise ValueError(f'Orb description {index} needs a source-reviewed layout')
            proposed = entry['text']
        else:
            if len(lines) <= MAXIMUM_ROWS and all(width(line) <= WIDTH for line in lines):
                continue
            proposed = text
        wrapped = wrap([proposed])
        if len(wrapped) > MAXIMUM_ROWS:
            raise ValueError('Orb description collides with the crafting stat row')
        if wrapped != lines:
            replacements[block] = replace(message, wrapped, table, preserve_words=not concise)
    return bundle.build(replacements)
