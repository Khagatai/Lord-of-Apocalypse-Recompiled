import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import archive_identity as identity


class ArchiveIdentityTests(unittest.TestCase):
    def test_identical_prefix_can_share_longer_authored_chain(self):
        short=((8,8,'a'),)
        long=short+((4,4,'b'),(2,2,'c'))
        self.assertEqual(identity.longest_compatible([long,short]),long)
        group=dict(source_width=8,source_height=8,levels=[{}, {}, {}],source_rgba_sha256=['a','b','c'])
        self.assertTrue(identity.supplies(group,short))
        self.assertTrue(identity.supplies(group,long))
        group['levels']=[{}]
        self.assertFalse(identity.supplies(group,long))

    def test_differing_base_or_overlapping_mip_is_still_refused(self):
        a=((8,8,'a'),(4,4,'b'))
        for b in (((8,8,'z'),),((8,8,'a'),(4,4,'z')),((16,8,'a'),)):
            self.assertIsNone(identity.longest_compatible([a,b]))
        self.assertIsNone(identity.longest_compatible([a,None]))

    def test_missing_or_changed_source_cannot_supply_chain(self):
        sig=((8,8,'a'),(4,4,'b'))
        group=dict(source_width=8,source_height=8,levels=[{},{}],source_rgba_sha256=['a','z'])
        self.assertFalse(identity.supplies(group,sig))
        group['source_width']=16
        self.assertFalse(identity.supplies(group,sig[:1]))
