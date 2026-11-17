"""Prove text-only reconstruction of the current WIP MES directly from Japanese."""
import argparse,collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mes_codec import GlyphTable
from rgf_archive import parse_index,resources
from message_recipe import export_bundle,sha

def read(folder):
    result={};glyphs=set();counts=collections.Counter()
    with (folder/'REGFILE.RZP').open('rb') as stream:
        for group,identity,raw in resources(stream,parse_index((folder/'REGFILE.RZL').read_bytes(),(folder/'REGFILE.RZP').stat().st_size)):
            occurrence=counts[group,identity];counts[group,identity]+=1
            if identity>>16==4:result[group,identity,occurrence]=raw
            if identity==0x50d78:glyphs.add(raw)
    if len(glyphs)!=1:raise ValueError('Ambiguous glyph tables')
    return result,glyphs.pop()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'private/local-build/japanese-messages.json');args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private'):raise ValueError('Keep translated game text private')
    before,glyph=read(ROOT/'private/translation/archives/japanese');after,target_glyph=read(ROOT/'private/translation/text-pass-16-archives')
    if glyph!=target_glyph or set(before)!=set(after):raise ValueError('Original glyph table or resource topology changed')
    table=GlyphTable.parse(glyph);recipes=[];failures=[]
    for key,source in before.items():
        target=after[key]
        if target==source:continue
        try:recipes.append(dict(group_index=key[0],occurrence=key[2],**export_bundle(source,target,table,key[1])))
        except ValueError as error:failures.append(dict(group_index=key[0],resource_id=f'{key[1]:08x}',occurrence=key[2],reason=str(error)))
    result=dict(schema=1,scope='English text-only recipes directly from original Japanese; no upstream patched ISO required',
        status='PASS' if not failures else 'INCOMPLETE',glyph_table_sha256=sha(glyph),bundles=recipes,failures=failures,
        verified_message_blocks=sum(len(row['entries']) for row in recipes),all_changed_MES_reconstructed=not failures,archives_created=False)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('bundles','failures')},indent=2))
    print('Unresolved bundle occurrences:',len(failures))
if __name__=='__main__':main()
