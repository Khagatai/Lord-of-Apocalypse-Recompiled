"""Read-only workspace storage inventory. Never deletes, moves, or hashes game data."""
import argparse,collections,heapq,json,os,stat,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'private/storage-current-audit.json');args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private'):parser.error('Audit reports must remain private.')
    base=ROOT.parent.resolve();directories={};extensions=collections.defaultdict(lambda:[0,0]);largest=[];errors=[];skipped=[];count=0;started=time.monotonic()
    def walk(folder):
        nonlocal count
        total=files=0
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    try:
                        info=entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:
                            skipped.append(os.path.relpath(entry.path,base));continue
                        if stat.S_ISDIR(info.st_mode):
                            size,n=walk(entry.path);total+=size;files+=n
                        elif stat.S_ISREG(info.st_mode):
                            size=info.st_size;total+=size;files+=1;count+=1
                            relative=os.path.relpath(entry.path,base).replace('\\','/');suffix=Path(entry.name).suffix.lower() or '[no extension]'
                            extensions[suffix][0]+=size;extensions[suffix][1]+=1
                            record=(size,relative,int(info.st_mtime_ns))
                            if len(largest)<160:heapq.heappush(largest,record)
                            elif size>largest[0][0]:heapq.heapreplace(largest,record)
                    except OSError as error:errors.append(dict(path=entry.path,error=str(error)))
        except OSError as error:errors.append(dict(path=str(folder),error=str(error)))
        relative=os.path.relpath(folder,base).replace('\\','/')
        directories[relative]=dict(bytes=total,files=files)
        return total,files
    total,files=walk(base)
    report=dict(scope='metadata-only-read-only-no-cleanup-performed',root=str(base),bytes=total,files=files,elapsed_seconds=round(time.monotonic()-started,3),
                sizes_are='logical file bytes; hardlinks/compression/allocation not deduplicated',directories=directories,
                extensions=dict(sorted(extensions.items(),key=lambda item:item[1][0],reverse=True)),
                largest_files=[dict(bytes=n,path=p,mtime_ns=t) for n,p,t in sorted(largest,reverse=True)],errors=errors,skipped_reparse_points=skipped)
    output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    private_key=ROOT.name+'/private'
    print(json.dumps(dict(total_gib=round(total/2**30,3),files=files,scan_errors=len(errors),skipped_reparse_points=len(skipped),
        largest_private_folders=[dict(path=p.removeprefix(private_key+'/'),gib=round(v['bytes']/2**30,3),files=v['files']) for p,v in sorted(directories.items(),key=lambda item:item[1]['bytes'],reverse=True) if p.startswith(private_key+'/') and len(p.split('/'))==3][:24],
        largest_files=report['largest_files'][:18],report=str(output)),indent=2))
if __name__=='__main__':main()
