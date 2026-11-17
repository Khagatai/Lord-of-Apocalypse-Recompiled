"""Bounded persistent native image operations; identical to the file-based tools."""
import ctypes,os,subprocess
from pathlib import Path
import title
ROOT=Path(__file__).resolve().parents[1]

class Native:
    def __init__(self,work):
        work=Path(work);gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk';self.dll_path=work/'hd-native.dll'
        command=[str(title.SDK/'bin/gcc.exe'),'-O2','-shared','-ffunction-sections','-fdata-sections','-Wl,--gc-sections,--exclude-all-symbols',
            '-I'+str(gpu),'-I'+str(title.SDK/'include'),'-I'+str(title.FRAMEWORK/'third_party/stb'),
            str(ROOT/'tools/hd-native.c'),str(gpu/'tex_scale.c'),str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),
            '-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(self.dll_path)]
        with (work/'build.log').open('w') as log:subprocess.run(command,env=title.environment(),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        self.search=os.add_dll_directory(str(title.SDK/'bin')) if os.name=='nt' else None
        self.dll=ctypes.CDLL(str(self.dll_path));ptr=ctypes.c_void_p;size=ctypes.c_size_t;integer=ctypes.c_int
        self.dll.loa_scale.argtypes=[ptr,size,integer,integer,integer,integer,ptr,size]
        self.dll.loa_crop.argtypes=[ptr,size,integer,integer,integer,integer,integer,integer,ptr,size]
        self.dll.loa_detail.argtypes=[ptr,size,integer,integer,ptr,size]
        self.dll.loa_pad.argtypes=[ptr,size,integer,integer,integer,integer,ptr,size]
        self.dll.loa_merge.argtypes=[ptr,size,ptr,size,ptr,size]
        for name in ('loa_scale','loa_crop','loa_detail','loa_pad','loa_merge'):getattr(self.dll,name).restype=integer
    def call(self,name,data,length,*args):
        if not isinstance(data,bytes) or not data or not 0<length<=64*1024**2:raise ValueError('Invalid native image buffer')
        source=ctypes.create_string_buffer(data,len(data));out=ctypes.create_string_buffer(length)
        if getattr(self.dll,name)(source,len(data),*args,out,length)!=1:raise ValueError('Native image operation failed: '+name)
        return out.raw
    def scale(self,data,w,h,wrap):return self.call('loa_scale',data,w*h*64,w,h,4,wrap)
    def crop(self,data,ew,eh,x,y,w,h):return self.call('loa_crop',data,w*h*4,ew,eh,x,y,w,h)
    def detail(self,data,w,h):return self.call('loa_detail',data,w*h*4,w,h)
    def pad(self,data,w,h,wrap,border=64):return self.call('loa_pad',data,(w+2*border)*(h+2*border)*4,w,h,border,wrap)
    def merge(self,restored,scaled):
        baseline=ctypes.create_string_buffer(scaled,len(scaled))
        return self.call('loa_merge',restored,len(scaled),baseline,len(scaled))
    def close(self):
        if self.dll:
            import _ctypes
            _ctypes.FreeLibrary(self.dll._handle);self.dll=None
        if self.search:self.search.close();self.search=None
