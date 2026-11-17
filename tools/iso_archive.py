"""Read original archive resources directly from a verified ISO without extraction copies."""
import contextlib,hashlib,importlib.util,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ReadonlyExtent:
    def __init__(self,stream,offset,size):
        if offset<0 or size<0:raise ValueError('Negative ISO extent')
        self.stream,self.offset,self.size,self.position=stream,offset,size,0
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        target=offset if whence==0 else self.position+offset if whence==1 else self.size+offset if whence==2 else -1
        if not 0<=target<=self.size:raise ValueError('Read outside archive extent')
        self.position=target;return target
    def read(self,size=-1):
        count=self.size-self.position if size<0 else min(size,self.size-self.position)
        self.stream.seek(self.offset+self.position);raw=self.stream.read(count)
        if len(raw)!=count:raise ValueError('Truncated ISO archive extent')
        self.position+=len(raw);return raw

@contextlib.contextmanager
def original_archive(image,root=ROOT):
    import tomllib
    root=Path(root).resolve();image=Path(image).resolve(strict=True)
    config=tomllib.loads((root/'config/lordofapocalypse.toml').read_text())['disc']
    with image.open('rb') as stream:
        if image.stat().st_size!=config['iso_size'] or hashlib.file_digest(stream,'sha256').hexdigest()!=config['iso_sha256']:raise ValueError('Wrong original ISO')
        stamp=image.stat();stream.seek(0)
        spec=importlib.util.spec_from_file_location('iso_archive_survey',root/'tools/survey-disc.py');survey=importlib.util.module_from_spec(spec);spec.loader.exec_module(survey)
        files=survey.ISO(stream).files()
        index=files['PSP_GAME/USRDIR/UPDATA/REGFILE.RZL'];data=files['PSP_GAME/USRDIR/UPDATA/REGFILE.RZP']
        index_view=ReadonlyExtent(stream,index['lba']*survey.SECTOR,index['size']);raw=index_view.read()
        yield raw,ReadonlyExtent(stream,data['lba']*survey.SECTOR,data['size'])
        final=image.stat()
        if (stamp.st_size,stamp.st_mtime_ns)!=(final.st_size,final.st_mtime_ns):raise ValueError('Original ISO changed during archive reading')
