"""Install checksum-verified MSYS2 OCR runtime in private/, without game inputs."""
import argparse,hashlib,io,json,re,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def install(package,output):
    if not re.fullmatch(r'mingw-w64-ucrt-x86_64-[a-z0-9+-]+',package):raise ValueError('Unsupported package name')
    page='https://packages.msys2.org/packages/'+package
    html=urllib.request.urlopen(page,timeout=40).read().decode('utf-8')
    urls=re.findall(r'https://mirror\.msys2\.org/mingw/ucrt64/[^"<> ]+\.pkg\.tar\.zst',html)
    urls=[url for url in urls if url.rsplit('/',1)[-1].startswith(package+'-')]
    hashes=re.findall(r'\b[a-f0-9]{64}\b',html)
    if not urls or len(set(hashes))!=1:raise ValueError('Ambiguous package metadata')
    url=urls[0];expected=hashes[0]
    data=urllib.request.urlopen(url,timeout=90).read()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Package checksum mismatch')
    paths=[]
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:zst') as archive:
        for member in archive:
            path=Path(member.name)
            if member.isfile() and not path.is_absolute() and '..' not in path.parts:
                wanted=(path.parent.as_posix()=='ucrt64/bin' and (path.suffix=='.dll' or path.name=='tesseract.exe')) or 'share/tessdata' in path.as_posix() or 'share/licenses' in path.as_posix()
                if wanted:
                    target=(output/path).resolve()
                    if not target.is_relative_to(output.resolve()):raise ValueError('Package path escapes output')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    raw=archive.extractfile(member).read();target.write_bytes(raw)
                    paths.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest()))
    return dict(package=package,metadata_url=page,url=url,sha256=expected,files=paths)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('packages',nargs='+')
    args=parser.parse_args();output=ROOT/'private/tools/local-ocr';output.mkdir(parents=True,exist_ok=True)
    path=output/'packages-lock.json';records=json.loads(path.read_text()) if path.exists() else []
    for package in args.packages:
        record=install(package,output);records=[r for r in records if r['package']!=package]+[record]
        path.write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(dict(package=package,files=len(record['files']),sha256=record['sha256'])),flush=True)

if __name__=='__main__':main()
