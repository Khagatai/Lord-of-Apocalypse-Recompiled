import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from mes_codec import Bundle, GlyphTable, Message
from mes_tokens import message_template
from orb_description_layout import descriptions, fit_orb_descriptions
from item_description_layout import width, wrap


class OrbDescriptionLayoutTests(unittest.TestCase):
    def test_race_marks_and_wards_leave_space_for_stats(self):
        self.assertEqual(len(descriptions()), 20)
        for index, text in descriptions().items():
            lines = wrap([text])
            self.assertLessEqual(len(lines), 4, index)
            self.assertTrue(all(width(line) <= 144 for line in lines), index)
        self.assertIn('damage against gods', descriptions()[87])
        self.assertIn('damage from gods', descriptions()[159])
        self.assertIn('Greatly', descriptions()[89])
        self.assertIn('Further', descriptions()[161])

    def test_bundle_keeps_names_other_tables_and_commands(self):
        table = GlyphTable(tuple(range(128)))
        name = Message((65535, 0, 0, 0), (table.encode('God Mark') + (65535,),)).build()
        source = 'An orb engraved with the mark of god-killing.'
        body = Message((65535, 1, 0, 0), (table.encode(source) + (65534,), (65535,))).build()
        blocks = [name] * 683
        blocks[87] = body
        bundle = Bundle(1, tuple(range(683)), b'', tuple(blocks))
        original = bundle.build()
        fixed = fit_orb_descriptions(original, table)
        result = Bundle.parse(fixed)
        edited = set(descriptions())
        for index in set(range(683)) - edited:
            self.assertEqual(result.blocks[index], bundle.blocks[index])
        lines, commands = message_template(Message.parse(result.blocks[87]), table)
        self.assertLessEqual(len(lines), 4)
        self.assertFalse(commands)
        self.assertEqual(fit_orb_descriptions(fixed, table), fixed)
        blocks[87] = Message((65535, 0, 0, 0), ((65524, 1, 65535),)).build()
        with self.assertRaises(ValueError):
            fit_orb_descriptions(Bundle(1, tuple(range(683)), b'', tuple(blocks)).build(), table)


if __name__ == '__main__':
    unittest.main()
