"""Timed MES cues. Keep EFF6 clock fields and EFF7 boundaries byte-exact."""
from dataclasses import dataclass
import struct
from mes_codec import Message
import mes_tokens


@dataclass(frozen=True)
class Cue:
    timing: tuple
    lines: tuple
    ending: int

    def message(self):
        return Message((0, 0, 0, 0), self.lines)

    def build(self):
        words = [1, 0xeff6, *self.timing]
        for line in self.lines:
            words.extend((len(line), *line))
        words.extend((2, 0xeff7, self.ending))
        return struct.pack(f"<{len(words)}H", *words)


@dataclass(frozen=True)
class TimedMessage:
    header: tuple
    cues: tuple
    padding: tuple = ()

    @classmethod
    def parse(cls, data):
        if len(data) < 32 or len(data) % 2:
            raise ValueError("Invalid timed subtitle extent")
        words = struct.unpack(f"<{len(data)//2}H", data)
        if words[0] != 0xff:
            raise ValueError("Unknown timed subtitle header")
        cursor, cues, records = 4, [], 0
        while cursor < len(words):
            if words[cursor:cursor+2] != (1, 0xeff6) or cursor+10 > len(words):
                raise ValueError("Expected timed cue start")
            timing = words[cursor+2:cursor+10]
            cursor += 10
            records += 1
            lines = []
            while cursor < len(words):
                count = words[cursor]
                cursor += 1
                if not count or cursor+count > len(words):
                    raise ValueError("Timed line extent differs")
                line = words[cursor:cursor+count]
                cursor += count
                records += 1
                if line[0] == 0xeff7:
                    if count != 2 or line[-1] not in (0xfffe, 0xffff) or not lines:
                        raise ValueError("Invalid timed cue end")
                    cues.append(Cue(timing, tuple(lines), line[-1]))
                    if line[-1] == 0xffff:
                        if records-1 != words[1] or any(words[cursor:]):
                            raise ValueError("Timed record count or padding differs")
                        return cls(words[:4], tuple(cues), words[cursor:])
                    break
                if line[-1] != 0xfffe:
                    raise ValueError("Unexpected timed text terminator")
                lines.append(line)
            else:
                raise ValueError("Timed cue end missing")
        raise ValueError("Timed final terminator missing")

    def build(self):
        return (struct.pack("<4H", *self.header) + b"".join(cue.build() for cue in self.cues) +
                struct.pack(f"<{len(self.padding)}H", *self.padding))

    def replace_cue(self, index, translated, table):
        cue = self.cues[index]
        message = mes_tokens.replace_message(cue.message(), translated, table)
        cues = list(self.cues)
        cues[index] = Cue(cue.timing, message.lines, cue.ending)
        result = TimedMessage(self.header, tuple(cues), self.padding)
        if TimedMessage.parse(result.build()).build() != result.build():
            raise ValueError("Timed edited roundtrip differs")
        return result
