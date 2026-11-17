"""Private caption bundle validation; enable only explicitly reviewed WIP bundles."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAGIC=b'LOACAP1\0'

def build(headers,cues):
    if not 0<len(headers)<=32 or not 0<len(cues)<=2048:raise ValueError('Invalid caption counts')
    for header in headers:
        if len(header)!=144 or not header.startswith(b'PSMF'):raise ValueError('Invalid movie header')
    if len(set(headers))!=len(headers):raise ValueError('Duplicate movie headers')
    table=[];pixels=[];unique_pixels={};offset=16+144*len(headers)+32*len(cues)
    for cue in cues:
        movie,first,end,x,y,w,h,rgba=cue
        if not 0<=movie<len(headers) or not 0<first<end<=1000000:raise ValueError('Invalid caption interval')
        if not 0<w<=480 or not 0<h<=272 or not 0<=x<=480-w or not 0<=y<=272-h:raise ValueError('Invalid caption rectangle')
        if len(rgba)!=w*h*4:raise ValueError('Invalid caption pixel extent')
        for previous in table:
            if previous[0]==movie and first<previous[2] and previous[1]<end:raise ValueError('Overlapping caption intervals')
        if rgba not in unique_pixels:
            unique_pixels[rgba]=offset;pixels.append(rgba);offset+=len(rgba)
        table.append((movie,first,end,x,y,w,h,unique_pixels[rgba]))
    if offset>64*1024*1024:raise ValueError('Caption bundle too large')
    return MAGIC+struct.pack('<2I',len(headers),len(cues))+b''.join(headers)+b''.join(struct.pack('<8I',*row) for row in table)+b''.join(pixels)

def environment(variant,root=None):
    env={'LOA_MOVIE_CAPTIONS':''}
    if variant!='english-text-test':return env
    root=Path(root) if root else ROOT/'private/translation/movie-captions'
    report_path=root/'result.json'
    if not report_path.exists():return env
    report=json.loads(report_path.read_text(encoding='utf-8'))
    if report.get('approved_for_launch') is not True:return env
    path=root/'captions.bin'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=report['bundle_sha256']:raise ValueError('Movie caption bundle hash differs')
    env['LOA_MOVIE_CAPTIONS']=str(path.resolve());return env
