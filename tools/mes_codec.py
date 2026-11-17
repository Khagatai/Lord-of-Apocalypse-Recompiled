"""Lossless MES message framing and TTL glyph decoding; refuse unsafe text edits."""
from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class GlyphTable:
    codes: tuple

    @classmethod
    def parse(cls, data):
        if len(data) < 12:
            raise ValueError("Truncated glyph table")
        magic, version, count = struct.unpack_from("<4sII", data)
        end = 12 + count * 2
        if magic != b".TTL" or version != 1 or not count or end > len(data) or any(data[end:]):
            raise ValueError("Unsupported glyph table or invalid extent")
        return cls(struct.unpack_from(f"<{count}H", data, 12))

    def decode(self, words):
        return "".join(chr(self.codes[v]) if v < len(self.codes) else f"<u16:{v:04x}>" for v in words)

    def encode(self, text):
        reverse = {}
        for index, code in enumerate(self.codes):
            reverse.setdefault(code, index)
        try:
            return tuple(reverse[ord(char)] for char in text)
        except KeyError as error:
            raise ValueError("Text contains a character absent from the game glyph table") from error

@dataclass(frozen=True)
class Message:
    header: tuple
    lines: tuple
    padding: tuple = ()

    @classmethod
    def parse(cls, data):
        if len(data) < 10 or len(data) % 2:
            raise ValueError("Invalid message word extent")
        words = struct.unpack(f"<{len(data)//2}H", data)
        cursor, lines = 4, []
        while cursor < len(words):
            count = words[cursor]
            cursor += 1
            if not count or cursor + count > len(words):
                raise ValueError("Invalid line length")
            line = words[cursor:cursor+count]
            cursor += count
            if line[-1] not in (0xfffe, 0xffff):
                raise ValueError("Unsupported line ending")
            lines.append(line)
            if line[-1] == 0xffff:
                if any(words[cursor:]):
                    raise ValueError("Unsupported trailing message data")
                return cls(words[:4], tuple(lines), words[cursor:])
        raise ValueError("Missing final message terminator")

    def build(self):
        words = list(self.header)
        for line in self.lines:
            if not 1 <= len(line) <= 65535:
                raise ValueError("Line length outside 16-bit range")
            words.extend((len(line), *line))
        words.extend(self.padding)
        return struct.pack(f"<{len(words)}H", *words)

    def editable(self, table):
        # Undecoded inline commands/icons may contain glyph-looking operands.
        # Never turn those operands into editable prose by guessing their width.
        return all(all(v < len(table.codes) for v in line[:-1]) for line in self.lines)

    def replace_line(self, index, text, table):
        if not self.editable(table):
            raise ValueError("Message contains unresolved inline commands; editing refused")
        if "\n" in text or "\r" in text:
            raise ValueError("Edit explicit lines rather than inserting uncontrolled line breaks")
        lines = list(self.lines)
        lines[index] = table.encode(text) + (lines[index][-1],)
        result = Message(self.header, tuple(lines), self.padding)
        result.build()
        return result

@dataclass(frozen=True)
class Bundle:
    version: int
    offsets: tuple
    prefix_gap: bytes
    blocks: tuple

    @classmethod
    def parse(cls, data):
        if len(data) < 12:
            raise ValueError("Truncated MES header")
        magic, version, count = struct.unpack_from("<4sII", data)
        table_end = 12 + count * 4
        if magic != b".MES" or version != 1 or not count or table_end > len(data):
            raise ValueError("Unsupported MES directory")
        offsets = struct.unpack_from(f"<{count}I", data, 12)
        if any(o < table_end or o >= len(data) or o % 2 for o in offsets):
            raise ValueError("Message pointer outside bundle")
        starts = sorted(set(offsets))
        bounds = starts + [len(data)]
        blocks = tuple(data[a:b] for a, b in zip(bounds, bounds[1:]))
        indices = {offset: index for index, offset in enumerate(starts)}
        return cls(version, tuple(indices[o] for o in offsets), data[table_end:starts[0]], blocks)

    def build(self, replacements=None):
        replacements = replacements or {}
        blocks = []
        for index, raw in enumerate(self.blocks):
            if index in replacements:
                from mes_legacy import LegacyMessage
                from mes_subtitles import TimedMessage
                if isinstance(replacements[index], LegacyMessage):
                    LegacyMessage.parse(raw, replacements[index].table)
                elif isinstance(replacements[index], TimedMessage):
                    TimedMessage.parse(raw)
                else:
                    Message.parse(raw)  # Refuse edits to an opaque framing variant.
                blocks.append(replacements[index].build())
            else:
                try:
                    blocks.append(Message.parse(raw).build())
                except ValueError:
                    blocks.append(raw)  # Unedited unknown records are preserved verbatim.
        position = 12 + len(self.offsets) * 4 + len(self.prefix_gap)
        positions = []
        for raw in blocks:
            positions.append(position)
            position += len(raw)
        pointers = [positions[i] for i in self.offsets]
        return (struct.pack("<4sII", b".MES", self.version, len(pointers)) +
                struct.pack(f"<{len(pointers)}I", *pointers) + self.prefix_gap + b"".join(blocks))
