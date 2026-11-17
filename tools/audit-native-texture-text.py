"""Local Japanese OCR triage of native XET top mips; never translation approval.

Only candidate previews are retained. No game data leaves private storage.
"""
import argparse,concurrent.futures,hashlib,importlib.util,json,os,re,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from rgf_archive import parse_index,resources
from xet_codec import Xet
from caption_ocr import Engine
spec=importlib.util.spec_from_file_location('audit_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archives',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if not a.archives.resolve().is_relative_to(ROOT/'private') or not out.is_relative_to(ROOT/'private') or out.exists():p.error('Use private archives and fresh private audit output')
 out.mkdir(parents=True);os.environ['OMP_THREAD_LIMIT']='1';local=threading.local();engines=[];lock=threading.Lock();seen=set();pixels_seen=set();skipped=[];duplicates=0;total=0;candidates=[];start=time.monotonic()
 def init():
  local.engine=Engine(Path('C:/Program Files/PDFgear/x64/tesseract41.dll'),Path('C:/Program Files/PDFgear/tessdata'))
  local.engine.lib.TessBaseAPISetPageSegMode(local.engine.api,11)
  with lock:engines.append(local.engine)
 def recognize(job):
  row,w,h,rgba=job;factor=3;pad=12;ow=w*factor+pad*2;oh=h*factor+pad*2;gray=bytearray(b'\xff'*(ow*oh))
  for y in range(h):
   scan=bytearray()
   for x in range(w):
    r,g,b,alpha=rgba[(y*w+x)*4:(y*w+x)*4+4];v=(r*299+g*587+b*114)//1000;v=255-(v*alpha//255);scan.extend(bytes([v])*factor)
   for j in range(factor):gray[(pad+y*factor+j)*ow+pad:(pad+y*factor+j)*ow+pad+len(scan)]=scan
  text,confidence=local.engine.recognize(ow,oh,gray);row.update(text=text,confidence=confidence,reviewed=False)
  jp=re.findall(r'[\u3040-\u30ff\u3400-\u9fff]',text)
  if confidence>=45 and len(jp)>=2:
   name=f"{row['resource_id']}-{row['source_sha256'][:12]}-{row['texture_index']:02d}.png";(out/name).write_bytes(png.png(w,h,rgba));row['preview']=name
  return row
 groups=parse_index((a.archives/'REGFILE.RZL').read_bytes(),(a.archives/'REGFILE.RZP').stat().st_size)
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=4,initializer=init) as pool,(out/'ocr.jsonl').open('w',encoding='utf-8') as log,(a.archives/'REGFILE.RZP').open('rb') as source:
   pending=[]
   def drain():
    nonlocal total
    for future in pending:
     row=future.result();log.write(json.dumps(row,ensure_ascii=False)+'\n');total+=1
     if 'preview' in row:candidates.append(row)
    pending.clear();log.flush();print(json.dumps(dict(processed=total,candidates=len(candidates),seconds=round(time.monotonic()-start,1))),flush=True)
   for group,identity,raw in resources(source,groups):
    if identity>>16!=2:continue
    sha=hashlib.sha256(raw).hexdigest();key=identity,sha
    if key in seen:continue
    seen.add(key);container=Xet.parse(raw)
    for i,t in enumerate(container.textures):
     row=dict(resource_id=f'{identity:08x}',source_sha256=sha,texture_index=i,name=t.name)
     if min(t.mips[0].width,t.mips[0].height)<12:skipped.append(dict(row,reason='dimension below twelve pixels'));continue
     try:w,h,rgba=container.preview(i,limit=512)
     except ValueError as e:skipped.append(dict(row,reason=str(e)));continue
     pixel_sha=hashlib.sha256(rgba).hexdigest()
     if pixel_sha in pixels_seen:duplicates+=1;continue
     pixels_seen.add(pixel_sha);row.update(width=w,height=h,pixels_sha256=pixel_sha)
     pending.append(pool.submit(recognize,(row,w,h,rgba)))
     if len(pending)>=32:drain()
   drain()
 finally:
  for engine in engines:engine.close()
 (out/'candidates.json').write_text(json.dumps(candidates,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 report=dict(scope='local-native-texture-OCR-triage-not-coverage-proof',resource_variants=len(seen),textures_scanned=total,pixel_duplicates=duplicates,candidates=len(candidates),skipped=skipped,external_service_used=False,visual_audit_complete=False,seconds=round(time.monotonic()-start,2))
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='skipped'}))
if __name__=='__main__':main()
