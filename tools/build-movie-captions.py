"""Build a private decoded-frame caption candidate; never approves it for play."""
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,movie_captions
from iso_edits import survey,extent_hash

def movie_inputs(draft_path,bitmaps,stream,files,movie_index):
    private=(ROOT/'private').resolve()
    if not draft_path.resolve().is_relative_to(private) or not bitmaps.resolve().is_relative_to(private):raise ValueError('Keep source text and bitmaps private')
    draft=json.loads(draft_path.read_text(encoding='utf-8'))
    render=json.loads((bitmaps/'render.json').read_text(encoding='utf-8-sig'))
    if render['scope']!='local-movie-caption-bitmaps':raise ValueError('Unknown caption renderer')
    matches=[row for name,row in files.items() if '/MOVIE/' in name and name.rsplit('/',1)[-1]==draft['movie']]
    if len(matches)!=1:raise ValueError('Movie identity ambiguous')
    row=matches[0]
    if extent_hash(stream,row['lba']*2048,row['size'])!=draft['source_sha256']:raise ValueError('Movie payload hash differs')
    stream.seek(row['lba']*2048);header=stream.read(144)
    if hashlib.sha256(header).hexdigest()!=draft['header144_sha256']:raise ValueError('Movie header differs')
    assets={row['id']:row for row in render['cues']};intervals=[]
    for cue in draft['cues']:
        intervals.append([cue['first_frame'] if 'first_frame' in cue else cue['start_frame_window'][0],cue['end_frame'] if 'end_frame' in cue else cue['end_frame_window'][1]])
    for i in range(1,len(intervals)):
        if intervals[i-1][1]>intervals[i][0]:
            if 'first_frame' in draft['cues'][i]:raise ValueError('Refined caption intervals overlap')
            boundary=(draft['cues'][i-1]['last_visible_sample']+draft['cues'][i]['first_visible_sample'])//2+1
            intervals[i-1][1]=intervals[i][0]=boundary
    cues=[];records=[]
    for cue,(first,end) in zip(draft['cues'],intervals):
        if not 0<first<end<=draft['decoded_frames']+1:raise ValueError('Caption interval exceeds decoded movie extent')
        asset=assets[cue['id']]
        if asset['lines']!=cue['english_lines']:raise ValueError('Caption text differs from rendered lines')
        name=asset['file']
        if Path(name).name!=name:raise ValueError('Caption pixel path escapes input')
        pixels=(bitmaps/name).read_bytes()
        cues.append((movie_index,first,end,asset['x'],asset['y'],asset['width'],asset['height'],pixels))
        records.append(dict(movie_index=movie_index,id=cue['id'],first_frame=first,end_frame=end,english_lines=cue['english_lines'],pixels_sha256=hashlib.sha256(pixels).hexdigest()))
    paginated=bool(draft['cues']) and all(c.get('credit_page') is True for c in draft['cues'])
    info=dict(movie=draft['movie'],source_sha256=draft['source_sha256'],draft_sha256=hashlib.sha256(draft_path.read_bytes()).hexdigest(),cue_count=len(cues),per_frame_refined=draft.get('sampling_step')==1,paginated_credits=paginated)
    return header,cues,records,info

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft',type=Path,nargs='?');parser.add_argument('--bitmaps',type=Path)
    parser.add_argument('--collection',type=Path,help='Private list of draft/bitmap pairs')
    parser.add_argument('--output',type=Path,default=ROOT/'private/translation/movie-captions-candidate')
    args=parser.parse_args();private=(ROOT/'private').resolve();out=args.output.resolve()
    if not out.is_relative_to(private) or out.is_symlink():parser.error('Keep caption candidates private')
    if (out/'result.json').exists() and json.loads((out/'result.json').read_text()).get('approved_for_launch') is True:
        raise ValueError('Never overwrite a reviewed active bundle; build the separate working candidate')
    if args.collection:
        if args.draft or args.bitmaps or not args.collection.resolve().is_relative_to(private):parser.error('Use a private collection or one draft/bitmap pair')
        jobs=[(ROOT/row['draft'],ROOT/row['bitmaps']) for row in json.loads(args.collection.read_text())['movies']]
    else:
        if not args.draft or not args.bitmaps:parser.error('A draft and --bitmaps are required')
        jobs=[(args.draft,args.bitmaps)]
    image=title.disc_image('english-v16');title.verify_disc_image(image,'english-v16')
    headers=[];cues=[];records=[];movies=[]
    with image.open('rb') as stream:
        files=survey.ISO(stream).files()
        for i,(draft,bitmaps) in enumerate(jobs):
            header,new_cues,new_records,info=movie_inputs(draft,bitmaps,stream,files,i)
            headers.append(header);cues.extend(new_cues);records.extend(new_records);movies.append(info)
    data=movie_captions.build(headers,cues)
    out.mkdir(parents=True,exist_ok=True)
    temporary=out/'captions.bin.tmp';temporary.write_bytes(data);os.replace(temporary,out/'captions.bin')
    report=dict(scope='local-native-movie-caption-candidate',approved_for_launch=False,
                bundle_sha256=hashlib.sha256(data).hexdigest(),movies=movies,movie_count=len(movies),cue_count=len(cues),
                timing='per-frame-story-captions-and-paginated-credits' if all(m['per_frame_refined'] or m['paginated_credits'] for m in movies) else 'sample-bracket-estimate-needs-per-frame-validation',audio_modified=False,source_movie_modified=False,cues=records)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key!='cues'},indent=2))

if __name__=='__main__':main()
