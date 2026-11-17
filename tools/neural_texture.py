"""Identity-pinned offline restoration helpers; no network operations or uploads."""
import hashlib
import json
from pathlib import Path
from collections import deque

ROOT=Path(__file__).resolve().parents[1]

def sha(data):return hashlib.sha256(data).hexdigest()

def verify_tool(folder):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(ROOT/'private'):raise ValueError('Upscaler must remain private')
    pins=json.loads((ROOT/'config/remaster-upscaler.json').read_text())
    for name,expected in pins['files'].items():
        if sha((folder/name).read_bytes())!=expected.lower():raise ValueError('Offline upscaler identity differs: '+name)
    return pins


def processing_pins(pins,model='realesrgan-x4plus'):
    if model not in ('realesrgan-x4plus','realesrgan-x4plus-anime'):
        raise ValueError('Unknown pinned restoration model')
    names=('realesrgan-ncnn-vulkan.exe','vcomp140.dll','vcomp140d.dll',f'models/{model}.param',f'models/{model}.bin')
    try:return {'model':model,'release':pins['release'],'files':{name:pins['files'][name] for name in names}}
    except KeyError as error:raise ValueError('Incomplete processing model pins') from error

def pad_opaque(data,width,height,border,wrap):
    if (type(width) is not int or type(height) is not int or not 1<=width<=512 or not 1<=height<=512 or
        type(border) is not int or not 1<=border<=128 or type(wrap) is not int or wrap not in (0,1,256,257) or
        len(data)!=width*height*4):raise ValueError('Invalid bounded texture/padding geometry')
    if any(a!=255 for a in data[3::4]):raise ValueError('Neural pilot accepts opaque authored textures only')
    def coord(n,size,clamp):return max(0,min(size-1,n)) if clamp else n%size
    xs=[coord(x-border,width,wrap&1) for x in range(width+2*border)]
    rows={}
    for y in range(height):
        source=data[y*width*4:(y+1)*width*4]
        rows[y]=b''.join(source[x*4:x*4+4] for x in xs)
    return b''.join(rows[coord(y-border,height,(wrap>>8)&1)] for y in range(height+2*border))


def masked_colours(data,width,height,wrap):
    """Extend visible RGB into transparent texels; never generate an alpha mask."""
    if (type(width) is not int or type(height) is not int or not 1<=width<=512 or not 1<=height<=512 or
        type(wrap) is not int or wrap not in (0,1,256,257) or len(data)!=width*height*4):
        raise ValueError('Invalid cutout geometry')
    alpha=set(data[3::4])
    if not any(alpha):raise ValueError('Masked material has no visible pixels')
    if alpha=={255}:return bytes(data)
    owners=[-1]*(width*height);pending=deque()
    for index,a in enumerate(data[3::4]):
        if a>0:owners[index]=index;pending.append(index)
    while pending:
        index=pending.popleft();x=index%width;y=index//width
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if not 0<=nx<width:
                if wrap&1:continue
                nx%=width
            if not 0<=ny<height:
                if wrap&256:continue
                ny%=height
            target=ny*width+nx
            if owners[target]<0:owners[target]=owners[index];pending.append(target)
    return b''.join(bytes(data[index*4:index*4+3])+b'\xff' for index in owners)


def cutout_colours(data,width,height,wrap):
    alpha=set(data[3::4])
    if not alpha.issubset({0,255}) or 255 not in alpha:
        raise ValueError('Cutout requires binary alpha and visible pixels')
    return masked_colours(data,width,height,wrap)


def merge_cutout_colours(restored,scaled_original):
    """Use restored visible RGB with the pinned scaler's exact alpha bytes."""
    if not restored or len(restored)!=len(scaled_original) or len(restored)%4 or any(a!=255 for a in restored[3::4]):
        raise ValueError('Invalid opaque restoration/cutout extent')
    output=bytearray(scaled_original)
    for start in range(0,len(output),4):
        if output[start+3]:output[start:start+3]=restored[start:start+3]
    return bytes(output)
