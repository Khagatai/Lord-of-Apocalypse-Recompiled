import copy,hashlib,importlib.util,json,os,struct,sys,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import hd_checkpoint_cache as cache
import local_player_setup as setup

def write(path,value):path.write_text(json.dumps(value))
def png(colour=(10,20,30,255)):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',4,4,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(colour)*4)*4))+chunk(b'IEND',b'')

class CheckpointReuse(unittest.TestCase):
    def fixture(self,root):
        pack=root/'pack';work=root/'work';pack.mkdir();(work/'completed').mkdir(parents=True)
        jobs={}
        for i in range(2):
            job=dict(dimensions=[[1,1]],source_rgba_sha256=[hashlib.sha256(bytes((10+i,20,30,255))).hexdigest()],
                wrap=0,method='scale',model=None,detail_pass=None,
                reference=dict(resource_id=f'{0x20000+i:08x}',source_sha256='a'*64,texture_index=0,name='synthetic'))
            jobs[cache.job_id(job)]=job
        recipe=dict(schema=1,game_pixels_included=False,archive_sha256='new archive',index_sha256='new index',jobs=jobs)
        identity=dict(tool='ISO-local-HD-v1',recipe_sha256='new recipe',archive_sha256='new archive',
            framework_commit='pin',processing_sources={'pipeline':'current'},model_pins={})
        previous=dict(identity,archive_sha256='old archive',recipe_sha256='old recipe',processing_sources={'pipeline':'legacy'})
        for folder in (pack,work):write(folder/'owner.json',previous)
        for i,(key,job) in enumerate(jobs.items()):
            name=f'tex-{i:05d}-0.png';(pack/name).write_bytes(png((10+i,20,30,255)))
            write(work/'completed'/(key+'.json'),dict(job=key,levels=[dict(file=name,width=4,height=4,sha256=cache.sha(pack/name))]))
        compatibility=dict(schema=1,legacy_processing_sources=[previous['processing_sources']])
        return recipe,pack,work,identity,compatibility

    def analyze(self,f):return cache.analyze(*f)
    def reconcile(self,f):return cache.reconcile(*f)

    def test_archive_key_and_reference_changes_reuse_bytes_without_copying(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,identity,compat=f
            before={p.name:(p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_ino) for p in pack.glob('*.png')}
            for job in recipe['jobs'].values():job['reference']['resource_id']='00029999'
            plan=self.reconcile(f)
            self.assertEqual((plan['reused_jobs'],plan['pending_jobs'],plan['pixel_files_copied']),(2,0,0))
            self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_ino) for p in pack.glob('*.png')})
            self.assertEqual(cache.load(pack/'owner.json'),identity)
            self.assertEqual(self.reconcile(f)['reused_jobs'],2)

    def test_one_changed_pixel_job_keeps_other_and_leaves_pixels_until_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,*_=f
            old=next(iter(recipe['jobs']));changed=recipe['jobs'].pop(old);changed['source_rgba_sha256']=['b'*64]
            recipe['jobs'][cache.job_id(changed)]=changed
            plan=self.reconcile(f)
            self.assertEqual((plan['reused_jobs'],plan['pending_jobs']),(1,1))
            self.assertTrue((work/'retired-completed'/(old+'.json')).exists())
            self.assertEqual(len(list(pack.glob('*.png'))),2)

    def test_missing_or_damaged_image_only_invalidates_its_jobs(self):
        for mode in ('missing','damaged','dimensions','metadata'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                f=self.fixture(Path(tmp));recipe,pack,work,*_=f
                record=next((work/'completed').glob('*.json'));row=cache.load(record);image=pack/row['levels'][0]['file']
                if mode=='missing':image.unlink()
                elif mode=='damaged':image.write_bytes(b'corrupted PNG')
                elif mode=='dimensions':row['levels'][0]['width']=8;write(record,row)
                else:record.write_text('{invalid')
                plan=self.reconcile(f)
                self.assertEqual((plan['reused_jobs'],plan['pending_jobs'],plan['repair_jobs']),(1,1,1))
                self.assertEqual(len(list((work/'completed').glob('*.json'))),1)

    def test_changed_canonical_input_cannot_keep_old_job_identifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,identity,*_=f
            next(iter(recipe['jobs'].values()))['wrap']=1
            before=(pack/'owner.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'job identity'):self.reconcile(f)
            self.assertEqual((pack/'owner.json').read_bytes(),before)

    def test_unknown_pixel_option_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError,'Unknown HD pixel'):
            cache.job_id(dict(new_pixel_option=True))

    def test_unreviewed_pipeline_invalidates_jobs_without_deleting_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,identity,compat=f;compat['legacy_processing_sources']=[]
            result=self.reconcile(f)
            self.assertEqual((result['reused_jobs'],result['pending_jobs']),(0,2))
            self.assertEqual(len(list(pack.glob('*.png'))),2)

    def test_model_change_only_invalidates_jobs_using_that_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,identity,compat=f
            old=next(iter(recipe['jobs']));job=recipe['jobs'].pop(old);job.update(method='restore',model='realesrgan-x4plus')
            key=cache.job_id(job);recipe['jobs'][key]=job
            record=work/'completed'/(old+'.json');row=cache.load(record);row['job']=key;record.unlink();write(work/'completed'/(key+'.json'),row)
            names=('realesrgan-ncnn-vulkan.exe','vcomp140.dll','vcomp140d.dll','models/realesrgan-x4plus.param','models/realesrgan-x4plus.bin')
            identity['model_pins']={name:'new' for name in names}
            self.assertEqual((self.reconcile(f)['reused_jobs'],len(list(pack.glob('*.png')))),(1,2))

    def test_unknown_owner_does_not_modify_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,*_=f;write(pack/'owner.json',dict(tool='user files'))
            with self.assertRaisesRegex(ValueError,'Unknown HD cache owner'):self.reconcile(f)
            self.assertEqual(len(list((work/'completed').glob('*.json'))),2)

    def test_path_traversal_is_rejected_before_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,*_=f;record=next((work/'completed').glob('*.json'))
            row=cache.load(record);row['levels'][0]['file']='../outside.png';write(record,row)
            before=(pack/'owner.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'Unsafe HD checkpoint filename'):self.reconcile(f)
            self.assertEqual((pack/'owner.json').read_bytes(),before)

    def test_interrupted_owner_promotion_can_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,identity,*_=f;real_write=cache.write
            def interrupted(path,value):
                if path==work/'owner.json':raise RuntimeError('cancelled')
                real_write(path,value)
            with patch.object(cache,'write',side_effect=interrupted):
                with self.assertRaisesRegex(RuntimeError,'cancelled'):self.reconcile(f)
            self.assertEqual(cache.load(work/'cache-transition.json')['state'],'PREPARED')
            self.assertEqual(self.reconcile(f)['reused_jobs'],2)
            self.assertEqual(cache.load(work/'cache-transition.json')['state'],'DONE')

    def test_first_build_has_no_cached_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=self.fixture(root);recipe,pack,work,identity,compat=f
            plan=cache.reconcile(recipe,root/'new-pack',root/'new-work',identity,compat)
            self.assertEqual((plan['reused_jobs'],plan['pending_jobs']),(0,2))

    def test_linked_image_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));recipe,pack,work,*_=f;image=next(pack.glob('*.png'));outside=Path(tmp)/'original.png'
            image.replace(outside)
            try:image.symlink_to(outside)
            except OSError:self.skipTest('Symlink creation unavailable')
            with self.assertRaisesRegex(ValueError,'Linked/escaping'):self.reconcile(f)
            self.assertEqual(outside.read_bytes(),png())

    def test_setup_does_not_reset_hd_for_changed_archive_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(setup,'ROOT',Path(tmp)):
            root=Path(tmp);work=root/'private/local-build';english=root/'private/translation/text-pass-16-image';english.mkdir(parents=True)
            rendered=work/'English-rendered';rendered.mkdir(parents=True);write(rendered/'result.json',dict(platform_rasterization_variants=[]))
            for name in ('REGFILE.RZP','REGFILE.RZL'):(english/name).write_bytes(b'new archive')
            recipe=root/'private/distribution/recipes/HD.json';recipe.parent.mkdir(parents=True)
            write(recipe,dict(archive_sha256=setup.sha(english/'REGFILE.RZP'),index_sha256=setup.sha(english/'REGFILE.RZL')))
            result=work/'HD-work/result.json';result.parent.mkdir();write(result,dict(state='HD_GENERATED'))
            with patch.object(setup,'run') as run,patch.object(setup,'reset_cache',side_effect=AssertionError('Do not erase HD')):
                setup.prepare_hd({'HD':{'path':recipe.relative_to(root).as_posix()}},work,{'HD':'changed'})
            self.assertTrue(any(c.args[0]=='build-local-hd-pack.py' for c in run.call_args_list))

