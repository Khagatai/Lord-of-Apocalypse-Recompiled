"""Lossless templates for measured MES commands; unknown commands stay blocked."""
import re
from mes_codec import Message

# Measured from the original title's command handlers, not inferred from text:
# renderer/width dispatch 08ccf198 -> 08bf99b4 (RGB), 08bf9954 (reset),
# 08bf99f0 (icon), 08bf9a28 (variable); substitutions at 0886edd0,
# 0886ee00, 0886ef9c, 0886f000 and 0886f058. FFF8 render handler
# 08bfa17c -> 08bfa1dc advances only two bytes (no operands); the width
# helper skips differently and must not be used to frame raw dialogue.
OPERANDS = {0xfffa: 3, 0xfff9: 0, 0xfff4: 1, 0xffef: 1,
            0xfff8: 0, 0xefe0: 1, 0xefe1: 1, 0xefe2: 0, 0xeff0: 0, 0xeff1: 1}
TAG = re.compile(r"<cmd:(\d+)>")


def template(words, table):
    text, commands, cursor = [], [], 0
    while cursor < len(words):
        word = words[cursor]
        if word < len(table.codes):
            text.append(chr(table.codes[word]))
            cursor += 1
            continue
        if word not in OPERANDS:
            raise ValueError(f"Unresolved command {word:04x}; editing refused")
        end = cursor + 1 + OPERANDS[word]
        if end > len(words):
            raise ValueError("Truncated command operands")
        text.append(f"<cmd:{len(commands)}>")
        commands.append(tuple(words[cursor:end]))
        cursor = end
    result = "".join(text)
    if len(TAG.findall(result)) != len(commands):
        raise ValueError("Literal text collides with command template syntax")
    return result, tuple(commands)


def replace(words, translated, table):
    if "\n" in translated or "\r" in translated:
        raise ValueError("Preserve explicit line structure")
    _, commands = template(words, table)
    matches = list(TAG.finditer(translated))
    if [m.group(0) for m in matches] != [f"<cmd:{i}>" for i in range(len(commands))]:
        raise ValueError("Command placeholders were removed, duplicated or reordered")
    if "<cmd:" in TAG.sub("", translated):
        raise ValueError("Malformed command placeholder")
    output, cursor = [], 0
    for index, match in enumerate(matches):
        output.extend(table.encode(translated[cursor:match.start()]))
        output.extend(commands[index])
        cursor = match.end()
    output.extend(table.encode(translated[cursor:]))
    return tuple(output)


def message_template(message, table):
    lines, all_commands = [], []
    for line in message.lines:
        text, commands = template(line[:-1], table)
        offset = len(all_commands)
        text = TAG.sub(lambda match: f"<cmd:{int(match[1])+offset}>", text)
        lines.append(text)
        all_commands.extend(commands)
    return lines, tuple(all_commands)


def replace_message(message, lines, table):
    if len(lines) != len(message.lines):
        raise ValueError("Preserve message line count")
    _, commands = message_template(message, table)
    tags = [m.group(0) for line in lines for m in TAG.finditer(line)]
    if tags != [f"<cmd:{i}>" for i in range(len(commands))]:
        raise ValueError("Message command stream changed")
    output = []
    for before, text in zip(message.lines, lines):
        if "\n" in text or "\r" in text or "<cmd:" in TAG.sub("", text):
            raise ValueError("Invalid message line or command marker")
        words, cursor = [], 0
        for match in TAG.finditer(text):
            words.extend(table.encode(text[cursor:match.start()]))
            words.extend(commands[int(match[1])])
            cursor = match.end()
        words.extend(table.encode(text[cursor:]))
        output.append(tuple(words) + (before[-1],))
    result = Message(message.header, tuple(output), message.padding)
    if message_template(result, table)[1] != commands:
        raise ValueError("Encoded command operands differ")
    return result
