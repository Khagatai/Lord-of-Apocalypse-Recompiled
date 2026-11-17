import io,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from iso_archive import ReadonlyExtent

class ArchiveExtent(unittest.TestCase):
    def test_reads_cannot_escape_selected_archive(self):
        stream=io.BytesIO(b'outsideABCDoutside');view=ReadonlyExtent(stream,7,4)
        self.assertEqual(view.read(100),b'ABCD');self.assertEqual(view.read(),b'')
        self.assertEqual(view.seek(-2,2),2);self.assertEqual(view.read(),b'CD')
        self.assertEqual(view.seek(0),0);self.assertEqual(view.read(1),b'A')
    def test_out_of_bounds_and_unknown_seek_are_rejected(self):
        view=ReadonlyExtent(io.BytesIO(b'ABCD'),0,4)
        for offset,whence in [(-1,0),(5,0),(1,2),(0,99)]:
            with self.assertRaises(ValueError):view.seek(offset,whence)
    def test_truncation_is_an_error(self):
        with self.assertRaisesRegex(ValueError,'Truncated'):ReadonlyExtent(io.BytesIO(b'AB'),0,4).read()

if __name__=='__main__':unittest.main()
