"""Measured legacy save/install text framing: CP932 byte counts, not word counts."""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class LegacyMessage:
    header: tuple
    lines: tuple
    padding: tuple
    table: object

    @classmethod
    def parse(cls, data, table):
        if len(data) < 12 or len(data) % 2:
            raise ValueError("Invalid legacy message extent")
        words = struct.unpack(f"<{len(data)//2}H", data)
        cursor, lines = 4, []
        while cursor < len(words):
            length = words[cursor]
            cursor += 1
            start = cursor
            while cursor < len(words) and words[cursor] not in (0xfffe, 0xffff):
                if words[cursor] >= len(table.codes):
                    raise ValueError("Unsupported legacy inline command")
                cursor += 1
            if cursor == len(words):
                raise ValueError("Legacy message terminator missing")
            line = words[start:cursor+1]
            cursor += 1
            try:
                actual = len(table.decode(line[:-1]).encode("cp932"))
            except UnicodeError as error:
                raise ValueError("Legacy glyphs cannot be encoded as CP932") from error
            if actual != length:
                raise ValueError("Legacy byte count differs")
            lines.append(line)
            if line[-1] == 0xffff:
                if len(lines) != words[1] or any(words[cursor:]):
                    raise ValueError("Legacy line count or trailing padding differs")
                return cls(words[:4], tuple(lines), words[cursor:], table)
        raise ValueError("Legacy final terminator missing")

    def build(self):
        words = list(self.header)
        for line in self.lines:
            length = len(self.table.decode(line[:-1]).encode("cp932"))
            if length > 65535:
                raise ValueError("Legacy text byte count exceeds field")
            words.extend((length, *line))
        words.extend(self.padding)
        return struct.pack(f"<{len(words)}H", *words)

    def editable(self, table):
        return table.codes == self.table.codes

    def replace_line(self, index, text, table):
        if not self.editable(table) or "\n" in text or "\r" in text:
            raise ValueError("Legacy table or explicit line structure differs")
        lines = list(self.lines)
        lines[index] = table.encode(text) + (lines[index][-1],)
        result = LegacyMessage(self.header, tuple(lines), self.padding, self.table)
        LegacyMessage.parse(result.build(), self.table)
        return result
