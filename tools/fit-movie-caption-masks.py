"""Fit private movie caption plates to source lettering and existing English ink.

Retains text pixels, decoded-picture timing and original movie/audio bytes.
Results are candidates: review the source/composite pairs before admission.
"""
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from caption_ocr import read_rgba_png
spec=importlib.util.spec_from_file_location('png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(points):
    return [min(x for x,y in points),min(y for x,y in points),max(x for x,y in points)+1,max(y for x,y in points)+1]
def lettering_bounds(points,line_count):
    """Group source ink by actual subtitle line, retaining punctuation at its ends.

    Do not use the draft's OCR character count as the mask's right edge: OCR can
    omit a character or a long dash. Moving scenery is suppressed by consensus;
    sparse isolated stars are separated from the dense caption clusters.
    """
    selected=[]
    for top,bottom in ((224,245),(245,272)) if line_count>1 else ((245,272),):
        columns={}
        for x,y in points:
            if top<=y<bottom:columns.setdefault(x,[]).append((x,y))
        clusters=[];current=[];previous=-100
        for x,ink in sorted(columns.items()):
            if x-previous>23 and current:clusters.append(current);current=[]
            current.extend(ink);previous=x
        if current:clusters.append(current)
        if not clusters:continue
        # Letters remain fixed and densely outlined at these two measured rows.
        plausible=[c for c in clusters if len(c)>=15 and min(x for x,y in c)<300 and max(x for x,y in c)>180]
        if plausible:selected.extend(max(plausible,key=len))
    return bounds(selected) if len(selected)>=15 else None
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('collection','samples','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume',action='store_true',help='Regenerate only named outputs in the same private working folder')
    a=p.parse_args();private=(ROOT/'private').resolve();out=a.output.resolve()
    if any(not path.resolve().is_relative_to(private) for path in (a.collection,a.samples,out)) or out.is_symlink() or (out.exists() and not a.resume):p.error('Use private inputs and fresh private output, or explicit --resume')
    jobs=json.loads(a.collection.read_text())['movies'];out.mkdir(parents=True,exist_ok=True);new=[];review=[]
    for job in jobs:
        draft_path=ROOT/job['draft'];folder=ROOT/job['bitmaps'];draft=json.loads(draft_path.read_text(encoding='utf-8'));movie=Path(draft['movie']).stem
        if all(c.get('credit_page') is True for c in draft['cues']):new.append(job);continue
        source=a.samples/movie;frames=json.loads((source/'frames.json').read_text())
        if frames['source_sha256']!=draft['source_sha256']:raise ValueError('Source sample movie identity differs')
        render=json.loads((folder/'render.json').read_text(encoding='utf-8-sig'));assets={r['id']:r for r in render['cues']}
        dest=out/movie
        if dest.is_symlink():raise ValueError('Output cannot be a symbolic link')
        dest.mkdir(exist_ok=True);records=[]
        for cue in draft['cues']:
            asset=assets[cue['id']];w,h=asset['width'],asset['height'];ox,oy=asset['x'],asset['y']
            rgba=(folder/asset['file']).read_bytes()
            if len(rgba)!=w*h*4 or asset['lines']!=cue['english_lines']:raise ValueError('Existing caption extent or wording differs')
            ink=[(ox+x,oy+y) for y in range(h) for x in range(w) if max(rgba[(y*w+x)*4:(y*w+x)*4+3])>0]
            if not ink:raise ValueError('Caption is blank')
            eb=bounds(ink)
            first,end=cue['first_frame'],cue['end_frame']
            eligible=[r for r in frames['frames'] if first<r['frame']<end-1]
            if not eligible:raise ValueError('Caption has no original-frame samples')
            # Three separated samples suppress moving bright background details.
            chosen=[eligible[k] for k in sorted(set((len(eligible)//4,len(eligible)//2,min(len(eligible)-1,len(eligible)*3//4))))]
            images=[]
            for f in chosen:
                sw,sh,s=read_rgba_png((source/f['file']).read_bytes())
                if (sw,sh)!=(480,64):raise ValueError('Expected measured footer strips')
                images.append(s)
            stable=[]
            # The measured baked lettering advances about 18 source pixels
            # per full-width character. A 16-pixel guide clipped edge strokes.
            half=min(w/2,max(len(s) for s in cue['japanese_lines'])*9+4)
            for y in range(max(16,oy-208),min(64,oy+h-208)):
                for x in range(ox,ox+w):
                    pos=(y*480+x)*4;votes=0
                    for s in images:
                        rgb=s[pos:pos+3]
                        if min(rgb)<180 or max(rgb)-min(rgb)>60:continue
                        # Baked subtitles have dark outlines, unlike large pale scenery.
                        dark=False
                        for dx,dy in ((-2,0),(2,0),(0,-2),(0,2)):
                            if not 0<=x+dx<480 or not 0<=y+dy<64:continue
                            q=((y+dy)*480+x+dx)*4
                            if max(s[q:q+3])<=100:dark=True;break
                        votes+=dark
                    if votes>=math.ceil(len(images)*.6):stable.append((x,y+208))
            measured=lettering_bounds(stable,len(cue['japanese_lines']))
            fallback=measured is None
            jb=[ox,oy,ox+w,oy+h] if fallback else measured
            # Conservative full-width Japanese glyph guide includes thin strokes
            # and dark/fading edge glyphs absent from a bright-ink consensus.
            x0=max(ox,math.floor(min(eb[0]-4,jb[0]-3,240-half)))
            x1=min(ox+w,math.ceil(max(eb[2]+4,jb[2]+3,240+half)))
            y0=max(oy,min(eb[1]-3,jb[1]-3));y1=min(oy+h,max(eb[3]+3,jb[3]+3))
            if not (x0<=eb[0]<eb[2]<=x1 and y0<=eb[1]<eb[3]<=y1):raise ValueError('English glyph would be clipped')
            nw,nh=x1-x0,y1-y0;pixels=b''.join(rgba[((y-oy)*w+x0-ox)*4:((y-oy)*w+x1-ox)*4] for y in range(y0,y1))
            stem=Path(asset['file']).stem;(dest/(stem+'.rgba')).write_bytes(pixels);(dest/(stem+'.png')).write_bytes(png.png(nw,nh,pixels))
            records.append(dict(asset,x=x0,y=y0,width=nw,height=nh,file=stem+'.rgba'))
            # A real source strip composited with the exact writer rectangle.
            sample=bytearray(images[len(images)//2])
            for yy in range(nh):
                at=((y0-208+yy)*480+x0)*4;sample[at:at+nw*4]=pixels[yy*nw*4:(yy+1)*nw*4]
            (dest/(stem+'-composite.png')).write_bytes(png.png(480,64,sample))
            review.append(dict(movie=movie,id=cue['id'],old_rectangle=[ox,oy,w,h],rectangle=[x0,y0,nw,nh],original_ink_bounds=jb,english_ink_bounds=eb,source_sample_frames=[r['frame'] for r in chosen],source_samples_sha256=[sha(source/r['file']) for r in chosen],english_pixels_preserved=True,retained_full_plate_for_manual_review=fallback))
        (dest/'render.json').write_text(json.dumps(dict(render,cues=records,plate='per-cue source-lettering and English-ink bounds',auto_shrink=False),indent=2)+'\n')
        new.append(dict(draft=job['draft'],bitmaps=str(dest.relative_to(ROOT))))
    (out/'collection.json').write_text(json.dumps(dict(movies=new),indent=2)+'\n')
    report=dict(status='candidate-needs-visual-review',cues=review,audio_modified=False,timing_modified=False,external_service_used=False)
    (out/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cues=len(review),old_plate_pixels=sum(r['old_rectangle'][2]*r['old_rectangle'][3] for r in review),new_plate_pixels=sum(r['rectangle'][2]*r['rectangle'][3] for r in review),audio_modified=False)))
if __name__=='__main__':main()
