from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import texture_pack


class HdUiSelection(unittest.TestCase):
    def test_saved_toggle_only_applies_to_wip_vulkan(self):
        enabled={'hd_ui':True}
        self.assertEqual(texture_pack.selected_folder(enabled,'vulkan','english-text-test').name,'hd-remaster-pack')
        for renderer,namespace in [('gdi','english-text-test'),('vulkan','japanese'),('vulkan','english-v16')]:
            self.assertIsNone(texture_pack.selected_folder(enabled,renderer,namespace))
        self.assertIsNone(texture_pack.selected_folder({'hd_ui':False},'vulkan','english-text-test'))

    def test_explicit_diagnostic_pack_does_not_silently_cross_versions(self):
        explicit=Path('private/custom-pack')
        self.assertEqual(texture_pack.selected_folder({'hd_ui':False},'vulkan','english-text-test',explicit),explicit)
        for renderer,namespace in [('gdi','english-text-test'),('vulkan','japanese')]:
            with self.assertRaises(ValueError):
                texture_pack.selected_folder({'hd_ui':True},renderer,namespace,explicit)