class BuilderReuse(unittest.TestCase):
    def fixture(self,root):
        private=root/'private';private.mkdir()
        recipe,pack,work,identity,compat=CheckpointReuse().fixture(private)
        spec=importlib.util.spec_from_file_location('content_cache_builder',ROOT/'tools/build-local-hd-pack.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        identity['framework_commit']=builder.title.CONFIG['runtime']['commit']
        for folder in (pack,work):
            own=cache.load(folder/'owner.json');own['framework_commit']=identity['framework_commit'];write(folder/'owner.json',own)
        raw=[b'abc',b'DEF'];packed=zlib.compress(b''.join(raw))+bytes(4)
        index=struct.pack('<7I',0x31464752,0x10001,2,24,28,60,28)
        index+=struct.pack('<8I',2,0,len(packed),6,3,0x20000,3,0x20001)
        archives=private/'archives';archives.mkdir();(archives/'REGFILE.RZL').write_bytes(index);(archives/'REGFILE.RZP').write_bytes(packed)
        for i,job in enumerate(recipe['jobs'].values()):job['reference']['source_sha256']=hashlib.sha256(raw[i]).hexdigest()
        recipe.update(archive_sha256=cache.sha(archives/'REGFILE.RZP'),index_sha256=cache.sha(archives/'REGFILE.RZL'),
            groups=[dict(key=f'{i+1:024x}',job=key) for i,key in enumerate(recipe['jobs'])])
        path=private/'recipe.json';write(path,recipe)
        (root/'config').mkdir();write(root/'config/hd-compatible-pipelines.json',compat)
        (root/'tools').mkdir();(root/'tools/inventory-textures.py').write_bytes((ROOT/'tools/inventory-textures.py').read_bytes())
        return builder,recipe,pack,work,archives,path,identity

    def build(self,f):
        builder,recipe,pack,work,archives,path,identity=f
        verify=builder.texture_pack.verify_sample
        with (patch.object(builder,'ROOT',path.parent.parent),
              patch.object(builder.hd_work,'processing_sources',return_value=identity['processing_sources']),
              patch.object(builder.texture_pack,'verify_sample',side_effect=lambda folder:verify(folder,private_root=path.parent)),
              patch.object(builder.neural_texture,'verify_tool',return_value={'files':{}})):
            return builder.build(archives,path,pack,work)

    def test_fully_reused_pack_updates_mapping_without_native_or_neural_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));builder,recipe,pack,work,*_=f
            before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in pack.glob('*.png')}
            with patch.object(builder.hd_native,'Native',side_effect=AssertionError('No image processing needed')):
                result=self.build(f)
            self.assertEqual((result['state'],result['reused_jobs'],result['generated_jobs'],result['inference_launches']),('HD_GENERATED',2,0,0))
            self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in pack.glob('*.png')})
            self.assertEqual(len(cache.load(pack/'sample.json')['textures']),2)

    @unittest.skipUnless(os.name=='nt','Windows image helper')
    def test_only_missing_job_runs_real_scaler(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));builder,recipe,pack,work,*_=f
            records=sorted((work/'completed').glob('*.json'));lost=cache.load(records[0]);records[0].unlink()
            survivor=cache.load(records[1]);image=pack/survivor['levels'][0]['file'];before=(image.read_bytes(),image.stat().st_mtime_ns)
            job=recipe['jobs'][lost['job']];pixel=bytes.fromhex('0a141eff') if job['reference']['resource_id']=='00020000' else bytes.fromhex('0b141eff')
            parsed=SimpleNamespace(textures=[SimpleNamespace(name='synthetic')],preview_mip=lambda *a,**k:(1,1,pixel))
            with patch.object(builder.Xet,'parse',return_value=parsed):result=self.build(f)
            self.assertEqual((result['reused_jobs'],result['generated_jobs'],result['inference_launches']),(1,1,0))
            self.assertEqual((image.read_bytes(),image.stat().st_mtime_ns),before)

if __name__=='__main__':unittest.main()
