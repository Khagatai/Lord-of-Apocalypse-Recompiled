from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import mip_runtime_patch


class PrivateMipRenderer(unittest.TestCase):
    def test_refuses_an_unknown_framework_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'framework/src/rt/gpu_sdl3vk/ge_gpu.c'
            source.parent.mkdir(parents=True)
            source.write_text('unrecognized runtime source')
            output=root/'prototype.c'
            with self.assertRaisesRegex(ValueError,'source hash mismatch'):
                mip_runtime_patch.prepare(root/'framework',output)
            self.assertFalse(output.exists())
            self.assertEqual(source.read_text(),'unrecognized runtime source')

    def test_pinned_copy_is_repeatable_and_leaves_upstream_unchanged(self):
        framework=ROOT/'external/nakagawa-recomp'
        source=framework/'src/rt/gpu_sdl3vk/ge_gpu.c'
        before=source.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            first=Path(folder)/'first.c';second=Path(folder)/'second.c'
            report=mip_runtime_patch.prepare(framework,first)
            again=mip_runtime_patch.prepare(framework,second)
            self.assertEqual(report,again)
            self.assertEqual(first.read_bytes(),second.read_bytes())
            self.assertEqual(report['upstream_sha256'],hashlib.sha256(before).hexdigest())
            self.assertEqual(report['generated_sha256'],hashlib.sha256(first.read_bytes()).hexdigest())
            self.assertEqual(len(report['extension_sha256']),5)
        self.assertEqual(source.read_bytes(),before)
