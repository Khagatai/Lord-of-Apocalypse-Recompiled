import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import pack_update
import texture_pack


def sha(data):return hashlib.sha256(data).hexdigest()


def png(colour):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',2,2,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(colour)*2)*2))+chunk(b'IEND',b'')


class PackUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary=ROOT/'private/tmp';temporary.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=temporary)
        self.root=Path(self.temporary.name);self.pack=self.root/'working';self.pack.mkdir()
        self.old=self.group(0,(255,0,0,255));self.old_png=self.pack/self.old['levels'][0]['file']
        report,ini=self.report([self.old])
        (self.pack/'sample.json').write_text(json.dumps(report,indent=2)+'\n')
        (self.pack/'textures.ini').write_bytes(ini)
        self.before={name:(self.pack/name).read_bytes() for name in ('sample.json','textures.ini')}

    def tearDown(self):self.temporary.cleanup()

    def group(self,index,colour):
        name=f'tex-{index:05d}-0.png';data=png(colour);(self.pack/name).write_bytes(data)
        return dict(key=f'{index+1:024x}',source_width=1,source_height=1,factor=2,
                    levels=[dict(file=name,width=2,height=2,sha256=sha(data))])

    def report(self,groups):
        lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
        lines += [g['key']+'_0 = '+g['levels'][0]['file'] for g in groups]
        ini=('\n'.join(lines)+'\n').encode()
        report=dict(scope='verified-mip-texture-pack',textures=groups,ini_sha256=sha(ini),sampler_namespace=None)
        if (self.pack/'sample.json').exists():report['base_manifest_sha256']=sha((self.pack/'sample.json').read_bytes())
        return report,ini

    def test_success_reuses_existing_png_and_keeps_metadata_only_rollback(self):
        old_stat=self.old_png.stat();old_data=self.old_png.read_bytes()
        new=self.group(1,(0,255,0,255));report,ini=self.report([self.old,new])
        checked=pack_update.commit(self.pack,report,ini,self.root)
        self.assertEqual(checked['images'],2)
        self.assertEqual(self.old_png.read_bytes(),old_data)
        self.assertEqual((self.old_png.stat().st_ino,self.old_png.stat().st_mtime_ns),(old_stat.st_ino,old_stat.st_mtime_ns))
        rollback=self.pack/'.metadata-rollback'
        self.assertEqual({p.name for p in rollback.iterdir()},{'sample.json','textures.ini'})
        self.assertEqual((rollback/'sample.json').read_bytes(),self.before['sample.json'])
        self.assertEqual(texture_pack.verify_sample(self.pack,self.root)['images'],2)
        published_time=(self.pack/'sample.json').stat().st_mtime_ns
        pack_update.commit(self.pack,report,ini,self.root)
        self.assertEqual((self.pack/'sample.json').stat().st_mtime_ns,published_time)

    def test_bad_new_png_is_refused_before_active_metadata_changes(self):
        new=self.group(1,(0,255,0,255));report,ini=self.report([self.old,new])
        (self.pack/new['levels'][0]['file']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):pack_update.commit(self.pack,report,ini,self.root)
        self.assertEqual({n:(self.pack/n).read_bytes() for n in self.before},self.before)
        self.assertFalse((self.pack/'.metadata-rollback').exists())
        self.assertEqual(texture_pack.verify_sample(self.pack,self.root)['images'],1)

    def test_failed_manifest_promotion_restores_both_active_metadata_files(self):
        new=self.group(1,(0,255,0,255));report,ini=self.report([self.old,new]);replace=pack_update.os.replace
        def fail_manifest(source,destination):
            if Path(destination)==self.pack/'sample.json' and Path(source).name.startswith('.sample-'):
                raise OSError('simulated promotion failure')
            return replace(source,destination)
        with patch.object(pack_update.os,'replace',side_effect=fail_manifest):
            with self.assertRaisesRegex(OSError,'simulated'):pack_update.commit(self.pack,report,ini,self.root)
        self.assertEqual({n:(self.pack/n).read_bytes() for n in self.before},self.before)
        self.assertFalse(any(p.name.startswith(('.sample-','.textures-')) for p in self.pack.iterdir()))
        self.assertEqual(texture_pack.verify_sample(self.pack,self.root)['images'],1)

    def test_stale_baseline_is_refused(self):
        report,ini=self.report([self.old]);report['base_manifest_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'changed since'):pack_update.commit(self.pack,report,ini,self.root)
        self.assertEqual({n:(self.pack/n).read_bytes() for n in self.before},self.before)

    def test_unchanged_update_creates_no_snapshot_or_metadata_write(self):
        report=json.loads(self.before['sample.json']);before=(self.pack/'sample.json').stat().st_mtime_ns
        pack_update.commit(self.pack,report,self.before['textures.ini'],self.root)
        self.assertEqual((self.pack/'sample.json').stat().st_mtime_ns,before)
        self.assertFalse((self.pack/'.metadata-rollback').exists())


if __name__=='__main__':unittest.main()
