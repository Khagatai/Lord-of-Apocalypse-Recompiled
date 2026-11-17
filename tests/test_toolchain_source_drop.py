import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('toolchain_setup',ROOT/'tools/install-toolchain.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)


class ToolchainSourceDrop(unittest.TestCase):
    def fixture(self,root):
        (root/'config').mkdir()
        (root/'config/lordofapocalypse.toml').write_text('[runtime]\npath="external/nakagawa-recomp"\ncommit="pin"\n')
        source=root/'external/nakagawa-recomp/source.c';source.parent.mkdir(parents=True);source.write_bytes(b'public')
        manifest=json.dumps(dict(schema=1,commit='pin',files={'source.c':hashlib.sha256(b'public').hexdigest()})).encode()
        (root/'config/source.json').write_bytes(manifest)
        (root/'config/local-build-inputs.json').write_text(json.dumps(dict(schema=1,framework=dict(
            manifest='config/source.json',sha256=hashlib.sha256(manifest).hexdigest(),commit='pin'))))
        return source

    def test_bootstrap_without_git_or_game_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            with patch.object(setup.subprocess,'check_output',side_effect=AssertionError('Git must not be invoked')):
                folder,pin=setup.verify_framework(root)
            self.assertEqual(pin,'pin');self.assertFalse((root/'private').exists())

    def test_tampered_source_stops_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=self.fixture(root);source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'source changed'):setup.verify_framework(root)
            self.assertFalse((root/'private').exists())

    def test_project_pin_cannot_override_source_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            path=root/'config/lordofapocalypse.toml';path.write_text(path.read_text().replace('commit="pin"','commit="other"'))
            with self.assertRaisesRegex(ValueError,'pins changed'):setup.verify_framework(root)


if __name__=='__main__':unittest.main()
