from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from mes_codec import GlyphTable, Message
from mes_tokens import template, replace, message_template, replace_message


class MesTokens(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable((32, 65, 66, 67))
        self.words = (0xfffa, 1, 2, 3, 1, 0xfff9, 0xfff4, 1, 2)

    def test_rgb_and_icon_operands_never_become_text(self):
        text, commands = template(self.words, self.table)
        self.assertEqual(text, "<cmd:0>A<cmd:1><cmd:2>B")
        self.assertEqual(commands, ((0xfffa, 1, 2, 3), (0xfff9,), (0xfff4, 1)))
        self.assertEqual(replace(self.words, text, self.table), self.words)
        output = replace(self.words, "<cmd:0>CCC<cmd:1><cmd:2>A", self.table)
        self.assertEqual(output, (0xfffa, 1, 2, 3, 3, 3, 3, 0xfff9, 0xfff4, 1, 1))

    def test_moved_missing_or_duplicated_commands_refused(self):
        for value in ("A", "<cmd:1><cmd:0><cmd:2>", "<cmd:0><cmd:1><cmd:2><cmd:2>"):
            with self.assertRaisesRegex(ValueError, "placeholders"):
                replace(self.words, value, self.table)

    def test_unknown_and_truncated_commands_refused(self):
        for words in ((0xfffc,), (0xfffa, 1, 2), (0xefe0,)):
            with self.assertRaises(ValueError):
                template(words, self.table)

    def test_pause_command_does_not_consume_next_glyph(self):
        words = (1, 0xfff8, 2)
        text, commands = template(words, self.table)
        self.assertEqual(text, "A<cmd:0>B")
        self.assertEqual(commands, ((0xfff8,),))
        self.assertEqual(replace(words, "C<cmd:0>A", self.table), (3, 0xfff8, 1))

    def test_reflow_preserves_global_command_order_operands_and_metadata(self):
        message = Message((0xffff, 1, 0, 0), ((0xfffa, 1, 2, 3, 1, 0xfffe), (2, 0xfff9, 0xffff)), (0,))
        before, commands = message_template(message, self.table)
        self.assertEqual(before, ["<cmd:0>A", "B<cmd:1>"])
        result = replace_message(message, ["<cmd:0>CC<cmd:1>", "A"], self.table)
        self.assertEqual(message_template(result, self.table)[1], commands)
        self.assertEqual(result.header, message.header)
        self.assertEqual(result.padding, message.padding)
        self.assertEqual([line[-1] for line in result.lines], [0xfffe, 0xffff])
        with self.assertRaisesRegex(ValueError, "stream"):
            replace_message(message, ["<cmd:1>A", "<cmd:0>B"], self.table)


if __name__ == "__main__":
    unittest.main()
