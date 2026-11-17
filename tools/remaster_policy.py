"""Keep the game's original dialogue illustrations out of HD replacement packs."""
import re
import sampler_pack


def original_portrait(name):
    # Reviewed 2D illustration families. NPC model atlases such as NPC01_00
    # are deliberately separate from NPC011 dialogue illustrations.
    return re.fullmatch(r'(?:NAMED|NPC)[0-9]{3}', name) is not None


def portrait_keys(catalog):
    keys = {key for row in catalog if original_portrait(row['name'])
            for key in row.get('candidate_keys', [])}
    return keys | {sampler_pack.tagged_key(key, wrap) for key in keys
                   for wrap in (0, 1, 256, 257)}


def portrait_group(group, keys):
    return (group['key'] in keys or group.get('canonical_key') in keys
            or any(original_portrait(ref['name'])
                   for ref in group.get('archive_references', [])))


def exclude_portraits(selected, catalog):
    keys = portrait_keys(catalog)
    retained, excluded = [], []
    for entry in selected:
        if any(original_portrait(row['name']) for row in entry[1]) or keys.intersection(entry[2]):
            excluded.extend(dict(name=row['name'], reason='original dialogue portrait retained')
                            for row in entry[1])
        else:
            retained.append(entry)
    return retained, excluded
