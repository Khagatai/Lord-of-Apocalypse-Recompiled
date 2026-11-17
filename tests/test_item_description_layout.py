import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from mes_codec import GlyphTable,Message,Bundle
from mes_tokens import message_template
from mes_edits import apply_edits,digest
from item_description_layout import wrap,width,replace

class ItemLayout(unittest.TestCase):
    def setUp(self):self.table=GlyphTable(tuple(range(32,127))+(0x2606,))
    def message(self,text):return Message((0xffff,0,0,0),(self.table.encode(text)+(0xffff,),))
    def test_wrap_retains_words_and_allocates_real_lines(self):
        m=self.message('A narrow sword made of volcanic glass and bone.')
        lines=wrap(message_template(m,self.table)[0]);n=replace(m,lines,self.table)
        self.assertEqual(n.header[1],len(lines)-1)
        self.assertGreater(len(n.lines),1)
        self.assertEqual(' '.join(lines),'A narrow sword made of volcanic glass and bone.')
    def test_colour_operands_and_full_width_rating_are_preserved(self):
        words=(0xfffa,92,92,132)+self.table.encode('A sword')+(0xfff9,)+self.table.encode(' ☆☆☆☆☆')+(0xffff,)
        m=Message((0xffff,0,0,0),(words,));lines=wrap(message_template(m,self.table)[0]);n=replace(m,lines,self.table)
        self.assertEqual(message_template(m,self.table)[1],message_template(n,self.table)[1])
        self.assertEqual(width('☆☆☆☆☆'),60)
    def test_loss_clipping_and_unknown_command_are_rejected(self):
        m=self.message('A sword of volcanic glass.')
        for lines in (['A sword.'],['A'*26],['A']*6):
            with self.assertRaises(ValueError):replace(m,lines,self.table)
        with self.assertRaises(ValueError):replace(Message((0xffff,0,0,0),((0xfff4,1,0xffff),)),['<cmd:0>'],self.table)
    def test_aliases_and_unrelated_resources_cannot_be_changed(self):
        m=self.message('A narrow sword made of volcanic glass and bone.');raw=m.build();source=Bundle(1,(0,1,0),b'',(raw,raw)).build()
        entry=dict(message_index=0,before_sha256=digest(raw),original_lines=message_template(m,self.table)[0],english_lines=wrap(message_template(m,self.table)[0]),item_panel_layout=True)
        manifest=dict(resource_id='000410e8',source_bundle_sha256=digest(source),entries=[entry]);out=Bundle.parse(apply_edits(source,self.table,manifest))
        self.assertEqual(out.offsets,(0,1,0));self.assertEqual(out.blocks[1],raw)
        manifest['resource_id']='000410cc'
        with self.assertRaises(ValueError):apply_edits(source,self.table,manifest)
    def test_wrong_header_requires_measurement(self):
        with self.assertRaises(ValueError):replace(Message((0xff,0,0,0),(self.table.encode('Sword')+(0xffff,),)),['Sword'],self.table)
    def test_concise_wording_cannot_drop_ratings_or_quantities(self):
        for old,new in [('Restores 20 HP','Restores HP'),('Sword ☆☆☆','Sword ☆☆')]:
            with self.assertRaises(ValueError):replace(self.message(old),[new],self.table,preserve_words=False)
    def test_colour_spacing_does_not_consume_phantom_columns(self):
        text='A <cmd:0> <cmd:1> sword'
        self.assertEqual(wrap([text]),['A <cmd:0><cmd:1>sword'])
    def test_full_width_quantity_can_be_localized_but_not_changed(self):
        table=GlyphTable(tuple(range(32,127))+(0xff11,))
        source=Message((0xffff,0,0,0),(table.encode('Chapter １')+(0xffff,),))
        replace(source,['Chapter 1'],table,preserve_words=False)
        with self.assertRaises(ValueError):replace(source,['Chapter 2'],table,preserve_words=False)

if __name__=='__main__':unittest.main()
