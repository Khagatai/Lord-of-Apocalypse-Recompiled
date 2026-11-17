import hashlib,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import media_runtime_patch as patch

class MediaRuntimePatch(unittest.TestCase):
    def test_unknown_source_refused(self):
        with self.assertRaisesRegex(ValueError,'hash mismatch'):patch.render(b'unknown source')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):patch.render_audio(b'unknown source')

    def test_audio_private_copy_preserves_pinned_source(self):
        framework=ROOT/'external/nakagawa-recomp';source=framework/'src/rt/hle_audio.c';before=source.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'hle_audio.c';report=patch.prepare_audio(framework,path)
            self.assertEqual(report['generated_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertIn('(uint32_t)q > n)',path.read_text())
            self.assertIn('AUDIO_LATE_WAKE_FRAMES',path.read_text())
        self.assertEqual(before,source.read_bytes())

    def test_native_regressing_clock_experiment_is_excluded_by_default(self):
        source=(ROOT/'external/nakagawa-recomp/src/rt/mpeg.c').read_bytes()
        self.assertNotIn('loa_audio_held_has_pts',patch.render(source))
        self.assertIn('loa_audio_held_has_pts',patch.render(source,experimental_audio_clock=True))

    def test_repeatable_private_copy_preserves_pinned_source(self):
        framework=ROOT/'external/nakagawa-recomp';source=framework/'src/rt/mpeg.c';before=source.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'mpeg.c';first=patch.prepare(framework,path);content=path.read_bytes()
            self.assertEqual(first,patch.prepare(framework,path));self.assertEqual(content,path.read_bytes())
            self.assertIn('MEM_R8(a+5)',path.read_text())
            self.assertEqual(first['generated_sha256'],hashlib.sha256(content).hexdigest())
        self.assertEqual(before,source.read_bytes())

if __name__=='__main__':unittest.main()
