"""Read-only movie caption samples directly from a verified local ISO.

No PMF/audio copies are extracted. Samples and narration text stay private.
The separately built helper uses the pinned native Media Foundation backend.
"""
import argparse,hashlib,importlib.util,json,re,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
from iso_edits import survey,extent_hash
_spec=importlib.util.spec_from_file_location('caption_png',ROOT/'tools/inventory-textures.py')
_png=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_png)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--movie',default='MOVIE01.PMF',help='Exact movie basename or ALL')
    parser.add_argument('--every',type=int,default=15)
    parser.add_argument('--full-frames',action='store_true',help='Sparse whole-picture audit for title text outside the footer')
    parser.add_argument('--update',action='store_true',help='Refine the same owned survey in place without duplicating old samples')
    parser.add_argument('--exclude-movie',action='append',default=[],help='Exact basename to leave at its existing sampling step')
    args=parser.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private') or (out.exists() and not args.update) or not 1<=args.every<=300:parser.error('Use a private output, explicit --update for an existing survey, and sampling step 1..300')
    if out.is_symlink():raise ValueError('Survey output cannot be a link')
    summaries={}
    if out.exists():
        summaries={row['movie']:row for row in json.loads((out/'summary.json').read_text())}
    image=title.disc_image('english-v16');title.verify_disc_image(image,'english-v16')
    helper=ROOT/'private/translation/text-pass-18-movie-survey/movie-survey.exe'
    if not helper.is_file():raise FileNotFoundError('Build the pinned movie survey helper first')
    out.mkdir(parents=True,exist_ok=args.update)
    with image.open('rb') as source:
        movies=[(n,r) for n,r in survey.ISO(source).files().items() if '/MOVIE/' in n and n.endswith('.PMF') and n.rsplit('/',1)[-1] not in args.exclude_movie and (args.movie=='ALL' or n.rsplit('/',1)[-1]==args.movie)]
        if not movies:raise ValueError('Movie not found')
        for name,row in movies:
            folder=out/Path(name).stem;frames=[]
            source.seek(row['lba']*2048);header=source.read(144)
            fingerprint=extent_hash(source,row['lba']*2048,row['size'])
            if folder.exists():
                previous=json.loads((folder/'frames.json').read_text())
                if folder.is_symlink() or previous['movie']!=name or previous['source_sha256']!=fingerprint or previous['sampling_step']%args.every or (previous.get('frame_crop','bottom-64')=='full')!=args.full_frames:
                    raise ValueError('Only refine the same source at a divisor of its old sampling step')
            else:folder.mkdir()
            with (folder/'decode.log').open('wb') as log:
                process=subprocess.Popen([str(helper),str(image),str(row['lba']*2048),str(row['size']),str(args.every)],stdout=subprocess.PIPE,stderr=log,env=title.environment())
                try:
                    while True:
                        wire=process.stdout.read(24)
                        if not wire:break
                        if len(wire)!=24:raise ValueError('Short survey frame header')
                        magic,index,w,h,pts=struct.unpack('<4Iq',wire)
                        if magic!=0x31464f4c or not 0<w<=512 or not 0<h<=512:raise ValueError('Invalid survey frame geometry')
                        rgba=process.stdout.read(w*h*4)
                        if len(rgba)!=w*h*4:raise ValueError('Short decoded frame')
                        crop_height=h if args.full_frames else min(h,64);crop=rgba[w*(h-crop_height)*4:]
                        filename=f'caption-{index:05d}.png';(folder/filename).write_bytes(_png.png(w,crop_height,crop))
                        frames.append(dict(frame=index,pts=pts,file=filename,width=w,height=crop_height,source_height=h))
                    code=process.wait(timeout=20)
                finally:
                    if process.poll() is None:process.terminate();process.wait(timeout=5)
            log=(folder/'decode.log').read_text(errors='replace');match=re.search(r'decoded_frames=(\d+)',log)
            record=dict(movie=name,returncode=code,decoded_frames=int(match[1]) if match else None,
                        source_sha256=fingerprint,header144_sha256=hashlib.sha256(header).hexdigest(),sampling_step=args.every,frame_crop='full' if args.full_frames else 'bottom-64',
                        source_movie_and_audio_modified=False,frames=frames)
            (folder/'frames.json').write_text(json.dumps(record,indent=2)+'\n')
            summaries[name]=dict(record,frames=len(frames))
            (out/'summary.json').write_text(json.dumps([summaries[n] for n in sorted(summaries)],indent=2)+'\n')
            print(json.dumps(dict(movie=Path(name).name,returncode=code,frames=record['decoded_frames'],samples=len(frames))),flush=True)
            if code or not match:raise RuntimeError('Movie decode failed; inspect private log')

if __name__=='__main__':main()
