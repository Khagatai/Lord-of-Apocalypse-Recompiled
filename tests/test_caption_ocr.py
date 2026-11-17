import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from caption_ocr import caption_mask,read_rgba_png
spec=importlib.util.spec_from_file_location('ocr_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)

class CaptionOCR(unittest.TestCase):
    def test_owned_png_roundtrip_and_corrupt_chunks_refused(self):
        pixels=bytes((250,250,250,255,0,0,0,255));data=png.png(2,1,pixels)
        self.assertEqual(read_rgba_png(data),(2,1,pixels))
        bad=bytearray(data);bad[-5]^=1
        with self.assertRaises(ValueError):read_rgba_png(bad)

    def test_neutral_text_is_upscaled_and_coloured_background_suppressed(self):
        rgba=bytes((255,255,255,255,220,150,80,255,0,0,0,255))
        w,h,pixels=caption_mask(3,1,rgba,factor=2,padding=1)
        self.assertEqual((w,h),(8,4))
        self.assertEqual(bytes(pixels[8:16]),bytes((255,0,0,255,255,255,255,255)))
        self.assertEqual(pixels[:8],b'\xff'*8)

    def test_unoutlined_bright_background_is_not_treated_as_caption_ink(self):
        rgba=b'\xff'*9*9*4
        w,h,pixels=caption_mask(9,9,rgba,factor=1,padding=0,text_only=True)
        self.assertEqual(pixels,b'\xff'*81)
        rgba=bytearray(rgba);rgba[(4*9+5)*4:(4*9+5)*4+4]=bytes((0,0,0,255))
        w,h,pixels=caption_mask(9,9,rgba,factor=1,padding=0,text_only=True)
        self.assertEqual(pixels[4*9+4],0)

if __name__=='__main__':unittest.main()
