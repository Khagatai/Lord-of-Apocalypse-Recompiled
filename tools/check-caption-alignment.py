"""Reconstruct private split-caption candidates and check their assembled ink."""
import argparse,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from rgf_archive import parse_index,resources
from texture_text import digest,reconstruct
from unm2_layout import Sprite,measure_caption_lines
from xet_codec import Xet

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--archives',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    private=(ROOT/'private').resolve();output=args.output.resolve()
    if not args.manifest.resolve().is_relative_to(private) or not output.is_relative_to(private) or output.exists():
        parser.error('Use a private manifest and a fresh private report path')
    rows=json.loads(args.manifest.read_text(encoding='utf-8-sig'))['resources']
    records={int(row['resource_id'],16):row for row in rows}
    if len(records)!=len(rows):raise ValueError('Duplicate resource identities')
    layouts=[row for row in rows if row.get('caption_layout') is True]
    if not layouts:raise ValueError('No caption layout records')
    wanted={int(row['resource_id'],16) for row in layouts}|{int(row['texture_resource_id'],16) for row in layouts}
    found={}
    groups=parse_index((args.archives/'REGFILE.RZL').read_bytes(),(args.archives/'REGFILE.RZP').stat().st_size)
    with (args.archives/'REGFILE.RZP').open('rb') as stream:
        for _,identity,raw in resources(stream,groups):
            if identity in wanted and digest(raw)==records[identity]['source_sha256']:
                found[identity]=raw
    if set(found)!=wanted:raise ValueError('Reviewed caption source variant missing')
    checked=[]
    for row in layouts:
        identity=int(row['resource_id'],16);texture_id=int(row['texture_resource_id'],16)
        layout=reconstruct(found[identity],row,private)
        texture=reconstruct(found[texture_id],records[texture_id],private)
        width,height,pixels=Xet.parse(texture).preview(row['texture_index'],1024)
        if [width,height]!=row['texture_size']:raise ValueError('Caption atlas dimensions differ')
        total,_,prototypes,_=struct.unpack_from('<4H',layout,4)
        sprites=[];seen=set()
        for indices in row['caption_rows']:
            line=[]
            for node in indices:
                if type(node) is not int or not prototypes<=node<total or node in seen:
                    raise ValueError('Invalid, repeated or non-instance caption node')
                seen.add(node)
                item=struct.unpack_from('<2H2h2f4H2I',layout,52+node*32)
                if item[4:6]!=(1.,1.):raise ValueError('Caption row includes hidden or transformed sprite')
                line.append(Sprite(item[2],item[3],item[6:10]))
            sprites.append(line)
        check=measure_caption_lines(pixels,width,height,sprites)
        checked.append(dict(layout_resource_id=row['resource_id'],texture_resource_id=row['texture_resource_id'],
                            layout_sha256=digest(layout),texture_sha256=digest(texture),**check))
    report=dict(scope='independent-static-caption-assembly',manifest_sha256=digest(args.manifest.read_bytes()),
                captions_verified=len(checked),lines_verified=sum(len(row['lines']) for row in checked),
                in_game_animation_validated=False,installed=False,captions=checked)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='captions'},indent=2))

if __name__=='__main__':main()
