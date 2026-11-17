import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import frame_rate_codegen as fps

class FrameRateCodegen(unittest.TestCase):
    def test_original_instruction_and_movie_restore_are_required(self):
        lines=['void synthetic(void) {','  L_08cb3d20: ;',
            'sr_begin(s, 0x08cb3ddcu, 0x00000000u); (void)0; sr_end(s, 0u, 0);','}']
        result='\n'.join(fps.rewrite(lines,0x08cb3cc4))
        self.assertIn('loa_fps_movie_restore()',result)
        self.assertIn('loa_fps_update(s, s->r[16], MEM_R32',result)
        self.assertIn('sr_fpu_div_s',result)
        with self.assertRaises(ValueError):fps.rewrite([l.replace('0x00000000u','0x00000001u') for l in lines],0x08cb3cc4)
        with self.assertRaises(ValueError):fps.rewrite(lines+lines,0x08cb3cc4)

    def test_original_condition_is_preserved_when_disabled(self):
        lines=['void synthetic(void) {','    { uint32_t _c = (s->r[4] != 0u);',
            '      sr_begin(s, 0x08cb3f8cu, 0x1480000au); sr_end(s, 0u, 0);','}']
        result='\n'.join(fps.rewrite(lines,0x08cb3f3c))
        self.assertIn('(s->r[4] != 0u) && !(loa_fps_enabled()',result)
        other=['unchanged'];self.assertIs(fps.rewrite(other,0x08804000),other)
