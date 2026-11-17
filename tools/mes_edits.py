"""Apply identity-checked plain-text edits without changing message structure."""
import hashlib
from mes_codec import Bundle, Message
import mes_tokens
import password_keys
from mes_legacy import LegacyMessage
from mes_subtitles import TimedMessage


def digest(data):
    return hashlib.sha256(data).hexdigest()


def apply_edits(source, table, manifest):
    if digest(source) != manifest["source_bundle_sha256"]:
        raise ValueError("Source bundle hash differs from translation manifest")
    bundle = Bundle.parse(source)
    protected_blocks = {block for alias, block in enumerate(bundle.offsets)
                        if password_keys.protected(manifest.get('resource_id'), alias)}
    replacements, seen = {}, set()
    for entry in manifest["entries"]:
        index = entry["message_index"]
        if not isinstance(index, int) or not 0 <= index < len(bundle.offsets):
            raise ValueError("Message index out of bounds")
        block = bundle.offsets[index]
        if block in protected_blocks:
            raise ValueError('Literal promotional password keys cannot be translated')
        if block in seen:
            raise ValueError("Duplicate edit or alias conflict")
        seen.add(block)
        raw = bundle.blocks[block]
        if digest(raw) != entry["before_sha256"]:
            raise ValueError("Source message hash differs from translation manifest")
        if entry.get('item_panel_layout'):
            if manifest.get('resource_id') not in ('000410e8','00040d77'):raise ValueError('Item panel layout is measured only for the shared gear and item-description tables')
            from item_description_layout import replace
            message=Message.parse(raw)
            if mes_tokens.message_template(message,table)[0]!=entry['original_lines']:raise ValueError('Original item text differs')
            replacements[block]=replace(message,entry['english_lines'],table,preserve_words=not entry.get('reviewed_concise_wording',False))
            continue
        if entry.get("timed_subtitles"):
            message = TimedMessage.parse(raw)
            cue_seen = set()
            for edit in entry["cue_edits"]:
                cue_index = edit["cue_index"]
                if cue_index in cue_seen or not 0 <= cue_index < len(message.cues):
                    raise ValueError("Duplicate or invalid timed cue index")
                cue_seen.add(cue_index)
                cue = message.cues[cue_index]
                if digest(cue.build()) != edit["before_sha256"]:
                    raise ValueError("Timed cue identity differs")
                if mes_tokens.message_template(cue.message(), table)[0] != edit["original_lines"]:
                    raise ValueError("Timed cue original text differs")
                message = message.replace_cue(cue_index, edit["english_lines"], table)
            replacements[block] = message
            continue
        legacy = entry.get("legacy_cp932", False)
        if legacy and manifest.get("resource_id") != "00040008":
            raise ValueError("Legacy framing is measured only for the save/install bundle")
        message = LegacyMessage.parse(raw, table) if legacy else Message.parse(raw)
        token_mode = entry.get("token_mode", False)
        if legacy and token_mode:
            raise ValueError("Legacy framing does not accept command-template edits")
        if not token_mode and not message.editable(table):
            raise ValueError("Unresolved inline commands; editing refused")
        original = (mes_tokens.message_template(message, table)[0] if token_mode == "message-stream-v1" else
                    [mes_tokens.template(line[:-1], table)[0] if token_mode else table.decode(line[:-1])
                     for line in message.lines])
        if original != entry["original_lines"]:
            raise ValueError("Original text differs from translation manifest")
        lines = entry["english_lines"]
        if len(lines) != len(message.lines) or not all(isinstance(s, str) for s in lines):
            raise ValueError("Preserve the original line count")
        if token_mode == "message-stream-v1":
            message = mes_tokens.replace_message(message, lines, table)
        elif token_mode:
            changed = tuple(mes_tokens.replace(line[:-1], text, table) + (line[-1],)
                            for line, text in zip(message.lines, lines))
            message = Message(message.header, changed, message.padding)
        else:
            for line, text in enumerate(lines):
                message = message.replace_line(line, text, table)
        replacements[block] = message
    if not replacements:
        raise ValueError("No edits supplied")
    output = bundle.build(replacements)
    check = Bundle.parse(output)
    if check.offsets != bundle.offsets or check.build() != output:
        raise ValueError("Edited bundle failed structural verification")
    for block, raw in enumerate(bundle.blocks):
        expected = replacements[block].build() if block in replacements else raw
        if check.blocks[block] != expected:
            raise ValueError("Unedited data or expected replacement differs")
    return output
