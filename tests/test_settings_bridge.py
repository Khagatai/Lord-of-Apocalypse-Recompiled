import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import graphics_settings as settings
from settings_bridge import Bridge, atomic_json
from unittest.mock import patch


class SettingsBridge(unittest.TestCase):
    def test_atomic_mailbox_retries_a_transient_windows_sharing_violation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ack.json'
            original=__import__('os').replace
            calls=[]
            def replace(source,target):
                calls.append(1)
                if len(calls)==1: raise PermissionError('sharing violation')
                return original(source,target)
            with patch('settings_bridge.os.replace',side_effect=replace), patch('settings_bridge.time.sleep'):
                atomic_json(path,{'sequence':5,'ok':True})
            self.assertEqual(len(calls),2)
            self.assertEqual(json.loads(path.read_text()),{'sequence':5,'ok':True})

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.preferences = self.folder/'preferences.json'
        self.bridge = Bridge(self.folder, self.preferences)

    def request(self, seq=1, restart=False, **changes):
        value = dict(settings.DEFAULTS, **changes)
        atomic_json(self.folder/'settings-request.json',
                    {'sequence': seq, 'restart': restart, 'codes': settings.menu_codes(value)})
        self.bridge.poll()
        return json.loads((self.folder/'settings-ack.json').read_text())

    def test_persists_real_choices_and_requires_matching_clean_restart_confirmation(self):
        self.assertTrue(self.request(restart=True, render_scale=4, variant='japanese')['ok'])
        self.assertEqual(settings.load(self.preferences)['render_scale'], 4)
        self.assertIsNone(self.bridge.restart_after_exit(0))
        atomic_json(self.folder/'restart-ready.json', {'sequence': 999})
        self.assertIsNone(self.bridge.restart_after_exit(0))
        atomic_json(self.folder/'restart-ready.json', {'sequence': 1})
        self.assertIsNone(self.bridge.restart_after_exit(1))
        self.assertEqual(self.bridge.restart_after_exit(0), 'japanese')

    def test_plain_save_and_stale_request_never_restart(self):
        self.request()
        before = self.preferences.read_bytes()
        self.request(render_scale=4)
        self.assertEqual(before, self.preferences.read_bytes())
        atomic_json(self.folder/'restart-ready.json', {'sequence': 1})
        self.assertIsNone(self.bridge.restart_after_exit(0))

    def test_invalid_request_leaves_preferences_unchanged_and_reports_failure(self):
        self.request()
        before = self.preferences.read_bytes()
        for seq, codes in ((2, [999]*12), (3, [True]*12), (4, [0]*11)):
            atomic_json(self.folder/'settings-request.json', {'sequence': seq, 'restart': True, 'codes': codes})
            self.bridge.poll()
            self.assertFalse(json.loads((self.folder/'settings-ack.json').read_text())['ok'])
            self.assertEqual(self.preferences.read_bytes(), before)
            self.assertIsNone(self.bridge.restart_after_exit(0))

    def test_write_failure_is_not_reported_as_success(self):
        self.preferences.mkdir()
        self.assertFalse(self.request()['ok'])
        self.assertTrue((self.folder/'settings-error.txt').is_file())

    def test_fresh_configuration_defaults_to_wip_and_exports_all_choices(self):
        env = self.bridge.environment(settings.load(self.preferences))
        self.assertEqual(env['LOA_SETTINGS_CODES'].split()[0], '0')
        self.assertEqual(len(env['LOA_SETTINGS_CODES'].split()), len(settings.OPTIONS))


if __name__ == '__main__':
    unittest.main()
