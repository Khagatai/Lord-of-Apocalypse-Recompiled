"""Split captions retain a common horizontal scale across their atlas cells."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.name=='nt','Windows local font renderer')
class CaptionAtlas(unittest.TestCase):
    def test_shared_scale_and_ink_stay_inside_cells(self):
        with tempfile.TemporaryDirectory(prefix='caption-test-',dir=ROOT/'private') as folder:
            root=Path(folder);plan=root/'spec.json'
            plan.write_text(json.dumps(dict(width=128,height=32,blocks=[
                dict(x=2,y=2,width=28,height=24,text='WIDE',fit_group='name'),
                dict(x=34,y=2,width=28,height=24,text='I',fit_group='name')
            ])))
            run=subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/render-caption-atlas.ps1'),
                                '-Spec',str(plan),'-Output',str(root/'rendered')],capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads((root/'rendered/render.json').read_text(encoding='utf-8-sig'))
            cells=report['cells']
            self.assertAlmostEqual(cells[0]['horizontal_ratio'],cells[1]['horizontal_ratio'])
            self.assertLess(cells[0]['horizontal_ratio'],1.)
            pixels=(root/'rendered/pixels.rgba').read_bytes()
            for y in range(32):
                for x in range(128):
                    if pixels[(y*128+x)*4+3]:
                        self.assertTrue(1<=y<=27 and (1<=x<=31 or 33<=x<=63))

if __name__=='__main__':unittest.main()
