"""Export private text/timing/crop instructions, without movie or caption pixels."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'private/local-build/movie-caption-recipe.json');args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private'):raise ValueError('Keep translated text/private recipe under private')
    base=ROOT/'private/translation/movie-captions';raw=(base/'captions.bin').read_bytes()
    if raw[:8]!=b'LOACAP1\0':raise ValueError('Unknown active caption format')
    count,cues=struct.unpack_from('<2I',raw,8);table=16+144*count;rows=[struct.unpack_from('<8I',raw,table+32*i) for i in range(cues)]
    collection=json.loads((base/'collection.json').read_text())['movies']
    if len(collection)!=count:raise ValueError('Caption movie count changed')
    movies=[];position=0
    for movie,job in enumerate(collection):
        draft=json.loads((ROOT/job['draft']).read_text(encoding='utf-8'));items=[]
        header=raw[16+144*movie:16+144*(movie+1)]
        if hashlib.sha256(header).hexdigest()!=draft['header144_sha256']:raise ValueError('Movie header identity changed')
        for cue in draft['cues']:
            row=rows[position];position+=1
            if row[0]!=movie:raise ValueError('Caption movie order changed')
            _,first,end,x,y,w,h,offset=row;pixels=raw[offset:offset+w*h*4]
            if len(pixels)!=w*h*4:raise ValueError('Active caption pixel extent truncated')
            items.append(dict(id=cue['id'],first_frame=first,end_frame=end,english_lines=cue['english_lines'],x=x,y=y,width=w,height=h,expected_pixels_sha256=hashlib.sha256(pixels).hexdigest()))
        movies.append(dict(movie=draft['movie'],source_sha256=draft['source_sha256'],header144_sha256=draft['header144_sha256'],decoded_frames=draft['decoded_frames'],credit_pages=all(c.get('credit_page') is True for c in draft['cues']),cues=items))
    if position!=cues:raise ValueError('Caption count changed')
    plan=json.loads((base/'credits-work/page-plan.json').read_text(encoding='utf-8'))
    pages=[[{k:row[k] for k in ('id','y','height','translation','mode','page_y')} for row in page] for page in plan['pages']]
    frames=json.loads((base/'credits-fullframes/MOVIE33/frames.json').read_text())
    recipe=dict(schema=1,scope='English caption text, measured timing/crops, and ISO-derived original credit glyphs',movies=movies,
        expected_bundle_sha256=hashlib.sha256(raw).hexdigest(),credits=dict(pages=pages,name_policy=plan['name_policy'],
        sample_step=150,scroll_advance_per_sample=161,sample_frames=[r['frame'] for r in frames['frames']]))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(movies=count,cues=cues,credit_pages=len(pages),pixel_payloads_exported=0),indent=2))
if __name__=='__main__':main()
