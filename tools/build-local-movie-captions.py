"""Generate caption pixels locally; recover original credit glyphs from the user's ISO."""
import argparse,hashlib,importlib.util,json,os,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,movie_captions
from iso_edits import survey,extent_hash

def sha(raw):return hashlib.sha256(raw).hexdigest()

def run_render(script,arguments):
    powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(powershell),'-NoProfile','-File',str(ROOT/'tools'/script),*arguments],capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr)

def discard_incomplete_render(render,record):
    """Retry only an incomplete owned movie render, preserving completed movies."""
    if not render.exists():return
    if render.is_symlink() or render.is_junction():raise ValueError('Linked caption render is not owned scratch')
    expected={f"cue-{cue['id']:04}.rgba" for cue in record['cues']}
    if all((render/name).is_file() for name in expected):return
    for path in render.iterdir():
        if path.is_symlink() or not path.is_file() or (path.name!='render.json' and not __import__('re').fullmatch(r'cue-[0-9]{4}\.(?:png|rgba)',path.name)):
            raise ValueError('Unknown file in interrupted caption render; preserving it')
    for path in render.iterdir():path.unlink()
    render.rmdir()

def credit_lines(image,row,plan,output):
    from tester_setup import patcher_paths
    lines={r['id']:r for page in plan['pages'] for r in page}
    buffers={i:bytearray(r['height']*480*4) for i,r in lines.items()};copied={i:0 for i in lines}
    helper=ROOT/'private/local-build/movie-helper/movie-survey.exe'
    if not helper.is_file():raise FileNotFoundError('Build the game-independent movie survey helper first')
    frames=plan['sample_frames'];advance=plan['scroll_advance_per_sample'];index=0
    # The native survey tool uses narrow fopen(). A scoped Windows DOS-device
    # alias supports Unicode, long and UNC original-ISO paths without copying it.
    with patcher_paths(image) as aliases,(output/'credit-decode.log').open('wb') as log:
        process=subprocess.Popen([str(helper),aliases[0],str(row['lba']*2048),str(row['size']),str(plan['sample_step'])],stdout=subprocess.PIPE,stderr=log,env=title.environment())
        try:
            while True:
                wire=process.stdout.read(24)
                if not wire:break
                if len(wire)!=24:raise ValueError('Truncated decoded frame header')
                magic,frame,w,h,pts=struct.unpack('<4Iq',wire)
                if magic!=0x31464f4c or (w,h)!=(480,272) or index>=len(frames) or frame!=frames[index]:raise ValueError('Measured credit frame sequence differs')
                pixels=process.stdout.read(w*h*4)
                if len(pixels)!=w*h*4:raise ValueError('Truncated decoded credit picture')
                top=index*advance;bottom=top+(h if index==len(frames)-1 else advance)
                for i,band in lines.items():
                    first=max(band['y'],top);end=min(band['y']+band['height'],bottom)
                    if first<end:
                        source=(first-top)*480*4;dest=(first-band['y'])*480*4;length=(end-first)*480*4
                        buffers[i][dest:dest+length]=pixels[source:source+length];copied[i]+=end-first
                index+=1
                if index%16==0:print('Credit source frames decoded:',index,flush=True)
            if process.wait(timeout=30)!=0 or index!=len(frames):raise ValueError('Credit decode did not complete')
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
    spec=importlib.util.spec_from_file_location('credit_png',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)
    folder=output/'credit-lines';folder.mkdir(exist_ok=True)
    for i,band in lines.items():
        if copied[i]!=band['height']:raise ValueError('Credit glyph row is incomplete')
        (folder/f'line-{i:03}.png').write_bytes(png.png(480,band['height'],buffers[i]))
    return folder

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--recipe',type=Path,default=ROOT/'private/local-build/movie-caption-recipe.json')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--resume',action='store_true')
    parser.add_argument('--allow-local-rasterization',action='store_true',help='Record local font pixels while preserving original movie identity and cue timing')
    args=parser.parse_args()
    output=args.output.resolve();image=args.image.resolve(strict=True)
    if not output.is_relative_to(ROOT/'private'):raise ValueError('Keep caption pixels private')
    raw=args.recipe.read_bytes();recipe=json.loads(raw)
    if recipe.get('schema')!=1:raise ValueError('Unknown caption recipe')
    identity=dict(tool='local-movie-caption-build-v1',recipe_sha256=sha(raw),source_ISO_sha256=title.CONFIG['disc']['iso_sha256'])
    if output.exists():
        if not args.resume or json.loads((output/'owner.json').read_text())!=identity:raise ValueError('Existing caption work does not match recipe')
    else:output.mkdir(parents=True);(output/'owner.json').write_text(json.dumps(identity,indent=2)+'\n')
    title.verify_disc_image(image,'japanese');headers=[];cues=[];verified=0;mismatches=[]
    with image.open('rb') as stream:
        files=survey.ISO(stream).files()
        for movie,record in enumerate(recipe['movies']):
            matches=[row for name,row in files.items() if name.endswith('/MOVIE/'+record['movie'])]
            if len(matches)!=1:raise ValueError('Movie source is ambiguous')
            row=matches[0]
            if extent_hash(stream,row['lba']*2048,row['size'])!=record['source_sha256']:raise ValueError('Original movie hash differs')
            stream.seek(row['lba']*2048);header=stream.read(144)
            if sha(header)!=record['header144_sha256']:raise ValueError('Original movie header differs')
            headers.append(header);work=output/Path(record['movie']).stem;work.mkdir(exist_ok=True);render=work/'rendered'
            discard_incomplete_render(render,record)
            if not render.exists():
                if record['credit_pages']:
                    lines=credit_lines(image,row,recipe['credits'],work)
                    plan=work/'plan.json';plan.write_text(json.dumps(recipe['credits'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                    run_render('render-local-credits.ps1',['-Plan',str(plan),'-Lines',str(lines),'-Output',str(render)])
                else:
                    draft=work/'draft.json';draft.write_text(json.dumps(dict(cues=record['cues']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                    run_render('render-movie-captions.ps1',['-Draft',str(draft),'-Output',str(render)])
            for cue in record['cues']:
                pixels=(render/f"cue-{cue['id']:04}.rgba").read_bytes();x,y,w,h=cue['x'],cue['y'],cue['width'],cue['height']
                if not record['credit_pages']:
                    if len(pixels)!=448*48*4 or not 16<=x<=x+w<=464 or not 224<=y<=y+h<=272:raise ValueError('Measured story caption crop differs')
                    ink=[(16+xx,224+yy) for yy in range(48) for xx in range(448) if any(pixels[(yy*448+xx)*4:(yy*448+xx)*4+3])]
                    if not ink:raise ValueError('Generated caption is blank')
                    if any(not x<=xx<x+w or not y<=yy<y+h for xx,yy in ink):
                        if not args.allow_local_rasterization:raise ValueError('Generated English glyph would be clipped')
                        right=max(x+w,min(464,max(xx for xx,yy in ink)+4));bottom=max(y+h,min(272,max(yy for xx,yy in ink)+4))
                        x=min(x,max(16,min(xx for xx,yy in ink)-3));y=min(y,max(224,min(yy for xx,yy in ink)-3));w,h=right-x,bottom-y
                    pixels=b''.join(pixels[((yy-224)*448+x-16)*4:((yy-224)*448+x-16+w)*4] for yy in range(y,y+h))
                if len(pixels)!=w*h*4:raise ValueError('Locally generated caption extent differs')
                if sha(pixels)!=cue['expected_pixels_sha256']:
                    mismatches.append(dict(movie=record['movie'],id=cue['id'],actual_sha256=sha(pixels),expected_sha256=cue['expected_pixels_sha256']))
                cues.append((movie,cue['first_frame'],cue['end_frame'],x,y,w,h,pixels));verified+=1
            print('Locally generated captions:',record['movie'],len(record['cues']),flush=True)
    if mismatches:
        (output/'pixel-mismatches.json').write_text(json.dumps(mismatches,indent=2)+'\n')
        if not args.allow_local_rasterization:
            raise ValueError(f'{len(mismatches)} caption renders differ; see pixel-mismatches.json. No bundle admitted.')
    data=movie_captions.build(headers,cues)
    if sha(data)!=recipe['expected_bundle_sha256'] and not args.allow_local_rasterization:raise ValueError('Locally generated caption bundle differs')
    (output/'captions.bin').write_bytes(data)
    report=dict(status='PASS',bundle_sha256=sha(data),movies=len(headers),verified_cues=verified,caption_pixels_copied_in=False,
        original_credit_glyphs_read_from_ISO=True,audio_modified=False,source_movie_modified=False,active_caption_bundle_changed=False,
        approved_for_launch=False,reference_bundle_sha256=recipe.get('reference_bundle_sha256',recipe['expected_bundle_sha256']),
        byte_identical_to_reference=sha(data)==recipe.get('reference_bundle_sha256',recipe['expected_bundle_sha256']),
        reference_comparison=recipe.get('reference_comparison'))
    report.update(local_rasterization_allowed=args.allow_local_rasterization,nonidentical_recipe_cues=len(mismatches),
        byte_identical_to_recipe=sha(data)==recipe['expected_bundle_sha256'])
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
