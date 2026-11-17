"""Rebuild the measured WIP English ASCII atlas from a private observer capture.

No game bytes or font outlines are distributed. The observer exports the atlas
only after seeing the measured R/S texture identity; this tool independently
checks all 19 previously drawn pages before constructing any replacement jobs.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from ui_pack import merge


def prepare(capture, output):
    capture,output=Path(capture).resolve(),Path(output).resolve()
    if not capture.is_relative_to(ROOT/'private') or not capture.is_dir():
        raise ValueError('Use a private observer capture directory')
    if not output.is_relative_to(ROOT/'private') or output.exists():
        raise ValueError('Use a fresh private output directory')
    raw=(capture/'ascii-atlas.raw').read_bytes()
    rows=[json.loads(x) for x in (capture/'ascii-atlas.jsonl').read_text().splitlines()]
    known=[json.loads(x) for x in (capture/'texture-probe.jsonl').read_text().splitlines()]
    if len(raw)!=48*256 or [r['first_code'] for r in rows]!=list(range(32,128,2)):
        raise ValueError('Unexpected ASCII atlas extent or character order')
    import re
    if any(not re.fullmatch('[0-9a-f]{24}',r['key']) for r in rows+known):
        raise ValueError('Invalid observed texture identity')
    anchor=next(r for r in known if r['key'].endswith('39c4625c'))
    rgba=(capture/('texture-'+anchor['key']+'.rgba')).read_bytes()
    if len(rgba)!=512*4:
        raise ValueError('Unexpected anchor extent')
    palette={}
    for i in range(512):
        value=(raw[25*256+i//2]>>(4*(i%2)))&15
        pixel=rgba[i*4:i*4+4]
        if palette.get(value,pixel)!=pixel:
            raise ValueError('Atlas palette does not reproduce the observed anchor')
        palette[value]=pixel
    if len(palette)!=16:
        raise ValueError('Incomplete observed palette')
    decoded=[]
    matched=0
    for index,row in enumerate(rows):
        pixels=b''.join(palette[(raw[index*256+i//2]>>(4*(i%2)))&15] for i in range(512))
        observed=next((r for r in known if r['key']==row['key']),None)
        if observed:
            if pixels!=(capture/('texture-'+row['key']+'.rgba')).read_bytes():
                raise ValueError('Decoded atlas differs from an actually drawn page')
            matched+=1
        decoded.append(pixels)
    if matched<19:
        raise ValueError('Need all 19 independently observed reference pages')
    spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/inventory-textures.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    output.mkdir(parents=True)
    (output/'sources').mkdir();(output/'jobs').mkdir()
    for row,pixels in zip(rows,decoded):
        code=row['first_code']
        source=output/'sources'/f'{code}.png'
        source.write_bytes(module.png(32,16,pixels))
        regions=[]
        for slot in range(2):
            character=code+slot
            if character in (32,127):
                continue
            ink=[(x,y) for y in range(16) for x in range(slot*16,(slot+1)*16) if pixels[(y*32+x)*4+3]>64]
            if not ink:
                raise ValueError(f'Printable character {character} has no measured ink')
            xs,ys=zip(*ink)
            regions.append(dict(text=chr(character),bold=False,outline_pixels=0,
                region=dict(x=slot*16,y=0,width=16,height=16),
                ink=dict(x=min(xs),y=min(ys),width=max(xs)-min(xs)+1,height=max(ys)-min(ys)+1)))
        job=dict(source=str(source),factor=4,key='00000000'+row['key'][8:],font='Arial',regions=regions)
        (output/'jobs'/f'{code}.json').write_text(json.dumps(job,indent=2)+'\n')
    report={'reference_pages_matched':matched,'pages':48,'printable_glyphs':94,
            'all_dialogue_validated':False,'complete_hd_remaster':False}
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--base-samples',type=Path,nargs=4,help='Also build and merge with prompts, two notices and numerals')
    args=parser.parse_args()
    report=prepare(args.capture,args.output)
    if args.base_samples:
        sources=list(args.base_samples)
        destination=args.output.resolve()/'atlases';destination.mkdir()
        for job in sorted((args.output/'jobs').glob('*.json')):
            target=destination/job.stem
            run=subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/build-ui-font-sample.ps1'),
                                '-Job',str(job.resolve()),'-Output',str(target)],capture_output=True,text=True)
            (destination/(job.stem+'.log')).write_text(run.stdout+run.stderr)
            run.check_returncode();sources.append(target)
        pack=merge(sources,args.output/'pack')
        report['pack_textures']=len(pack['textures'])
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
