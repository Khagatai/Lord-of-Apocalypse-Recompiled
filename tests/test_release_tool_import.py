import hashlib,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('release_tool_import',ROOT/'tools/import-release-tools.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


class ReleaseToolImport(unittest.TestCase):
    def fixture(self,root,paths=None):
        paths=paths or {'private/tools/pspdecrypt/example.c':b'public source','private/modules/EBOOT.elf':b'must never import',
            'private/tools/pspdecrypt/EBOOT.elf':b'not a public tool dependency'}
        archive=root/'payload.zip';records=[]
        with zipfile.ZipFile(archive,'w') as z:
            for name,data in paths.items():
                z.writestr(m.PREFIX+name,data);records.append(dict(path=name,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
            z.writestr(m.PREFIX+'PACKAGE-MANIFEST.json',json.dumps(dict(schema=2,files=records,game_payloads_included=False,builds_native_game_locally=True)))
        return archive,dict(size=archive.stat().st_size,sha256=m.sha(archive))

    def test_import_is_repeatable_and_never_imports_game_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,metadata=self.fixture(root);target=root/'clone';target.mkdir()
            first=m.import_payload(archive,metadata,target);second=m.import_payload(archive,metadata,target)
            self.assertEqual(first['imported_files'],1);self.assertEqual(second['imported_files'],0)
            self.assertFalse((target/'private/modules').exists())

    def test_wrong_archive_hash_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,metadata=self.fixture(root);metadata['sha256']='0'*64;target=root/'clone';target.mkdir()
            with self.assertRaisesRegex(ValueError,'hash/size'):m.import_payload(archive,metadata,target)
            self.assertEqual(list(target.iterdir()),[])

    def test_changed_existing_dependency_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,metadata=self.fixture(root);target=root/'clone';path=target/'private/tools/pspdecrypt/example.c';path.parent.mkdir(parents=True);path.write_bytes(b'my edits')
            with self.assertRaisesRegex(ValueError,'Existing dependency differs'):m.import_payload(archive,metadata,target)
            self.assertEqual(path.read_bytes(),b'my edits')

    def test_path_traversal_rejected_even_outside_dependency_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,metadata=self.fixture(root,{'../escaped':b'bad'});target=root/'clone';target.mkdir()
            with self.assertRaisesRegex(ValueError,'Unsafe dependency path'):m.import_payload(archive,metadata,target)
            self.assertFalse((root/'escaped').exists())


if __name__=='__main__':unittest.main()
