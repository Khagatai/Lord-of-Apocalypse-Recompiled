from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from neural_texture import pad_opaque,cutout_colours,masked_colours,merge_cutout_colours,processing_pins

class NeuralTextureTests(unittest.TestCase):
    def test_opposite_edges_supply_repeat_context_and_clamp_retains_edge(self):
        pixels=b''.join(bytes((n,0,0,255)) for n in (1,2,3,4))
        def red(data):return list(data[::4])
        self.assertEqual(red(pad_opaque(pixels,2,2,1,0)),[4,3,4,3,2,1,2,1,4,3,4,3,2,1,2,1])
        self.assertEqual(red(pad_opaque(pixels,2,2,1,257)),[1,1,2,2,1,1,2,2,3,3,4,4,3,3,4,4])
        for wrap in (0,1,256,257):
            padded=pad_opaque(pixels,2,2,3,wrap)
            self.assertEqual(padded[(3*8+3)*4:(3*8+5)*4],pixels[:8])
            self.assertEqual(padded[(4*8+3)*4:(4*8+5)*4],pixels[8:])

    def test_transparency_and_invalid_geometry_are_refused(self):
        with self.assertRaisesRegex(ValueError,'opaque'):
            pad_opaque(bytes((255,0,0,0)),1,1,1,0)
        for args in ((b'',1,1,1,0),(b'\xff'*4,1,1,129,0),(b'\xff'*4,1,1,1,2)):
            with self.assertRaisesRegex(ValueError,'geometry'):pad_opaque(*args)

    def test_cutout_visible_colours_preserved_and_wrap_changes_edge_context(self):
        raw=bytearray(8*4);raw[3*4:4*4]=bytes((255,0,0,255));raw[7*4:8*4]=bytes((0,0,255,255))
        clamped=cutout_colours(raw,8,1,257);repeated=cutout_colours(raw,8,1,256)
        self.assertEqual(clamped[:4],bytes((255,0,0,255)))
        self.assertEqual(repeated[:4],bytes((0,0,255,255)))
        for result in (clamped,repeated):
            self.assertEqual(result[12:16],raw[12:16]);self.assertEqual(result[28:32],raw[28:32])
            self.assertEqual(set(result[3::4]),{255})
        with self.assertRaisesRegex(ValueError,'binary alpha'):
            cutout_colours(bytes((0,0,0,100)),1,1,0)

    def test_cutout_alpha_and_invisible_rgb_are_exactly_preserved(self):
        baseline=bytes((10,20,30,0,20,30,40,64,30,40,50,255))
        restored=bytes((200,210,220,255))*3
        result=merge_cutout_colours(restored,baseline)
        self.assertEqual(result[3::4],baseline[3::4])
        self.assertEqual(result[:4],baseline[:4])
        self.assertEqual(result[4:7],restored[4:7]);self.assertEqual(result[8:11],restored[8:11])
        with self.assertRaisesRegex(ValueError,'extent'):
            merge_cutout_colours(restored[:-1],baseline)

    def test_masked_context_preserves_semitransparent_colours_without_creating_alpha(self):
        source=bytes((200,20,10,64,0,0,0,0,20,30,200,255))
        result=masked_colours(source,3,1,257)
        self.assertEqual(result[:3],source[:3]);self.assertEqual(result[-4:-1],source[-4:-1])
        self.assertEqual(set(result[3::4]),{255})
        with self.assertRaisesRegex(ValueError,'no visible'):
            masked_colours(bytes(4),1,1,0)

    def test_unused_model_pins_do_not_invalidate_an_identical_processing_profile(self):
        files={name:'a'*64 for name in ('realesrgan-ncnn-vulkan.exe','vcomp140.dll','vcomp140d.dll',
               'models/realesrgan-x4plus.param','models/realesrgan-x4plus.bin')}
        baseline={'release':'pinned release','files':files}
        extra={'release':'pinned release','files':dict(files,**{'models/realesrgan-x4plus-anime.bin':'b'*64})}
        self.assertEqual(processing_pins(baseline),processing_pins(extra))
        extra['files']['models/realesrgan-x4plus.bin']='c'*64
        self.assertNotEqual(processing_pins(baseline),processing_pins(extra))
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            processing_pins(baseline,'realesrgan-x4plus-anime')

if __name__=='__main__':unittest.main()
