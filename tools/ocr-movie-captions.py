"""Transcribe private decoded movie captions locally; OCR is never approval."""
import argparse,concurrent.futures,difflib,hashlib,json,os,re,sys,threading,time,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from caption_ocr import Engine,read_rgba_png,caption_mask

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--workers',type=int,choices=range(1,5),default=4)
    parser.add_argument('--movie',help='Only this movie stem for a bounded check')
    parser.add_argument('--update',action='store_true',help='Regenerate the same owned, unreviewed OCR outputs in place')
    args=parser.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private') or (out.exists() and not args.update) or out.is_symlink():parser.error('Use private transcription output and --update for owned OCR drafts')
    if out.exists() and json.loads((out/'result.json').read_text())['scope']!='local-OCR-drafts-not-approved':raise ValueError('Output is not owned OCR scratch')
    os.environ['OMP_THREAD_LIMIT']='1';jobs=[];movie_sources={}
    roots=[ROOT/'private/translation/text-pass-18-opening-timing/MOVIE01']+sorted((ROOT/'private/translation/text-pass-18-all-movie-captions').glob('MOVIE*'))
    for folder in roots:
        if folder.name=='MOVIE01' and folder.parent.name!='text-pass-18-opening-timing':continue
        if args.movie and folder.name!=args.movie:continue
        source=json.loads((folder/'frames.json').read_text());movie_sources[folder.name]={k:v for k,v in source.items() if k!='frames'}
        for frame in source['frames']:jobs.append((folder,frame))
    if not jobs:raise ValueError('No decoded frames')
    out.mkdir(parents=True,exist_ok=args.update);local=threading.local();engines=[];lock=threading.Lock()
    def initialize():
        local.engine=Engine(args.dll,args.models)
        with lock:engines.append(local.engine)
    def recognize(job):
        folder,frame=job;path=folder/frame['file'];raw=path.read_bytes();w,h,rgba=read_rgba_png(raw)
        w,h,gray=caption_mask(w,h,rgba,text_only=True);text,confidence=local.engine.recognize(w,h,gray)
        return dict(movie=folder.name,frame=frame['frame'],png=str(path.relative_to(ROOT)),png_sha256=hashlib.sha256(raw).hexdigest(),text=text,confidence=confidence,reviewed=False)
    started=time.monotonic();results=[]
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers,initializer=initialize) as pool,(out/'ocr.jsonl').open('w',encoding='utf-8') as destination:
            for row in pool.map(recognize,jobs):
                results.append(row);destination.write(json.dumps(row,ensure_ascii=False)+'\n')
                if len(results)%64==0:
                    destination.flush();print(json.dumps(dict(processed=len(results),total=len(jobs),seconds=round(time.monotonic()-started,1))),flush=True)
    finally:
        for engine in engines:engine.close()
    clusters=[];current=None
    for row in results:
        text=unicodedata.normalize('NFKC',re.sub(r'\s+','',row['text']))
        if row['confidence']<25 or len(re.findall(r'[\u3040-\u30ff\u3400-\u9fff]',text))<2:continue
        if current and current['movie']==row['movie'] and row['frame']-current['last_sample']<=30 and difflib.SequenceMatcher(None,current['normalized'],text).ratio()>=.72:
            current['last_sample']=row['frame'];current['samples']+=1
            if row['confidence']>current['confidence']:current.update(text=row['text'],confidence=row['confidence'],representative=row['png'],normalized=text)
        else:
            current=dict(movie=row['movie'],first_sample=row['frame'],last_sample=row['frame'],samples=1,text=row['text'],confidence=row['confidence'],representative=row['png'],normalized=text,reviewed=False)
            clusters.append(current)
    (out/'candidates.json').write_text(json.dumps(clusters,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    report=dict(scope='local-OCR-drafts-not-approved',frames=len(results),candidate_groups=len(clusters),
                preprocessing='neutral-ink-with-dark-outline-and-footer-mask',
                model_sha256=hashlib.sha256((args.models/'jpn.traineddata').read_bytes()).hexdigest(),
                engine_dll_sha256=hashlib.sha256(args.dll.read_bytes()).hexdigest(),external_service_used=False,
                seconds=round(time.monotonic()-started,2),sources=movie_sources)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sources'}))

if __name__=='__main__':main()
