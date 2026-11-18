"""Word wrapping for the character creator's shared title-description panel."""
import hashlib
import json
from pathlib import Path
from mes_codec import Bundle, Message
from mes_tokens import TAG, message_template
from message_recipe import reflow
from item_description_layout import width

# Keep a margin inside the panel, using the original six-pixel ASCII advance.
WIDTH = 174
LINES = 4

# Match the full existing text so later translations are never overwritten.
# These four concise versions were checked against the original Japanese.
CONCISE = {
    514: (
        "Chapter 04 cleared. The king confronts the agent Chaos, remembering the king's memories brought by the twin serpents.",
        "Chapter 04 cleared. The king faces Chaos's envoy. The twin serpents bring back royal memories.",
    ),
    518: (
        "Chapter 08 cleared. Connection to the past, return to the beginning. Death once more visits the dragon.",
        "Chapter 08 cleared. Return to the past, back to the beginning. Death visits the dragon again.",
    ),
    964: (
        "Gradually, exclusively assigned to... the days when the editor's outrageous behavior (!?) are gracefully handled begin.",
        "Now the editor's personal aide, your days of deftly handling unreasonable demands begin.",
    ),
    981: (
        "The one who landed a decisive blow on a vulnerable point, unable to reach the immortality power derived from dragon's blood.",
        "Struck a vital point beyond the protection of immortality gained from the evil dragon's blood.",
    ),
}


def wrap(lines):
    result = []
    current = ''
    for word in ' '.join(lines).split():
        if width(word) > WIDTH:
            raise ValueError('Title description contains an overlong word')
        candidate = ' '.join(filter(None, (current, word)))
        if width(candidate) > WIDTH:
            result.append(current)
            current = word
        else:
            current = candidate
    if current:
        result.append(current)
    result = result or ['']
    if len(result) > LINES:
        raise ValueError('Title description needs concise wording to fit the panel')
    return result


def reflow_descriptions(raw, table):
    """The measured bundle holds 500 names followed by 500 descriptions."""
    bundle = Bundle.parse(raw)
    if len(bundle.offsets) != 1000 or len(bundle.blocks) != 1000:
        raise ValueError('Unmeasured title-description directory')
    replacements = {}
    for index, block in enumerate(bundle.offsets[500:], start=500):
        message = Message.parse(bundle.blocks[block])
        lines, commands = message_template(message, table)
        # This panel has plain descriptions. Unexpected commands need review.
        if commands or any(TAG.search(line) for line in lines):
            raise ValueError('Unmeasured title-description commands')
        if len(lines) <= LINES and all(width(line) <= WIDTH for line in lines):
            continue
        text = ' '.join(' '.join(lines).split())
        concise = CONCISE.get(index)
        if concise and text == concise[0]:
            lines = [concise[1]]
        wrapped = wrap(lines)
        if wrapped != lines:
            replacements[block] = reflow(message, wrapped, table)
    return bundle.build(replacements)


def fit_title_text(raw, table):
    bundle = Bundle.parse(raw)
    if len(bundle.offsets) != 1000 or len(bundle.blocks) != 1000:
        raise ValueError('Unmeasured title directory')
    plan = json.loads((Path(__file__).resolve().parents[1] /
                       'config/title-name-wording.json').read_text(encoding='utf-8'))
    if plan['schema'] != 1 or plan['resource_id'] != '00040e2f' or plan['maximum_advance'] != WIDTH:
        raise ValueError('Unsupported title name layout plan')
    replacements = {}
    for index, block in enumerate(bundle.offsets[:500]):
        message = Message.parse(bundle.blocks[block])
        lines, commands = message_template(message, table)
        if len(lines) == 1 and width(lines[0]) <= WIDTH:
            continue
        entry = plan['entries'].get(str(index))
        source = ' '.join(' '.join(lines).split())
        if commands or not entry or hashlib.sha256(source.encode('utf-8')).hexdigest() != entry['source_text_sha256']:
            raise ValueError(f'Title name {index} needs a source-reviewed layout')
        if width(entry['text']) > WIDTH:
            raise ValueError('Reviewed title name exceeds its panel')
        replacements[block] = reflow(message, [entry['text']], table)
    return reflow_descriptions(bundle.build(replacements), table)
