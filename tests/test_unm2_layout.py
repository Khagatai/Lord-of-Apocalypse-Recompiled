import struct,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from unm2_layout import Sprite,caption_sprites,replace_caption_fields,measure_caption_lines

def fixture():
    data=bytearray(52+5*32+8);data[:4]=b'UNM2'
    struct.pack_into('<4H',data,4,5,5,2,3);struct.pack_into('<I',data,20,52)
    for i,(x,y,u) in enumerate(((0,0,0),(0,0,16),(10,20,0),(30,24,16),(50,20,0))):
        struct.pack_into('<2H2h2f4H2I',data,52+i*32,0,0,x,y,1.,1.,u,0,u+16,16,0xffffffff,32)
    data[-8:]=b'animtail';return bytes(data)

class CaptionLayout(unittest.TestCase):
    def test_reused_glyphs_keep_their_prototype_and_align_positions(self):
        source=fixture();self.assertEqual(len(caption_sprites(source,64,32)),3)
        edits=[dict(node=i,uv=(u,16,u+16,32),**({'position':(10+(i-2)*20,20)} if i>=2 else {})) for i,u in enumerate((0,16,0,16,0))]
        target=replace_caption_fields(source,64,32,edits)
        self.assertEqual([p.y for p in caption_sprites(target,64,32)],[20,20,20])
        self.assertEqual(target[-8:],b'animtail');self.assertEqual(target[:52],source[:52])
        for i in range(5):
            off=52+i*32
            self.assertEqual(target[off:off+4],source[off:off+4])
            self.assertEqual(target[off+8:off+16],source[off+8:off+16])
            self.assertEqual(target[off+24:off+32],source[off+24:off+32])

    def test_mismatched_prototype_and_unknown_flags_fail(self):
        with self.assertRaisesRegex(ValueError,'lost its prototype'):
            replace_caption_fields(fixture(),64,32,[dict(node=0,uv=(0,16,16,32))])
        data=bytearray(fixture());struct.pack_into('<I',data,52+2*32+28,99)
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            caption_sprites(data,64,32)

    def test_invalid_uv_and_duplicate_nodes_fail(self):
        for edits in ([dict(node=0,uv=(-1,0,16,16))], [dict(node=0,uv=(0,0,16,16))]*2):
            with self.assertRaises(ValueError):replace_caption_fields(fixture(),64,32,edits)

    def test_visible_ink_alignment_accounts_for_atlas_padding(self):
        pixels=bytearray(32*16*4)
        for left,top in ((2,1),(18,4)):
            for y in range(top,top+5):
                for x in range(left,left+4):pixels[(y*32+x)*4:(y*32+x)*4+4]=b'\xff'*4
        good=[Sprite(10,20,(0,0,16,16)),Sprite(20,17,(16,0,32,16))]
        result=measure_caption_lines(pixels,32,16,[good])
        self.assertEqual(result['lines'][0]['baseline_error_pixels'],0)
        self.assertEqual(result['lines'][0]['chunk_gaps'],[6])
        with self.assertRaisesRegex(ValueError,'baselines'):
            measure_caption_lines(pixels,32,16,[[good[0],Sprite(20,20,(16,0,32,16))]])
        with self.assertRaisesRegex(ValueError,'overlap'):
            measure_caption_lines(pixels,32,16,[[good[0],Sprite(11,17,(16,0,32,16))]])
        with self.assertRaisesRegex(ValueError,'canvas'):
            measure_caption_lines(pixels,32,16,[[Sprite(-5,20,(0,0,16,16))]])
        with self.assertRaisesRegex(ValueError,'too close'):
            measure_caption_lines(pixels,32,16,[good,good])
        shifted=[Sprite(p.x+5,p.y+12,p.uv) for p in good]
        with self.assertRaisesRegex(ValueError,'centres'):
            measure_caption_lines(pixels,32,16,[good,shifted])

if __name__=='__main__':unittest.main()
