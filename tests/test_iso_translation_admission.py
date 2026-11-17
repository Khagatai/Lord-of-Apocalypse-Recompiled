import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import translation_candidate as candidate


class OriginalDiscAdmission(unittest.TestCase):
    def fixture(self,root):
        config=root/'config';config.mkdir();private=root/'private';private.mkdir()
        names=['PSP_GAME/SYSDIR/EBOOT.BIN','PSP_GAME/USRDIR/UPDATA/REGFILE.RZL','PSP_GAME/USRDIR/UPDATA/REGFILE.RZP','PSP_GAME/USRDIR/AUDIO.DAT']
        chunks=[b'CODE',b'INDX',b'TEXT',b'AUDI'];raw=bytearray(8192);files={};baseline={}
        for i,(name,data) in enumerate(zip(names,chunks)):
            raw[i*2048:i*2048+4]=data;files[name]=dict(lba=i,size=4);baseline[name]=dict(size=4,sha256=hashlib.sha256(data).hexdigest())
        identity='a'*64;manifest=config/'original.json';manifest.write_text(json.dumps(dict(source_iso_sha256=identity,files=baseline)))
        (config/'local-build-inputs.json').write_text(json.dumps(dict(original_files=dict(manifest='config/original.json',sha256=hashlib.sha256(manifest.read_bytes()).hexdigest()))))
        image=private/'English.iso';image.write_bytes(raw);report=private/'result.json'
        record=dict(scope='English ISO built directly from original Japanese ISO',source_ISO_sha256=identity,status='PASS',
            all_resource_payloads_verified=True,audio_and_game_code_unchanged=True,candidate_size=len(raw),candidate_sha256=hashlib.sha256(raw).hexdigest())
        report.write_text(json.dumps(record));return image,report,record,files

    def check(self,root,image,report,files):
        class ISO:
            def __init__(self,stream):pass
            def files(self):return files
        with patch.object(candidate.title,'ROOT',root),patch.object(candidate.title,'CONFIG',dict(disc=dict(iso_sha256='a'*64))),patch.object(candidate.survey,'ISO',ISO):
            return candidate.verify(image,report)

    def test_verified_message_archive_change_preserves_code_and_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image,report,record,files=self.fixture(root)
            raw=bytearray(image.read_bytes());raw[4096:4100]=b'ENGL';image.write_bytes(raw);record['candidate_sha256']=hashlib.sha256(raw).hexdigest();report.write_text(json.dumps(record))
            self.assertEqual(self.check(root,image,report,files)[0],record['candidate_sha256'])

    def test_self_consistent_report_cannot_admit_changed_code_or_audio(self):
        for offset in (0,6144):
            with self.subTest(offset=offset),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);image,report,record,files=self.fixture(root)
                raw=bytearray(image.read_bytes());raw[offset]=0;image.write_bytes(raw)
                record['candidate_sha256']=hashlib.sha256(raw).hexdigest();report.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,'non-message file'):self.check(root,image,report,files)


if __name__=='__main__':unittest.main()
