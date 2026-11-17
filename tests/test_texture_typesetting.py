"""Local caption edits must preserve nearby artwork and refuse font shrinking."""
import importlib.util,json,os,subprocess,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.name=='nt','Windows local font renderer')
class Typesetting(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='typesetting-test-',dir=ROOT/'private')
        self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        spec=importlib.util.spec_from_file_location('caption_png',ROOT/'tools/inventory-textures.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        rgba=bytearray(bytes((100,100,100,255))*32*32)
        rgba[(5*32+5)*4:(5*32+5)*4+4]=bytes((255,254,192,255))
        self.source=self.root/'source.png';self.source.write_bytes(module.png(32,32,rgba))

    def render(self,block):
        plan=self.root/'spec.json';plan.write_text(json.dumps(dict(source_png=str(self.source.relative_to(ROOT)),blocks=[block])))
        return subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/render-texture-text.ps1'),
                               '-Spec',str(plan),'-Output',str(self.root/'rendered')],capture_output=True,text=True,timeout=20)

    def block(self):
        return dict(x=0,y=0,width=16,height=16,font_pixels=12,line_height=16,bold=True,
                    color='#FFFEC0',background='#000000',paragraphs=[''],fit_single_line=False)

    def test_yellow_caption_mask_retains_grey_illustration(self):
        block=self.block();block['erase_yellow_ink']=True
        run=self.render(block);self.assertEqual(run.returncode,0,run.stderr)
        pixels=(self.root/'rendered/pixels.rgba').read_bytes()
        def pixel(x,y):return pixels[(y*32+x)*4:(y*32+x)*4+4]
        self.assertEqual(pixel(5,5),bytes((0,0,0,255)))
        self.assertEqual(pixel(6,5),bytes((100,100,100,255)))
        self.assertEqual(pixel(20,5),bytes((100,100,100,255)))

    def test_fixed_size_rejects_crowded_label(self):
        block=self.block();block.update(width=8,paragraphs=['HI'],fit_single_line=True,preserve_font_size=True)
        run=self.render(block)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('shorter wording',run.stderr)
        self.assertFalse((self.root/'rendered').exists())

if __name__=='__main__':unittest.main()
