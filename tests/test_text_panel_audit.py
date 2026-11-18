import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from mes_codec import Bundle, GlyphTable, Message
from text_panel_layout import validate

spec = importlib.util.spec_from_file_location('panel_audit', ROOT / 'tools/audit-text-panels.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class TextPanelAuditTests(unittest.TestCase):
    def test_icons_count_and_dynamic_substitutions_require_review(self):
        table = GlyphTable(tuple(range(128)))
        message = Message((65535, 0, 0, 0), (
            (65530, 255, 255, 255, *table.encode('A'), 65524, 1, 65519, 2, 65535),))
        lines, advances, uncertain = audit.measurements(message, table)
        self.assertEqual(advances, [18])
        self.assertEqual(uncertain, ['ffef'])

    def test_profiles_require_matching_resource_range_and_shape(self):
        profile = dict(resource_id='00040da0', name='orb', ranges=[[63, 269]],
                       minimum_rows=2, width=144, rows=4)
        self.assertEqual(audit.profile_for([profile], '00040da0', 87, ['first', 'second']), profile)
        self.assertIsNone(audit.profile_for([profile], '00040da0', 86, ['God Mark']))
        self.assertIsNone(audit.profile_for([profile], '000410cc', 87, ['first', 'second']))
        self.assertIsNone(audit.profile_for([profile], '00040da0', 527, ['first', 'second']))

    def test_generation_rejects_single_line_overflow_at_a_pinned_slot(self):
        table = GlyphTable(tuple(range(128)))
        message = Message((65535, 0, 0, 0), (table.encode('A' * 25) + (65535,),))
        raw = Bundle(1, (0,), b'', (message.build(),)).build()
        profile = dict(resource_id='00040da0', name='orb', ranges=[[0, 0]],
                       minimum_rows=2, width=144, rows=4)
        with self.assertRaisesRegex(ValueError, '00040da0:0 exceeds orb'):
            validate(raw, table, 0x40da0, [profile])
        profile['width'] = 150
        self.assertEqual(validate(raw, table, 0x40da0, [profile]), 1)
        self.assertEqual(validate(raw, table, 0x410cc, [profile]), 0)


if __name__ == '__main__':
    unittest.main()
