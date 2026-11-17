"""Local PNG verification cache backed by Windows file IDs and change times.

Metadata and INI semantics are still checked on every launch. Unsupported
directory queries fall back to full PNG verification; cache writes are optional.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile

class PackChangedDuringVerification(ValueError):
    """A directory identity changed during this verification pass."""

def directory_snapshot(folder):
    """FILE_ID_BOTH_DIR_INFO includes ChangeTime even when LastWriteTime is restored.

    Layout/API: learn.microsoft.com/windows/win32/api/winbase/ns-winbase-file_id_both_dir_info
    Directory attributes and reparse points are refused by the PNG reader below.
    """
    if os.name!='nt':raise OSError('Windows directory identities unavailable')
    from ctypes import wintypes as w
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.CreateFileW.argtypes=(w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE)
    api.CreateFileW.restype=w.HANDLE
    api.GetFileInformationByHandleEx.argtypes=(w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD)
    api.GetFileInformationByHandleEx.restype=w.BOOL
    api.CloseHandle.argtypes=(w.HANDLE,)
    handle=api.CreateFileW(str(folder),1,7,None,3,0x02000000,None)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    result={};buffer=ctypes.create_string_buffer(65536)
    try:
        first=True
        while True:
            if not api.GetFileInformationByHandleEx(handle,11 if first else 10,buffer,len(buffer)):
                error=ctypes.get_last_error()
                if error==18:break
                raise ctypes.WinError(error)
            first=False;offset=0;raw=buffer.raw
            while True:
                next_offset=struct.unpack_from('<I',raw,offset)[0]
                created,access,written,changed,size=struct.unpack_from('<qqqqq',raw,offset+8)
                attrs,length=struct.unpack_from('<II',raw,offset+56)
                file_id=struct.unpack_from('<Q',raw,offset+96)[0]
                if length%2 or offset+104+length>len(raw):raise OSError('Malformed directory record')
                name=raw[offset+104:offset+104+length].decode('utf-16-le',errors='surrogatepass')
                result[name]=[created,written,changed,size,file_id,attrs]
                if not next_offset:break
                if next_offset<104 or offset+next_offset>=len(raw):raise OSError('Malformed directory chain')
                offset+=next_offset
    finally:api.CloseHandle(handle)
    return result

def validator_digest():
    here=Path(__file__).resolve().parent
    h=hashlib.sha256()
    for name in ('texture_cache.py','texture_pack.py','sampler_pack.py'):
        h.update(name.encode());h.update((here/name).read_bytes())
    return h.hexdigest()

class PackCache:
    def __init__(self,folder,path):
        self.folder=Path(folder);self.path=Path(path);self.version=validator_digest()
        self.old={};self.records={};self.hits=0;self.hashed=0;self.supported=True;self.warning=None
        try:self.snapshot=directory_snapshot(self.folder)
        except OSError:self.snapshot={};self.supported=False
        try:
            if self.path.stat().st_size>(16<<20):raise ValueError('Oversized cache')
            saved=json.loads(self.path.read_bytes())
            if (saved.get('schema')==1 and saved.get('validator')==self.version
                and saved.get('folder')==str(self.folder) and isinstance(saved.get('files'),dict)):
                self.old=saved['files']
        except (OSError,ValueError,TypeError,AttributeError):pass

    def png(self,name,digest,dimensions):
        path=self.folder/name
        if self.supported:
            identity=self.snapshot.get(name)
            if identity is None or identity[-1]&0x410:raise ValueError('Mip PNG missing or reparse point refused')
            record=[identity,*dimensions,digest]
            if self.old.get(name)==record:
                self.hits+=1;self.records[name]=record;return
        else:
            st=path.lstat()
            if not path.is_file() or path.is_symlink() or getattr(st,'st_file_attributes',0)&0x400:
                raise ValueError('Mip PNG missing or reparse point refused')
            record=None
        data=path.read_bytes();self.hashed+=1
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Mip PNG missing or hash mismatch')
        if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Mip image is not a PNG')
        if struct.unpack_from('>II',data,16)!=tuple(dimensions):raise ValueError('Mip PNG dimensions differ')
        if record is not None:self.records[name]=record

    def finish(self):
        if self.supported:
            again=directory_snapshot(self.folder)
            if any(again.get(name)!=record[0] for name,record in self.records.items()):
                raise PackChangedDuringVerification('HD pack changed during verification; retry after the update finishes')
            if self.old==self.records:return self.statistics()
            value=dict(schema=1,validator=self.version,folder=str(self.folder),files=self.records)
            temporary=None
            try:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,suffix='.tmp',delete=False) as stream:
                    temporary=Path(stream.name);json.dump(value,stream,separators=(',',':'))
                    stream.flush();os.fsync(stream.fileno())
                os.replace(temporary,self.path);temporary=None
            except OSError as error:self.warning=str(error)
            finally:
                if temporary is not None:temporary.unlink(missing_ok=True)
        return self.statistics()

    def statistics(self):
        return dict(unchanged_pngs_reused=self.hits,pngs_hashed=self.hashed,metadata_supported=self.supported,warning=self.warning)
