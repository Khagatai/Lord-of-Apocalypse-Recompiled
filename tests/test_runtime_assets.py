from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from runtime_assets import configure_fonts


class RuntimeFonts(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).resolve()
        self.release=self.root/'release'
        (self.release/'font').mkdir(parents=True)
        (self.release/'font/project.pgf').write_bytes(b'locator-only font fixture')

    def test_relocated_executable_uses_release_font_assets(self):
        env={}
        root,hashes=configure_fonts(env,self.release)
        self.assertEqual(root,self.release/'font')
        self.assertEqual(env['SR_FONTDIR'],str(root))
        self.assertIn('project.pgf',hashes)

    def test_explicit_absolute_font_configuration_is_preserved(self):
        selected=self.root/'selected'
        selected.mkdir()
        (selected/'different.pgf').write_bytes(b'separate locator fixture')
        env={'SR_FONTDIR':str(selected)}
        root,hashes=configure_fonts(env,self.release)
        self.assertEqual(root,selected)
        self.assertEqual(set(hashes),{'different.pgf'})

    def test_invalid_relative_configuration_is_not_silently_repaired(self):
        with self.assertRaisesRegex(ValueError,'absolute'):
            configure_fonts({'SR_FONTDIR':'relative/font'},self.release)

    def test_missing_assets_fail_instead_of_testing_blank_glyphs(self):
        empty=self.root/'empty'
        empty.mkdir()
        with self.assertRaisesRegex(FileNotFoundError,'no PGF'):
            configure_fonts({'SR_FONTDIR':str(empty)},self.release)
        with self.assertRaisesRegex(FileNotFoundError,'missing'):
            configure_fonts({'SR_FONTDIR':str(self.root/'missing')},self.release)


if __name__=='__main__':
    unittest.main()
