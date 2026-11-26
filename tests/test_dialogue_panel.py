import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mes_codec import GlyphTable,Message
from mes_tokens import message_template,replace_message
from text_panel_layout import measurements

class DialoguePanel(unittest.TestCase):
    def test_item_and_quantity_substitutions_are_budgeted_with_original_colours(self):
        config=json.loads((ROOT/'config/dialogue-panel-wording.json').read_text())
        table=GlyphTable(tuple(range(128)))
        for slot,lines in config['entries'].items():
            words=(0xefe0,0) if slot=='41' else (0xefe0,0,0xfffa,100,255,100,0xefe1,0,0xfff9)
            original=Message((0xffff,2,0,0),(words+(0xfffe,),(0xfffe,),(0xffff,)))
            target=replace_message(original,lines,table)
            self.assertEqual(message_template(target,table)[1],message_template(original,table)[1])
            _,advances,uncertain=measurements(target,table,config['runtime_command_widths'])
            self.assertFalse(uncertain);self.assertLessEqual(max(advances),config['width'],slot)
            self.assertEqual(target.header,original.header)

    def test_other_runtime_operands_are_not_silently_assigned_a_width(self):
        table=GlyphTable(tuple(range(128)))
        original=Message((0xffff,0,0,0),((0xefe0,1,0xffff),))
        _,_,uncertain=measurements(original,table,{'efe0:0000':282})
        self.assertEqual(uncertain,['efe0'])

if __name__=='__main__':unittest.main()
