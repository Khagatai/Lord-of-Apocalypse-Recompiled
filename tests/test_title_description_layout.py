import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from title_description_layout import wrap, width, WIDTH, LINES, reflow_descriptions, fit_title_text
from mes_codec import Bundle, GlyphTable, Message
from mes_tokens import message_template


class TitleDescriptionLayoutTests(unittest.TestCase):
    def test_reported_spear_gunner_description(self):
        original = ['Primarily, a general term for slayers who fight',
                    'monsters using spear rifles.', '']
        result = wrap(original)
        self.assertEqual(' '.join(result).split(), ' '.join(original).split())
        self.assertLessEqual(len(result), LINES)
        self.assertTrue(all(width(line) <= WIDTH for line in result))
        self.assertGreater(len(result), 2)

    def test_empty_and_already_wrapped_descriptions(self):
        self.assertEqual(wrap(['', '', '']), [''])
        result = wrap(['A warrior of unknown origin.'])
        self.assertEqual(result, ['A warrior of unknown origin.'])

    def test_overflow_requires_review(self):
        with self.assertRaises(ValueError):
            wrap(['word ' * 50])
        with self.assertRaises(ValueError):
            wrap(['W' * 30])

    def test_bundle_preserves_names_and_reflows_description(self):
        table = GlyphTable(tuple(range(128)))
        name = Message((65535, 0, 0, 0), (table.encode('Spear Gunner') + (65535,),)).build()
        lines = ['Primarily, a general term for slayers who fight',
                 'monsters using spear rifles.', '']
        description = Message((65535, 2, 0, 0), tuple(
            table.encode(line) + (65535 if i == 2 else 65534,)
            for i, line in enumerate(lines))).build()
        bundle = Bundle(1, tuple(range(1000)), b'', (name,) * 500 + (description,) * 500)
        original = bundle.build()
        fixed = reflow_descriptions(original, table)
        result = Bundle.parse(fixed)
        self.assertEqual(result.blocks[:500], bundle.blocks[:500])
        for raw in result.blocks[500:]:
            message = Message.parse(raw)
            wrapped, commands = message_template(message, table)
            self.assertEqual(' '.join(wrapped).split(), ' '.join(lines).split())
            self.assertEqual(message.header, (65535, len(wrapped) - 1, 0, 0))
            self.assertLessEqual(len(wrapped), LINES)
            self.assertTrue(all(width(line) <= WIDTH for line in wrapped))
            self.assertFalse(commands)
        self.assertEqual(reflow_descriptions(fixed, table), fixed)

    def test_long_title_name_uses_source_reviewed_wording(self):
        table = GlyphTable(tuple(range(128)))
        def message(text):
            return Message((65535, 0, 0, 0), (table.encode(text) + (65535,),)).build()
        blocks = [message('Title')] * 500 + [message('')] * 500
        blocks[12] = message('The fate guided by dragon and thunder clouds')
        original = Bundle(1, tuple(range(1000)), b'', tuple(blocks)).build()
        fixed = fit_title_text(original, table)
        result = Bundle.parse(fixed)
        lines, _ = message_template(Message.parse(result.blocks[12]), table)
        self.assertEqual(lines, ["Dragon and Storm's Fate"])
        self.assertEqual(result.blocks[13], blocks[13])
        self.assertEqual(fit_title_text(fixed, table), fixed)
        blocks[12] = message('A different long title that has never been reviewed')
        with self.assertRaises(ValueError):
            fit_title_text(Bundle(1, tuple(range(1000)), b'', tuple(blocks)).build(), table)


if __name__ == '__main__':
    unittest.main()
