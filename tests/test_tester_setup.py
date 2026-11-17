import ctypes,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import tester_setup,title
class TesterSetup(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows filename mappings')
    def test_unicode_patch_setup_uses_real_hashes_and_does_not_copy_original(self):
        tool=title.ROOT/'private/tools/xdelta/xdelta3.exe'
        if not tool.is_file():self.skipTest('Local patcher unavailable')
        with tempfile.TemporaryDirectory(prefix='LOA-Ω-') as tmp:
            root=Path(tmp);private=root/'private';private.mkdir()
            original=root/'日本語-original.iso';original.write_bytes(b'abc'*10000)
            wanted=root/'日本語-target.iso';wanted.write_bytes(b'abc'*5000+b'English'+b'abc'*5000)
            delta=private/'日本語.vcdiff';output=private/'prepared.iso'
            with tester_setup.patcher_paths(original,wanted,delta) as (src,dst,patchname):
                subprocess.run([str(tool),'-e','-s',src,dst,patchname],check=True,capture_output=True)
            os.link(tool,private/'patcher.exe')
            record=lambda p:dict(size=p.stat().st_size,sha256=tester_setup.sha(p))
            manifest=root/'release.json';manifest.write_text(json.dumps(dict(schema=1,original=record(original),patcher=dict(path='private/patcher.exe',sha256=tester_setup.sha(tool)),images=[dict(label='test',path='private/prepared.iso',patch='private/日本語.vcdiff',patch_sha256=tester_setup.sha(delta),**record(wanted))])),encoding='utf-8')
            with patch.object(tester_setup,'ROOT',root),patch.object(tester_setup,'MANIFEST',manifest),patch.object(tester_setup,'STATE',private/'state.json'):
                self.assertTrue(tester_setup.prepare(original)['original_unchanged'])
            self.assertEqual(output.read_bytes(),wanted.read_bytes())
            self.assertEqual(original.read_bytes(),b'abc'*10000)
    @unittest.skipUnless(os.name=='nt','Windows filename mappings')
    def test_filename_alias_is_removed_when_patching_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,'simulated patcher failure'):
                with tester_setup.patcher_paths(Path(tmp)/'absent Ω') as names:
                    alias=names[0][4:]
                    raise RuntimeError('simulated patcher failure')
            query=ctypes.WinDLL('kernel32',use_last_error=True).QueryDosDeviceW
            query.argtypes=(ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32)
            self.assertEqual(query(alias,ctypes.create_unicode_buffer(4096),4096),0)
            self.assertEqual(ctypes.get_last_error(),2)
    def test_wrong_dump_is_rejected_before_patching(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image=root/'mine.iso';image.write_bytes(b'user original')
            manifest=root/'release.json';manifest.write_text(json.dumps(dict(schema=1,original=dict(size=13,sha256='0'*64))))
            with patch.object(tester_setup,'MANIFEST',manifest),patch.object(tester_setup.subprocess,'run',side_effect=AssertionError('Must not run patcher')):
                with self.assertRaisesRegex(ValueError,'Wrong game image'):tester_setup.prepare(image)
            self.assertEqual(image.read_bytes(),b'user original')
    def test_installer_refuses_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(tester_setup,'ROOT',Path(tmp)):
            with self.assertRaisesRegex(ValueError,'escapes'):tester_setup.private_path('../other/file.iso')
    def test_local_original_path_is_selected_without_changing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/'private/distribution/local-image.json';state.parent.mkdir(parents=True)
            image=(root/'my own dump.iso').resolve();state.write_text(json.dumps(dict(schema=1,path=str(image))))
            with patch.object(title,'ROOT',root):
                self.assertEqual(title.disc_image('japanese'),image)
                state.write_text(json.dumps(dict(schema=1,path='../bad.iso')))
                with self.assertRaisesRegex(ValueError,'absolute'):title.disc_image('japanese')
if __name__=='__main__':unittest.main()
