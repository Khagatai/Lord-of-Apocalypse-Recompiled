import hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import hd_recipe_migration as migration
s=importlib.util.spec_from_file_location('migration_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(s);s.loader.exec_module(png)

class RecipeMigration(unittest.TestCase):
    def fixture(self,root):
        pack=root/'pack';work=root/'work';pack.mkdir();(work/'completed').mkdir(parents=True)
        job=dict(dimensions=[[1,1]],source_rgba_sha256=['source'],wrap=0,method='scale',model=None,detail_pass=None)
        old=dict(schema=1,game_pixels_included=False,archive_sha256='archive',index_sha256='index',jobs={'shared':job,'retired':job})
        new=dict(old,jobs={'shared':dict(job),'added':dict(job,detail_pass='detail')})
        a=root/'old.json';b=root/'new.json';a.write_text(json.dumps(old));b.write_text(json.dumps(new))
        owner=dict(tool='ISO-local-HD-v1',recipe_sha256=migration.sha(a),archive_sha256='archive',framework_commit='pin',model_pins={'model':'hash'},processing_sources={'pipeline':'known'})
        for folder in (pack,work):(folder/'owner.json').write_text(json.dumps(owner))
        for i,name in enumerate(('shared','retired')):
            file=f'tex-{i:05}-0.png';raw=png.png(4,4,bytes((10+i,20,30,255))*16);(pack/file).write_bytes(raw)
            row=dict(job=name,levels=[dict(file=file,width=4,height=4,sha256=hashlib.sha256(raw).hexdigest())])
            (work/'completed'/(name+'.json')).write_text(json.dumps(row))
        return a,b,pack,work,owner
    def run_migration(self,fixture):
        a,b,pack,work,owner=fixture
        return migration.rebind(a,b,pack,work,'pin',owner['model_pins'],[owner['processing_sources']])
    def test_reuses_verified_jobs_retires_metadata_without_copying_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));result=self.run_migration(f);a,b,pack,work,owner=f
            self.assertEqual(result['retained_completed_jobs'],1);self.assertEqual(result['newly_required_jobs'],1)
            self.assertTrue((work/'retired-completed/retired.json').exists())
            self.assertTrue((pack/'tex-00001-0.png').exists());self.assertEqual(result['pixel_files_copied'],0)
            self.assertEqual(json.loads((pack/'owner.json').read_text())['recipe_sha256'],migration.sha(b))
    def test_corrupt_png_does_not_promote_or_remove_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=self.fixture(Path(tmp));a,b,pack,work,owner=f;(pack/'tex-00000-0.png').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'PNG changed'):self.run_migration(f)
            self.assertEqual(json.loads((pack/'owner.json').read_text()),owner)
            self.assertTrue((work/'completed/retired.json').exists())
    def test_changed_archive_or_shared_processing_is_rejected(self):
        for change in ('archive','processing'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                f=self.fixture(Path(tmp));a,b,pack,work,owner=f;new=json.loads(b.read_text())
                if change=='archive':new['archive_sha256']='other'
                else:new['jobs']['shared']['wrap']=1
                b.write_text(json.dumps(new))
                with self.assertRaises(ValueError):self.run_migration(f)
                self.assertEqual(json.loads((pack/'owner.json').read_text()),owner)
    def test_unknown_pipeline_cannot_adopt_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b,pack,work,owner=self.fixture(Path(tmp));bad=dict(owner,processing_sources={'other':'unknown'})
            (pack/'owner.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'checkpoint owner'):migration.rebind(a,b,pack,work,'pin',owner['model_pins'],[owner['processing_sources']])

if __name__=='__main__':unittest.main()
