import hashlib,importlib.util,json,random,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import hd_native,hd_work,neural_texture,setup_resources,title
from text_render_worker import Renderer

def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Scheduling(unittest.TestCase):
    def test_compiler_workers_bound_cpu_and_ram(self):
        self.assertEqual(setup_resources.compiler_workers(64,64*1024**3),8)
        self.assertEqual(setup_resources.compiler_workers(1,64*1024**3),1)
        self.assertEqual(setup_resources.compiler_workers(32,3*1024**3),1)
        self.assertEqual(setup_resources.compiler_workers(8,10*1024**3),5)
    def test_byte_cache_lru_and_oversized_entries(self):
        c=hd_work.ByteCache(6)
        self.assertEqual(c.get('a',lambda:b'123'),b'123')
        self.assertEqual(c.get('a',lambda:self.fail('cached value decoded again')),b'123')
        c.get('b',lambda:b'456');c.get('c',lambda:b'789');self.assertNotIn('a',c.entries)
        c.get('large',lambda:b'x'*20);self.assertLessEqual(c.size,6);self.assertNotIn('large',c.entries)
    def test_pixel_cache_keeps_different_image_shapes_separate(self):
        a=hd_work.content_token(b'rgba',b'padded','model',None,64,128)
        b=hd_work.content_token(b'rgba',b'padded','model',None,128,64)
        self.assertNotEqual(a,b)
        self.assertEqual(a,hd_work.content_token(b'rgba',b'padded','model',None,64,128))
    def test_batches_cover_once_and_limit_memory(self):
        jobs={str(i):dict(method='restore',dimensions=[[256,256]]) for i in range(130)}
        groups=list(hd_work.batches(jobs,list(jobs),64,64*1024**2))
        self.assertEqual([i for group in groups for i in group],list(jobs))
        self.assertTrue(all(len(group)<=4 for group in groups))
    def test_resume_requires_known_pipeline_and_identical_inputs(self):
        builder=module('migration_test','build-local-hd-pack.py')
        old=dict(processing_sources={'old':'known'},archive_sha256='archive',recipe_sha256='recipe',framework_commit='pin',model_pins={'model':'hash'})
        new=dict(old,processing_sources={'new':'known'})
        compat=dict(schema=1,legacy_processing_sources=[old['processing_sources']])
        self.assertTrue(builder.compatible_owner(old,new,compat))
        for key in ('archive_sha256','recipe_sha256','framework_commit','model_pins'):
            changed=dict(old);changed[key]='different'
            self.assertFalse(builder.compatible_owner(changed,new,compat))
        self.assertFalse(builder.compatible_owner(dict(old,processing_sources={'unknown':'pipeline'}),new,compat))
    def test_only_unreferenced_generated_pngs_are_pruned(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack=Path(tmp);(pack/'owner.json').write_text('{}');(pack/'tex-00000-0.png').write_bytes(b'used')
            (pack/'tex-00001-0.png').write_bytes(b'orphan');(pack/'custom.png').write_bytes(b'preserve')
            removed=hd_work.prune_orphans(pack,{'tex-00000-0.png'})
            self.assertEqual([r['file'] for r in removed],['tex-00001-0.png'])
            self.assertTrue((pack/'tex-00000-0.png').exists());self.assertTrue((pack/'custom.png').exists())

@unittest.skipUnless(sys.platform=='win32','Windows native helpers')
class NativePixels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/'private/setup-optimisation';folder.mkdir(parents=True,exist_ok=True)
        cls.tmp=tempfile.TemporaryDirectory(prefix='synthetic-',dir=folder);cls.work=Path(cls.tmp.name)
        cls.png=module('synthetic_png','inventory-textures.py')
        cls.generator=module('legacy_helper_compile','build-local-hd-pack.py')
        cls.generator.compile_helpers(cls.work,title.environment());cls.native=hd_native.Native(cls.work)
    @classmethod
    def tearDownClass(cls):cls.native.close();cls.tmp.cleanup()
    def test_same_scaler_pixels_for_all_wraps_and_alpha(self):
        rng=random.Random(42)
        for w,h in ((1,1),(4,8),(16,16)):
            pixels=bytes(rng.randrange(256) for _ in range(w*h*4));source=self.work/'source.rgba';source.write_bytes(pixels)
            for wrap in (0,1,256,257):
                out=self.work/'baseline.rgba'
                subprocess.run([str(self.work/'scale.exe'),str(source),str(out),str(w),str(h),'4',str(wrap&1),str(wrap>>8)],env=title.environment(),check=True,capture_output=True)
                self.assertEqual(self.native.scale(pixels,w,h,wrap),out.read_bytes())
    def test_same_png_crop_and_detail_pixels_as_file_helpers(self):
        w,h=32,32;pixels=bytes((i*71+13)%256 for i in range(w*h*4));source=self.work/'image.png';source.write_bytes(self.png.png(w,h,pixels))
        out=self.work/'crop.rgba'
        subprocess.run([str(self.work/'decode.exe'),str(source),str(out),str(w),str(h),'4','3','16','12'],env=title.environment(),check=True,capture_output=True)
        self.assertEqual(self.native.crop(source.read_bytes(),w,h,4,3,16,12),out.read_bytes())
        subprocess.run([str(self.work/'sharpen.exe'),str(source),str(out)],env=title.environment(),check=True,capture_output=True)
        result=self.native.detail(pixels,w,h);self.assertEqual(result,out.read_bytes());self.assertEqual(result[3::4],pixels[3::4])
        with self.assertRaises(ValueError):self.native.crop(b'not PNG',32,32,0,0,16,16)
    def test_padding_and_mask_extension_match_python_for_every_wrap(self):
        for w,h in ((1,1),(4,8),(16,16)):
            for mode in ('opaque','binary','soft'):
                pixels=bytearray((i*71+13)%256 for i in range(w*h*4))
                for i in range(w*h):pixels[i*4+3]=255 if mode=='opaque' else (255 if i==0 else (0 if mode=='binary' else i%3*127))
                pixels=bytes(pixels)
                for wrap in (0,1,256,257):
                    expected=neural_texture.pad_opaque(neural_texture.masked_colours(pixels,w,h,wrap),w,h,64,wrap)
                    self.assertEqual(self.native.pad(pixels,w,h,wrap),expected)
        with self.assertRaises(ValueError):self.native.pad(bytes(16),2,2,0)
    def test_native_colour_merge_preserves_all_alpha_values_exactly(self):
        restored=bytearray((i*13+71)%256 for i in range(32*32*4));scaled=bytes((i*71+13)%256 for i in range(len(restored)))
        restored[3::4]=bytes([255])*(len(restored)//4);restored=bytes(restored)
        self.assertEqual(self.native.merge(restored,scaled),neural_texture.merge_cutout_colours(restored,scaled))
        bad=bytearray(restored);bad[3]=0
        with self.assertRaises(ValueError):self.native.merge(bytes(bad),scaled)
    def test_reused_text_worker_preserves_regions_and_reports_errors(self):
        source=self.work/'source.png';pixels=bytes((30,40,50,255))*64*32;source.write_bytes(self.png.png(64,32,pixels))
        plan=dict(source_png=source.relative_to(ROOT).as_posix(),blocks=[dict(x=4,y=4,width=56,height=20,paragraphs=['Hello'],line_height=12,font_pixels=10,color='#ffffff',background='#000000')])
        spec=self.work/'plan.json';spec.write_text(json.dumps(plan));process=None
        with Renderer(ROOT) as worker:
            for i in range(2):
                target=self.work/('text-'+str(i));worker.render('render-texture-text.ps1',spec,target)
                if process:self.assertEqual(worker.process.pid,process)
                process=worker.process.pid;rendered=(target/'pixels.rgba').read_bytes();self.assertEqual(len(rendered),len(pixels))
                self.assertEqual(rendered[:64*4*4],pixels[:64*4*4]);self.assertNotEqual(rendered,pixels)
            plan['blocks'][0]['width']=100;spec.write_text(json.dumps(plan))
            with self.assertRaisesRegex(RuntimeError,'exceeds image'):worker.render('render-texture-text.ps1',spec,self.work/'bad-text')

if __name__=='__main__':unittest.main()
