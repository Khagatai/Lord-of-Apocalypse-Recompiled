"""Strict reader for the measured static boss-caption UNM2 sprite layout.

This is not a general animation decoder. Unsupported transforms/flags fail.
Game resources and assembled reference pixels must remain private.
"""
from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class Sprite:
    x:int
    y:int
    uv:tuple

def caption_sprites(data,width,height):
    if len(data)<52 or data[:4]!=b'UNM2':raise ValueError('Unknown caption layout')
    total,copy_total,count,instances=struct.unpack_from('<4H',data,4)
    offset=struct.unpack_from('<I',data,20)[0]
    if not 0<count<=128 or not 0<instances<=128 or total!=count+instances or total!=copy_total or offset!=52 or offset+total*32>len(data):
        raise ValueError('Unsupported caption table shape')
    result=[]
    prototypes=[]
    for i in range(count):
        a=struct.unpack_from('<2H2h2f4H2I',data,offset+i*32)
        if a[:4]!=(0,0,0,0) or a[4:6]!=(1.,1.) or a[-2:]!=(0xffffffff,32):
            raise ValueError('Unsupported caption prototype')
        prototypes.append(a[6:10])
    for i in range(instances):
        item=data[offset+(count+i)*32:offset+(count+i+1)*32]
        b=struct.unpack('<2H2h2f4H2I',item)
        if b[:2]!=(0,0) or b[4] not in (0.,1.) or b[5]!=1. or b[6:10] not in prototypes or b[-2:]!=(0xffffffff,32):
            raise ValueError('Unsupported caption transform, colour or prototype')
        if b[4]==0.:continue  # Authored hidden glyph; it contributes no pixels.
        u,v,right,bottom=b[6:10]
        if not 0<=u<=right<=width or not 0<=v<=bottom<=height:raise ValueError('Caption UV outside texture')
        if u==right or v==bottom:continue
        if not -1024<=b[2]<=1024 or not -1024<=b[3]<=1024:
            raise ValueError('Caption position exceeds diagnostic bounds')
        result.append(Sprite(b[2],b[3],(u,v,right,bottom)))
    return tuple(result)

def assemble(rgba,width,height,sprites,canvas_width=480,canvas_height=320):
    if len(rgba)!=width*height*4:raise ValueError('RGBA extent differs')
    if not 1<=canvas_width<=2048 or not 1<=canvas_height<=2048:raise ValueError('Invalid reference canvas')
    result=bytearray(canvas_width*canvas_height*4)
    for sprite in sprites:
        u,v,right,bottom=sprite.uv
        for yy in range(bottom-v):
            for xx in range(right-u):
                x,y=sprite.x+xx,sprite.y+yy
                if not 0<=x<canvas_width or not 0<=y<canvas_height:continue
                src=((v+yy)*width+u+xx)*4;dst=(y*canvas_width+x)*4
                # Alpha-over in straight RGBA for reference contact sheets.
                a=rgba[src+3];old=result[dst+3];alpha=a+(old*(255-a)+127)//255
                if not alpha:continue
                for c in range(3):
                    numerator=rgba[src+c]*a+result[dst+c]*old*(255-a)/255
                    result[dst+c]=min(255,round(numerator/alpha))
                result[dst+3]=alpha
    return bytes(result)

def measure_caption_lines(rgba,width,height,rows,canvas_width=480,canvas_height=320,
                          baseline_tolerance=1,minimum_line_gap=6,centre_tolerance=1):
    """Check quantized glyph pixels after placement, excluding runtime animation."""
    if len(rgba)!=width*height*4:raise ValueError('RGBA extent differs')
    lines=[]
    for row in rows:
        boxes=[]
        for sprite in row:
            u,v,right,bottom=sprite.uv
            if not 0<=u<right<=width or not 0<=v<bottom<=height:
                raise ValueError('Caption UV outside texture')
            ink=[(sprite.x+x-u,sprite.y+y-v)
                 for y in range(v,bottom) for x in range(u,right)
                 if rgba[(y*width+x)*4+3]>=32]
            if not ink:raise ValueError('Caption chunk has no visible ink')
            box=(min(x for x,y in ink),min(y for x,y in ink),
                 max(x for x,y in ink)+1,max(y for x,y in ink)+1)
            if box[0]<0 or box[1]<0 or box[2]>canvas_width or box[3]>canvas_height:
                raise ValueError('Visible caption exceeds diagnostic canvas')
            boxes.append(box)
        if not boxes:raise ValueError('Caption line is empty')
        gaps=[b[0]-a[2] for a,b in zip(boxes,boxes[1:])]
        if any(gap<0 for gap in gaps):raise ValueError('Caption chunks overlap or reading order differs')
        baselines=[box[3] for box in boxes]
        error=max(baselines)-min(baselines)
        if error>baseline_tolerance:raise ValueError('Visible caption baselines do not align')
        lines.append(dict(bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),
                                  max(b[2] for b in boxes),max(b[3] for b in boxes)],
                          baseline_error_pixels=error,chunk_gaps=gaps,chunk_bounds=boxes))
    gaps=[b['bounds'][1]-a['bounds'][3] for a,b in zip(lines,lines[1:])]
    if any(gap<minimum_line_gap for gap in gaps):raise ValueError('Caption lines are too close or overlap')
    centres=[(line['bounds'][0]+line['bounds'][2])/2 for line in lines]
    centre_error=max(centres)-min(centres) if centres else 0
    if centre_error>centre_tolerance:raise ValueError('Caption line centres do not align')
    return dict(lines=lines,line_gaps=gaps,canvas=[canvas_width,canvas_height],
                centre_error_pixels=centre_error,
                scope='quantized-static-assembly-not-runtime-animation')


def replace_caption_fields(source,width,height,edits):
    """Change only measured caption UVs/instance positions; retain animation tables."""
    caption_sprites(source,width,height)
    total,_,count,_=struct.unpack_from('<4H',source,4)
    output=bytearray(source);seen=set()
    for edit in edits:
        index=edit['node']
        if type(index) is not int or not 0<=index<total or index in seen:raise ValueError('Invalid or duplicate caption node')
        seen.add(index);offset=52+32*index
        uv=edit['uv']
        if len(uv)!=4 or any(type(x) is not int for x in uv) or not 0<=uv[0]<uv[2]<=width or not 0<=uv[1]<uv[3]<=height:
            raise ValueError('Replacement caption UV outside atlas')
        struct.pack_into('<4H',output,offset+16,*uv)
        if 'position' in edit:
            xy=edit['position']
            if index<count or len(xy)!=2 or any(type(x) is not int or not -1024<=x<=1024 for x in xy):raise ValueError('Invalid caption instance position')
            struct.pack_into('<2h',output,offset+4,*xy)
    # Every authored instance must still use the same prototype's UV, including
    # repeated letters and authored hidden/empty cells.
    mapping={}
    for index in range(count):
        old=struct.unpack_from('<4H',source,52+32*index+16)
        new=struct.unpack_from('<4H',output,52+32*index+16)
        if old in mapping and mapping[old]!=new:raise ValueError('Conflicting shared caption prototype')
        mapping[old]=new
    for index in range(count,total):
        old=struct.unpack_from('<4H',source,52+32*index+16)
        if struct.unpack_from('<4H',output,52+32*index+16)!=mapping[old]:raise ValueError('Caption instance lost its prototype')
    caption_sprites(output,width,height)
    return bytes(output)
