"""Copied release launches need artifact integrity, not developer Git tooling."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import title


class ReleaseLaunch(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        config=copy.deepcopy(title.CONFIG)
        def fixture(name):
            path=self.root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(('synthetic fixture '+name).encode())
            return hashlib.sha256(path.read_bytes()).hexdigest()
        config['runtime']['codegen_adapter_sha256']=fixture(config['runtime']['codegen_adapter'])
        config['runtime']['timing_codegen_sha256']=fixture('tools/frame_rate_codegen.py')
        config['runtime']['companion_name_codegen_sha256']=fixture('tools/companion_name_codegen.py')
        config['runtime']['camera_codegen_sha256']=fixture('tools/camera_codegen.py')
        config['runtime']['password_codegen_sha256']=fixture('tools/password_codegen.py')
        for module in (config['module'],config['dynamic_modules']['libfont']):
            module['sha256']=fixture(module['file'])
        (self.root/'config').mkdir(exist_ok=True)
        (self.root/'config/lordofapocalypse.json').write_text(json.dumps({
            'executable':{key:config['module'][key] for key in ('base','entry')}}))
        self.folder=self.root/'private/native-release/lordofapocalypse'
        self.metadata={'framework_commit':config['runtime']['commit'],
                       'executable_sha256':fixture('private/native-release/lordofapocalypse/lordofapocalypse.exe'),
                       'flat_image_sha256':fixture('private/native-release/lordofapocalypse/lordofapocalypse_image.bin')}
        self.record=self.folder/'host-ui-build.json'
        self.record.write_text(json.dumps(self.metadata))
        self.config=config
        for context in (patch.object(title,'ROOT',self.root),patch.object(title,'CONFIG',config),
                        patch.object(title.shutil,'which',return_value=None),
                        patch.object(title.subprocess,'check_output',side_effect=AssertionError('Git must not run'))):
            context.start();self.addCleanup(context.stop)

    def test_copied_release_without_git_or_checkout(self):
        self.assertFalse((self.root/'external').exists())
        self.assertEqual(title.verify_launch_inputs(),self.config['runtime']['commit'])

    def test_mismatched_runtime_files_are_rejected(self):
        for name in ('lordofapocalypse.exe','lordofapocalypse_image.bin'):
            path=self.folder/name
            before=path.read_bytes()
            path.write_bytes(b'wrong build')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                title.verify_launch_inputs()
            path.write_bytes(before)

    def test_missing_manifest_and_files_are_rejected(self):
        self.record.unlink()
        with self.assertRaisesRegex(FileNotFoundError,'manifest missing'):
            title.verify_launch_inputs()
        self.record.write_text(json.dumps(self.metadata))
        (self.folder/'lordofapocalypse.exe').unlink()
        with self.assertRaisesRegex(FileNotFoundError,'runtime file missing'):
            title.verify_launch_inputs()

    def test_wrong_framework_pin_is_rejected(self):
        self.metadata['framework_commit']='0'*40
        self.record.write_text(json.dumps(self.metadata))
        with self.assertRaisesRegex(ValueError,'framework pin mismatch'):
            title.verify_launch_inputs()

    def test_game_module_integrity_is_still_required(self):
        (self.root/self.config['module']['file']).write_bytes(b'changed module')
        with self.assertRaisesRegex(ValueError,'Module hash mismatch'):
            title.verify_launch_inputs()

    def test_build_and_diagnostic_checks_still_require_git(self):
        for operation in (title.verify_inputs,lambda:title.verify_launch_inputs('diagnostic')):
            with self.assertRaisesRegex(FileNotFoundError,'Git is required'):
                operation()


if __name__=='__main__':
    unittest.main()
