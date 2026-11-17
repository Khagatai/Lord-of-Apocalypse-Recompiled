"""Package an explicit allowlist of room-server source; no game/client data."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'private/online-server';folder.mkdir(exist_ok=True)
    contents={'room_service.py':(ROOT/'tools/room_service.py').read_bytes(),'ONLINE_SERVER.md':(ROOT/'docs/ONLINE_SERVER.md').read_bytes(),
              'client-example.json':b'{"url":"https://YOUR_ROOM_SERVICE_DOMAIN"}\n'}
    manifest={name:hashlib.sha256(data).hexdigest() for name,data in contents.items()}
    contents['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    path=folder/'loa-room-service.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in contents.items():archive.writestr(name,data)
    (folder/'package.json').write_text(json.dumps(dict(path=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),files=manifest),indent=2)+'\n')
    print(f'Prepared {path} ({path.stat().st_size} bytes); source-only server files, not deployed.')
if __name__=='__main__':main()
