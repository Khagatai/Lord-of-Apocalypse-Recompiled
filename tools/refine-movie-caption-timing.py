"""Measure baked-caption appearance around observed brackets using real frames.

Stable white-ink templates come from the private sample images. Results describe
image visibility, not automatic approval of narration/audio synchronization.
"""
import argparse,hashlib,importlib.util,json,statistics,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from caption_ocr import read_rgba_png
from iso_edits import survey,extent_hash
import title
spec=importlib.util.spec_from_file_location('timing_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)

def neutral(r,g,b):return min(r,g,b) if max(r,g,b)-min(r,g,b)<=60 else 0

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('draft',type=Path)
    parser.add_argument('--samples',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--update',action='store_true',help='Update the same private timing diagnostic in place')
    parser.add_argument('--boundary-radius',type=int,default=20,choices=range(20,61),help='Frames around each observed boundary; larger windows still require separable blank evidence')
    args=parser.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private') or (out.exists() and not args.update) or out.is_symlink():parser.error('Use private timing output and explicit --update for owned diagnostics')
    if out.exists() and not (out/'decode.log').is_file():raise ValueError('Existing folder is not a timing diagnostic')
    for path in (args.draft,args.samples):
        if not path.resolve().is_relative_to(ROOT/'private'):raise ValueError('Source text and frames must remain private')
    draft=json.loads(args.draft.read_text(encoding='utf-8'));sample_report=json.loads((args.samples/'frames.json').read_text())
    templates=[];all_windows=set();radius=args.boundary_radius
    for cue in draft['cues']:
        frames=[row for row in sample_report['frames'] if cue['first_visible_sample']<=row['frame']<=cue['last_visible_sample']]
        samples=[]
        for row in frames:
            w,h,rgba=read_rgba_png((args.samples/row['file']).read_bytes())
            if (w,h)!=(480,64):raise ValueError('Expected actual 480x64 caption strips')
            samples.append(rgba)
        if not samples:raise ValueError('Cue has no source samples')
        mask=[];votes_by_offset={}
        for y in range(8,64):
            for x in range(48,432):
                offset=(y*480+x)*4
                votes=sum(neutral(*rgba[offset:offset+3])>=180 for rgba in samples)
                votes_by_offset[offset]=votes
                if votes>=max(1,(len(samples)*4+4)//5):mask.append(offset)
        consensus=.8
        if len(mask)<15:
            consensus=.6;mask=[o for o,v in votes_by_offset.items() if v>=max(1,(len(samples)*3+4)//5)]
        if len(mask)<15:raise ValueError(f'Cue {cue["id"]} has insufficient stable ink; manual review required')
        pairs=[]
        for offset in mask:
            pixel=offset//4;x=pixel%480;y=pixel//480;candidates=[]
            for dy in (-2,-1,0,1,2):
                for dx in (-2,-1,0,1,2):
                    if not (dx or dy) or not 0<=x+dx<480 or not 0<=y+dy<64:continue
                    neighbor=((y+dy)*480+x+dx)*4
                    if sum(max(rgba[neighbor:neighbor+3])<=100 for rgba in samples)>=max(1,(len(samples)*3+4)//5):
                        candidates.append((sum(min(rgba[neighbor:neighbor+3]) for rgba in samples),neighbor))
            if candidates:pairs.append((offset,min(candidates)[1]))
        if len(pairs)<15:raise ValueError(f'Cue {cue["id"]} lacks stable text-outline contrast')
        mask=pairs
        full=statistics.mean(sum(max(0,neutral(*rgba[o:o+3])-min(rgba[n:n+3])) for o,n in mask)/len(mask) for rgba in samples)
        first=cue['first_visible_sample'];last=cue['last_visible_sample']
        window=set(range(max(1,first-radius),first+radius+1))|set(range(max(1,last-radius),last+radius+1))
        templates.append(dict(mask=mask,full=full,window=window,scores={},consensus=consensus))
        all_windows.update(window)
    image=title.disc_image('english-v16');title.verify_disc_image(image,'english-v16')
    with image.open('rb') as stream:
        rows=[row for name,row in survey.ISO(stream).files().items() if '/MOVIE/' in name and name.rsplit('/',1)[-1]==draft['movie']]
        if len(rows)!=1:raise ValueError('Movie identity ambiguous')
        row=rows[0]
        if extent_hash(stream,row['lba']*2048,row['size'])!=draft['source_sha256']:raise ValueError('Movie source differs')
    out.mkdir(parents=True,exist_ok=args.update);evidence={}
    helper=ROOT/'private/translation/text-pass-18-movie-survey/movie-survey.exe'
    with (out/'decode.log').open('wb') as log:
        process=subprocess.Popen([str(helper),str(image),str(row['lba']*2048),str(row['size']),'1'],stdout=subprocess.PIPE,stderr=log,env=title.environment())
        try:
            while True:
                header=process.stdout.read(24)
                if not header:break
                if len(header)!=24:raise ValueError('Short frame header')
                magic,index,w,h,pts=struct.unpack('<4Iq',header)
                if magic!=0x31464f4c or w!=480 or h!=272:raise ValueError('Unexpected movie geometry')
                raw=process.stdout.read(w*h*4)
                if len(raw)!=w*h*4:raise ValueError('Short frame pixels')
                if index in all_windows:
                    crop=raw[w*(h-64)*4:];evidence[index]=crop
                    for template in templates:
                        if index in template['window']:
                            template['scores'][index]=sum(max(0,neutral(*crop[o:o+3])-min(crop[n:n+3])) for o,n in template['mask'])/len(template['mask'])
                if index%500==0:print(json.dumps(dict(decoded_frames=index)),flush=True)
            code=process.wait(timeout=20)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=5)
    if code:raise RuntimeError('Native movie decode failed')
    (out/'visibility-scores.json').write_text(json.dumps([dict(id=cue['id'],full=template['full'],scores=template['scores']) for cue,template in zip(draft['cues'],templates)],indent=2)+'\n')
    records=[];review=[]
    for cue,template in zip(draft['cues'],templates):
        first=cue['first_visible_sample'];last=cue['last_visible_sample'];scores=template['scores']
        before=statistics.mean(scores[n] for n in range(max(1,first-radius),max(1,first-radius)+4))
        after=statistics.mean(scores[n] for n in range(last+radius-3,last+radius+1))
        full=template['full'];threshold_start=before+.25*(full-before);threshold_end=after+.25*(full-after)
        starts=[n for n in range(max(1,first-radius+1),first+radius) if scores[n]>=threshold_start and scores[n+1]>=threshold_start]
        ends=[n for n in range(max(2,last-radius+1),last+radius) if scores[n]>=threshold_end and scores[n-1]>=threshold_end]
        if not starts or not ends or max(before,after)>.75*full:raise ValueError(f'Cue {cue["id"]} visibility not separable (full={full:.1f}, before={before:.1f}, after={after:.1f}); manual boundary review required')
        start=min(starts);end=max(ends)+1
        records.append(dict(cue,first_frame=max(1,start-1),end_frame=end+1))
        review.append(dict(id=cue['id'],stable_ink_pixels=len(template['mask']),first_frame=max(1,start-1),end_frame=end+1,
                           template_consensus_fraction=template['consensus'],boundary_radius=radius,
                           full_ink_level=full,before_level=before,after_level=after,visibility_threshold_fraction=.25,
                           scores=scores))
        for label,n in (('before',start-1),('start',start),('last',end-1),('after',end)):
            if n in evidence:(out/f'cue-{cue["id"]:04d}-{label}-{n:05d}.png').write_bytes(png.png(480,64,evidence[n]))
    for a,b in zip(records,records[1:]):
        overlap=a['end_frame']-b['first_frame']
        if overlap>4:raise ValueError('Measured cue intervals overlap beyond transition padding; review required')
        if overlap>0:
            boundary=(a['end_frame']+b['first_frame'])//2
            a['end_frame']=b['first_frame']=boundary
            a['transition_padding_adjusted']=b['transition_padding_adjusted']=True
    result=dict(draft,cues=records,status='per-frame-visibility-refined-needs-native-and-audio-review',sampling_step=1)
    (out/'draft.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (out/'measurements.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(dict(cues=len(records),decoded_frames=index,source_movie_modified=False,audio_modified=False)))

if __name__=='__main__':main()
