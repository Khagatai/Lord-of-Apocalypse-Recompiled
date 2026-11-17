"""Memory-bounded caches/batches. Scheduling never changes pixel processing."""
from collections import OrderedDict
import hashlib,json,re

def content_token(baseline,padded,model,detail,w,h):
    # Equal RGBA byte streams can describe differently shaped images.
    return hashlib.sha256(json.dumps(dict(dimensions=[w*4,h*4],baseline=hashlib.sha256(baseline).hexdigest(),
        padded=hashlib.sha256(padded).hexdigest() if padded else None,model=model,detail=detail),sort_keys=True).encode()).hexdigest()

class ByteCache:
    def __init__(self,limit):self.limit=limit;self.size=0;self.entries=OrderedDict();self.hits=0;self.misses=0
    def get(self,key,load):
        if key in self.entries:
            self.hits+=1;value=self.entries.pop(key);self.entries[key]=value;return value
        self.misses+=1;value=load()
        if len(value)<=self.limit:
            while self.entries and self.size+len(value)>self.limit:
                _,old=self.entries.popitem(last=False);self.size-=len(old)
            self.entries[key]=value;self.size+=len(value)
        return value

def batches(jobs,order,max_jobs=64,budget=256*1024**2):
    if not 1<=max_jobs<=128 or budget<64*1024**2:raise ValueError('Invalid bounded HD batch')
    batch=[];used=0
    for identity in order:
        job=jobs[identity]
        cost=sum(w*h*64+((w+128)*(h+128)*64 if job['method']=='restore' else 0) for w,h in job['dimensions'])
        if batch and (len(batch)>=max_jobs or used+cost>budget):yield batch;batch=[];used=0
        batch.append(identity);used+=cost
    if batch:yield batch

def prune_orphans(pack,used):
    """Only after final validation: remove generated PNGs with no mapping."""
    if not (pack/'owner.json').is_file():raise ValueError('Unowned generated pack')
    removed=[]
    for path in pack.iterdir():
        if path.name in used or not re.fullmatch(r'tex-[0-9]{5}-[0-7]\.png',path.name):continue
        if path.is_symlink() or not path.is_file() or path.resolve().parent!=pack.resolve():raise ValueError('Unsafe orphan texture path')
        data=path.read_bytes();removed.append(dict(file=path.name,size=len(data),sha256=hashlib.sha256(data).hexdigest()));path.unlink()
    return removed
