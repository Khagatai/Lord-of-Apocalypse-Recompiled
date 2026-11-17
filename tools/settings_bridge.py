"""Validated per-run settings mailbox. The supervisor alone writes preferences."""
import json
from pathlib import Path
import os
import time
import graphics_settings as settings


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=True)+'\n', encoding='ascii')
    for attempt in range(10):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt==9:
                raise
            time.sleep(0.02)


class Bridge:
    def __init__(self, folder, preferences=settings.SETTINGS):
        self.folder = Path(folder)
        self.preferences = Path(preferences)
        self.sequence = 0
        self.restart_sequence = None
        self.restart_variant = None

    def environment(self, graphics):
        return {'LOA_SETTINGS_DIR': str(self.folder),
                'LOA_SETTINGS_CODES': ' '.join(map(str, settings.menu_codes(graphics)))}

    def poll(self):
        path = self.folder/'settings-request.json'
        if not path.exists():
            return
        try:
            value = json.loads(path.read_text())
            seq = value['sequence']
            if type(seq) is not int or not 1 <= seq <= 1000000:
                raise ValueError('Invalid request sequence')
            if seq <= self.sequence:
                return
            self.sequence = seq
            if set(value) != {'sequence', 'codes', 'restart'} or type(value['restart']) is not bool:
                raise ValueError('Invalid settings request')
            codes = value['codes']
            if not isinstance(codes, list) or any(type(code) is not int for code in codes):
                raise ValueError('Invalid settings choices')
            graphics = settings.from_menu(codes)
            settings.save(graphics, self.preferences)
            self.restart_sequence = seq if value['restart'] else None
            self.restart_variant = graphics['variant'] if value['restart'] else None
            atomic_json(self.folder/'settings-ack.json', {'sequence': seq, 'ok': True})
        except (ValueError, KeyError, TypeError, OSError) as error:
            self.restart_sequence = self.restart_variant = None
            atomic_json(self.folder/'settings-ack.json', {'sequence': self.sequence, 'ok': False})
            (self.folder/'settings-error.txt').write_text(str(error)+'\n')

    def restart_after_exit(self, returncode):
        """A saved preference alone never restarts a run: require runtime confirmation."""
        ready = self.folder/'restart-ready.json'
        if returncode != 0 or self.restart_sequence is None or not ready.exists():
            return None
        try:
            value = json.loads(ready.read_text())
        except (OSError, ValueError):
            return None
        return self.restart_variant if value == {'sequence': self.restart_sequence} else None
