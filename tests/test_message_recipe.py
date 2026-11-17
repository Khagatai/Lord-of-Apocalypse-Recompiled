import hashlib,importlib.util,json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mes_codec import GlyphTable,Message,Bundle
from message_recipe import export_message,reconstruct_message,export_bundle,reconstruct_bundle

class MessageRecipe(unittest.TestCase):
    def setUp(self):self.table=GlyphTable(tuple(range(128)))
    def message(self,text):return Message((0xffff,0,0,0),(self.table.encode(text)+(0xffff,),))
    def test_text_recipe_round_trip_contains_no_original_text(self):
        before=self.message('old original');after=self.message('New English')
        recipe=export_message(before.build(),after.build(),self.table,0x40001)
        self.assertEqual(reconstruct_message(before.build(),recipe,self.table,0x40001).build(),after.build())
        self.assertNotIn('old original',json.dumps(recipe));self.assertNotIn('raw',recipe)
    def test_source_identity_is_required(self):
        before=self.message('original');after=self.message('English');recipe=export_message(before.build(),after.build(),self.table,0x40001)
        with self.assertRaisesRegex(ValueError,'Original message hash'):reconstruct_message(self.message('changed').build(),recipe,self.table,0x40001)
    def test_unknown_command_stream_changes_are_rejected(self):
        before=Message((0xffff,0,0,0),((0xfff4,1,*self.table.encode('old'),0xffff),))
        after=Message((0xffff,0,0,0),((0xfff4,2,*self.table.encode('new'),0xffff),))
        with self.assertRaises(ValueError):export_message(before.build(),after.build(),self.table,0x40001)
    def test_explicit_colour_formatting_keeps_significant_commands(self):
        before=Message((0xffff,0,0,0),((0xfffa,255,0,0,0xfff4,1,*self.table.encode('old'),0xffff),))
        after=Message((0xffff,0,0,0),((0xfffa,0,255,0,*self.table.encode('new'),0xfff4,1,0xfff9,0xffff),))
        recipe=export_message(before.build(),after.build(),self.table,0x40001)
        self.assertEqual(recipe['kind'],'formatted')
        self.assertEqual(reconstruct_message(before.build(),recipe,self.table,0x40001).build(),after.build())
    def test_duplicate_glyph_and_zero_padding_are_reproduced(self):
        table=GlyphTable(tuple(range(128))+(ord('A'),))
        before=Message((0xffff,0,0,0),((ord('B'),0xffff),),(0,))
        after=Message((0xffff,0,0,0),((128,0xffff),))
        recipe=export_message(before.build(),after.build(),table,0x40001)
        self.assertEqual(recipe['glyph_choices'],[dict(line=0,position=0,glyph=128)])
        self.assertEqual(reconstruct_message(before.build(),recipe,table,0x40001).build(),after.build())
        recipe['glyph_choices'][0]['glyph']=ord('C')
        with self.assertRaisesRegex(ValueError,'changes translated character'):reconstruct_message(before.build(),recipe,table,0x40001)
    def test_aliases_are_preserved(self):
        before=self.message('original');after=self.message('English')
        source=Bundle(1,(0,0),b'',(before.build(),)).build();target=Bundle(1,(0,0),b'',(after.build(),)).build()
        recipe=export_bundle(source,target,self.table,0x40001)
        self.assertEqual(len(recipe['entries']),1)
        self.assertEqual(Bundle.parse(reconstruct_bundle(source,recipe,self.table)).offsets,(0,0))
    def test_item_reflow_stays_in_the_measured_resource(self):
        before=self.message('old words');after=Message((0xffff,1,0,0),(self.table.encode('New')+(0xfffe,),self.table.encode('words')+(0xffff,)))
        recipe=export_message(before.build(),after.build(),self.table,0x410e8)
        self.assertEqual(recipe['kind'],'item-layout')
        with self.assertRaises(ValueError):reconstruct_message(before.build(),recipe,self.table,0x40001)

class ReleaseGuard(unittest.TestCase):
    def test_uncleared_payload_cannot_replace_setup_by_default(self):
        spec=importlib.util.spec_from_file_location('setup_builder_guard',ROOT/'tools/build-online-setup.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);work=root/'private/distribution-test';work.mkdir(parents=True)
            (work/'github-assets-result.json').write_text(json.dumps(dict(public_distribution_review_complete=False)))
            output=root/'Setup.exe';output.write_bytes(b'keep existing installer')
            with patch.object(builder,'ROOT',root),patch.object(sys,'argv',['build-online-setup.py','--output',str(output)]):
                with self.assertRaisesRegex(RuntimeError,'Release installer blocked'):builder.main()
            self.assertEqual(output.read_bytes(),b'keep existing installer')

if __name__=='__main__':unittest.main()
