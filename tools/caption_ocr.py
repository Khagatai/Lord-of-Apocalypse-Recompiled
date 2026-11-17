"""Local bitmap-caption preprocessing and installed Tesseract C-API bridge."""
import ctypes,os,struct,zlib

def read_rgba_png(data):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Not PNG')
    pos=8;compressed=bytearray();geometry=None
    while pos<len(data):
        size=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8];body=data[pos+8:pos+8+size]
        if pos+size+12>len(data) or zlib.crc32(kind+body)!=struct.unpack_from('>I',data,pos+8+size)[0]:raise ValueError('Corrupt PNG chunk')
        if kind==b'IHDR':
            w,h,depth,color,compression,filtering,interlace=struct.unpack('>2I5B',body)
            if not 1<=w<=1024 or not 1<=h<=1024 or (depth,color,compression,filtering,interlace)!=(8,6,0,0,0):raise ValueError('Unsupported caption PNG')
            geometry=w,h
        if kind==b'IDAT':compressed.extend(body)
        pos+=size+12
        if kind==b'IEND':break
    if geometry is None:raise ValueError('PNG has no geometry')
    w,h=geometry;scan=zlib.decompress(compressed)
    if len(scan)!=(w*4+1)*h:raise ValueError('PNG scan extent differs')
    rgba=bytearray()
    for y in range(h):
        start=y*(w*4+1)
        if scan[start]!=0:raise ValueError('Only owned unfiltered survey PNGs are accepted')
        rgba.extend(scan[start+1:start+1+w*4])
    return w,h,bytes(rgba)

def caption_mask(width,height,rgba,factor=3,padding=12,text_only=False):
    if len(rgba)!=width*height*4 or not 1<=factor<=4:raise ValueError('Invalid caption extent')
    w=width*factor+padding*2;h=height*factor+padding*2;output=bytearray(b'\xff'*(w*h))
    for y in range(height):
        row=bytearray()
        for x in range(width):
            r,g,b,a=rgba[(y*width+x)*4:(y*width+x)*4+4]
            # Keep pale neutral caption ink; suppress coloured movie backgrounds.
            value=255-min(r,g,b) if min(r,g,b)>=145 and max(r,g,b)-min(r,g,b)<=60 else 255
            if text_only and value<255:
                if (height>=64 and y<16) or (width>=128 and not 16<=x<width-16):value=255
                else:
                    outlined=False
                    for dy in (-2,-1,0,1,2):
                        for dx in (-2,-1,0,1,2):
                            if not 0<=x+dx<width or not 0<=y+dy<height:continue
                            offset=((y+dy)*width+x+dx)*4
                            if max(rgba[offset:offset+3])<=100:outlined=True;break
                        if outlined:break
                    if not outlined:value=255
            row.extend(bytes([value])*factor)
        for yy in range(factor):output[(padding+y*factor+yy)*w+padding:(padding+y*factor+yy)*w+padding+len(row)]=row
    return w,h,output

class Engine:
    def __init__(self,dll,model_folder):
        self.directory=os.add_dll_directory(str(dll.parent))
        self.lib=ctypes.CDLL(str(dll));lib=self.lib
        signatures={
            'TessBaseAPICreate':([],ctypes.c_void_p),
            'TessBaseAPIInit3':([ctypes.c_void_p,ctypes.c_char_p,ctypes.c_char_p],ctypes.c_int),
            'TessBaseAPISetPageSegMode':([ctypes.c_void_p,ctypes.c_int],None),
            'TessBaseAPISetSourceResolution':([ctypes.c_void_p,ctypes.c_int],None),
            'TessBaseAPISetImage':([ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int],None),
            'TessBaseAPIGetUTF8Text':([ctypes.c_void_p],ctypes.c_void_p),
            'TessBaseAPIMeanTextConf':([ctypes.c_void_p],ctypes.c_int),
            'TessDeleteText':([ctypes.c_void_p],None),
            'TessBaseAPIClear':([ctypes.c_void_p],None),
            'TessBaseAPIDelete':([ctypes.c_void_p],None),
        }
        for name,(arguments,result) in signatures.items():
            fn=getattr(lib,name);fn.argtypes=arguments;fn.restype=result
        self.api=lib.TessBaseAPICreate()
        if not self.api or lib.TessBaseAPIInit3(self.api,str(model_folder).encode('utf-8'),b'jpn'):
            self.close();raise RuntimeError('Installed Japanese OCR model could not initialize')
        lib.TessBaseAPISetPageSegMode(self.api,6)

    def recognize(self,width,height,gray):
        buffer=ctypes.create_string_buffer(bytes(gray));lib=self.lib
        lib.TessBaseAPISetImage(self.api,buffer,width,height,1,width)
        lib.TessBaseAPISetSourceResolution(self.api,300)
        pointer=lib.TessBaseAPIGetUTF8Text(self.api)
        try:text=ctypes.string_at(pointer).decode('utf-8').strip() if pointer else ''
        finally:
            if pointer:lib.TessDeleteText(pointer)
        confidence=lib.TessBaseAPIMeanTextConf(self.api);lib.TessBaseAPIClear(self.api)
        return text,confidence

    def close(self):
        if getattr(self,'api',None):self.lib.TessBaseAPIDelete(self.api);self.api=None
        if getattr(self,'directory',None):self.directory.close();self.directory=None
