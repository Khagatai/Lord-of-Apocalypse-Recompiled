import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import iso_local_setup as setup
import source_identity

class LocalISOSetup(unittest.TestCase):
    def fixture(self,root):
        root=Path(root);(root/'config').mkdir();(root/'tools').mkdir()
        image=root/'own.iso';image.write_bytes(b'DISC')
        elf=b'\x7fELFsynthetic';digest=hashlib.sha256(elf).hexdigest()
        names=['PSP_GAME/SYSDIR/EBOOT.BIN','PSP_GAME/USRDIR/UPDATA/MODULE/LIBFONT.PRX']
        text='[disc]\niso_size=4\niso_sha256="'+setup.file_hash(image)+'"\nid="NPJH50503"\nversion="1.01"\napp_version="01.00"\n[disc.files]\n'
        text+='\n'.join(json.dumps(n)+'="'+hashlib.sha1(b'DISC').hexdigest()+'"' for n in names)
        text+='\n[module]\nfile="private/modules/EBOOT.elf"\nsha256="'+digest+'"\nbase=1\nentry=2\n[evidence]\nppsspp_revision="synthetic"\n[dynamic_modules.libfont]\nfile="private/modules/LIBFONT.elf"\nsha256="'+digest+'"\n'
        (root/'config/lordofapocalypse.toml').write_text(text)
        seed=dict(schema=1,kind='measured-register-seed',disc_sha256=setup.file_hash(image),module_sha256=digest,base=1,entry=2,ppsspp_revision='synthetic',registers={n:0 for n in ['r'+str(i) for i in range(1,32)]+['hi','lo']})
        (root/'config/startup-registers.json').write_text(json.dumps(seed))
        # Disc parsing itself has separate tests; this fixture isolates ordering,
        # failure propagation and ownership with synthetic module bytes.
        (root/'tools/survey-disc.py').write_text('SECTOR=1\ndef sfo(raw):return dict(DISC_ID="NPJH50503",DISC_VERSION="1.01",APP_VER="01.00")\nclass ISO:\n def __init__(self,stream):pass\n def files(self):return {name:dict(lba=0,size=4) for name in '+repr(names+['PSP_GAME/PARAM.SFO'])+'}\n def read(self,offset,size):return b"DISC"\n')
        bridge=root/'helper.dll';bridge.write_bytes(b'synthetic helper placeholder')
        return image,bridge,elf

    def test_wrong_iso_rejected_before_decrypting_or_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image,bridge,elf=self.fixture(root);image.write_bytes(b'BAD!')
            with patch.object(setup,'decrypt_module') as decrypt:
                with self.assertRaisesRegex(ValueError,'Wrong ISO'):setup.prepare_inputs(image,root,bridge)
                decrypt.assert_not_called()
            self.assertFalse((root/'private').exists())

    def test_late_module_failure_promotes_no_game_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image,bridge,elf=self.fixture(root)
            with patch.object(setup,'decrypt_module',side_effect=[elf,b'wrong plaintext']):
                with self.assertRaisesRegex(ValueError,'Decrypted module identity'):setup.prepare_inputs(image,root,bridge)
            self.assertFalse((root/'private').exists())

    def test_exact_inputs_are_repeatable_and_not_marked_playable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image,bridge,elf=self.fixture(root)
            with patch.object(setup,'decrypt_module',return_value=elf):
                first=setup.prepare_inputs(image,root,bridge)
                module=root/'private/modules/EBOOT.elf';stamp=module.stat().st_mtime_ns
                second=setup.prepare_inputs(image,root,bridge)
            self.assertEqual(module.stat().st_mtime_ns,stamp)
            self.assertEqual(second['state'],'INPUTS_VERIFIED')
            self.assertFalse(first['ready_to_play']);self.assertFalse(first['english_prepared']);self.assertFalse(first['HD_prepared'])
            self.assertEqual(image.read_bytes(),b'DISC')
            seed=(root/'private/oracle-prefix/entry-prefix.trace').read_text()
            self.assertIn('# init r1=0x00000000',seed);self.assertNotIn(' op=',seed)

    def test_unknown_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image,bridge,elf=self.fixture(root)
            existing=root/'private/modules/LIBFONT.elf';existing.parent.mkdir(parents=True);existing.write_bytes(b'keep me')
            with patch.object(setup,'decrypt_module',return_value=elf):
                with self.assertRaisesRegex(ValueError,'Existing local input differs'):setup.prepare_inputs(image,root,bridge)
            self.assertEqual(existing.read_bytes(),b'keep me');self.assertFalse((root/'private/modules/EBOOT.elf').exists())

    def test_boot_identity_and_register_types_are_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image,bridge,elf=self.fixture(root)
            seed_path=root/'config/startup-registers.json';seed=json.loads(seed_path.read_text());seed['entry']=99;seed_path.write_text(json.dumps(seed))
            with self.assertRaisesRegex(ValueError,'Startup seed title identity'):setup.prepare_inputs(image,root,bridge)
            seed['entry']=2;seed['registers']['r1']=True;seed_path.write_text(json.dumps(seed))
            with self.assertRaisesRegex(ValueError,'Invalid measured registers'):setup.prepare_inputs(image,root,bridge)

    def test_output_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'escapes'):setup.install_exact(Path(tmp),'../escape',b'no')

    def test_invalid_encryption_header_is_not_sent_to_native_helper(self):
        with patch.object(setup.ctypes,'CDLL') as library:
            with self.assertRaisesRegex(ValueError,'encrypted PSP'):setup.decrypt_module(b'not encrypted','missing.dll')
            library.assert_not_called()

class SourceDropIdentity(unittest.TestCase):
    def test_source_change_cannot_pass_pinned_drop_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir();source=root/'external/nakagawa-recomp/one.c';source.parent.mkdir(parents=True);source.write_bytes(b'public source')
            manifest=root/'config/source.json';manifest.write_text(json.dumps(dict(schema=1,commit='pin',files={'one.c':setup.file_hash(source)})))
            (root/'config/local-build-inputs.json').write_text(json.dumps(dict(schema=1,framework=dict(manifest='config/source.json',sha256=setup.file_hash(manifest),commit='pin'))))
            self.assertEqual(source_identity.verify(root,'framework'),'pin')
            source.write_bytes(b'tampered')
            with self.assertRaises(ValueError):source_identity.verify(root,'framework')

if __name__=='__main__':unittest.main()
