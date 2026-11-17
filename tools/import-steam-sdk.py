"""Import a user-downloaded official Steamworks SDK ZIP into ignored local tools."""
import argparse,hashlib,json,stat,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path);args=parser.parse_args()
    archive=args.archive.resolve();destination=ROOT/'private/tools/steamworks-sdk'
    with zipfile.ZipFile(archive) as source:
        entries=source.infolist()
        if len(entries)>10000 or sum(i.file_size for i in entries)>256*1024*1024:raise ValueError('Unexpected SDK archive size.')
        names={i.filename for i in entries}
        for required in ('sdk/public/steam/steam_api.h','sdk/redistributable_bin/win64/steam_api64.dll','sdk/redistributable_bin/win64/steam_api64.lib'):
            if required not in names:raise ValueError('Not the expected Steamworks SDK layout.')
        files={}
        for entry in entries:
            name=PurePosixPath(entry.filename)
            if not name.parts or name.parts[0]!='sdk' or '..' in name.parts or '\\' in entry.filename or name.is_absolute() or stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Unsafe archive member.')
            if entry.is_dir():continue
            target=destination.joinpath(*name.parts[1:]).resolve()
            if not target.is_relative_to(destination.resolve()):raise ValueError('SDK archive path escaped.')
            target.parent.mkdir(parents=True,exist_ok=True);data=source.read(entry)
            if not target.exists() or target.read_bytes()!=data:target.write_bytes(data)
            files[target.relative_to(destination).as_posix()]=hashlib.sha256(data).hexdigest()
    (destination/'intake.json').write_text(json.dumps(dict(archive_name=archive.name,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=files),indent=2)+'\n')
    print(f'Imported {len(files)} SDK files into ignored {destination}. Original ZIP preserved; nothing uploaded.')
if __name__=='__main__':main()
