import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source_export',ROOT/'tools/export-github-source.py')
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)


class SourceExport(unittest.TestCase):
    def test_preserves_user_readme_and_stages_note_removal_without_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';destination=Path(tmp)/'export'
            (source/'config').mkdir(parents=True);destination.mkdir()
            (source/'README.md').write_text('Source README')
            (destination/'README.md').write_text('User edited README')
            (destination/'AGENTS.md').write_text('Private development notes')
            (source/'config/lordofapocalypse.toml').write_text('[runtime]\ncommit="'+('1'*40)+'"\n[previous_runtime]\ncommit="'+('2'*40)+'"\n')
            git=['git','-c','safe.directory='+destination.as_posix(),'-C',str(destination)]
            subprocess.run(git+['init'],check=True,capture_output=True)
            subprocess.run(git+['add','README.md','AGENTS.md'],check=True,capture_output=True)
            with patch.object(exporter,'ROOT',source),patch.object(exporter,'selected',return_value={'README.md':source/'README.md'}):
                result=exporter.export(destination)
            self.assertEqual((destination/'README.md').read_text(),'User edited README')
            self.assertFalse((destination/'AGENTS.md').exists())
            indexed=subprocess.check_output(git+['ls-files'],text=True).splitlines()
            self.assertNotIn('AGENTS.md',indexed)
            self.assertIn('external/nakagawa-recomp',indexed)
            self.assertIn('external/psp-recomp',indexed)
            self.assertFalse(result['committed']);self.assertFalse(result['pushed'])
            self.assertNotEqual(subprocess.run(git+['rev-parse','--verify','HEAD'],capture_output=True).returncode,0)


if __name__=='__main__':unittest.main()
