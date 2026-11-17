"""Package a local tester runtime update without ISOs, saves or preferences."""
import argparse,hashlib,json,os,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    output=a.output.resolve()
    if output.exists():raise FileExistsError('Refusing to replace existing runtime update')
    release=ROOT/'private/native-release/lordofapocalypse'
    record=json.loads((release/'host-ui-build.json').read_text())
    if sha(release/'lordofapocalypse.exe')!=record['executable_sha256']:raise ValueError('Runtime build differs')
    if sha(release/'lordofapocalypse_image.bin')!=record['flat_image_sha256']:raise ValueError('Guest image differs')
    names=['private/native-release/lordofapocalypse/'+n for n in ('lordofapocalypse.exe','host-ui-build.json')]
    names+=['tools/'+n for n in ('coop_hle.c','coop_service_wait.h','coop-runtime.mk','title.py')]
    output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_suffix('.zip.part')
    if temporary.exists():raise FileExistsError('Unfinished runtime update exists')
    records=[]
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in names:
            path=ROOT/name;z.write(path,name);records.append(dict(path=name,size=path.stat().st_size,sha256=sha(path)))
        z.writestr('COOP-UPDATE-MANIFEST.json',json.dumps(dict(schema=1,framework_commit=record['framework_commit'],expected_guest_image_sha256=record['flat_image_sha256'],files=records,full_multiplayer_acceptance=False),indent=2))
        z.writestr('READ-ME-COOP-FIX.txt',
            'Close the game and launcher on BOTH PCs.\n'
            'Extract this ZIP INTO the folder containing Start-Game.cmd.\n'
            'Merge folders and replace matching files. Both players need the update.\n'
            'Saves, preferences, ISO and HD assets are not included or reset.\n'
            'Start through Start-Game.cmd. Keep both PCs at 30 FPS for the first retest.\n'
            'F1 -> Networking -> Steam: create/join the lobby. Check confirmed peers.\n'
            'Both players should close F1, enter the guild hall and create/join a game room.\n'
            'Then repeat with BOTH PCs at 60 FPS after restarting.\n'
            'Actual shared missions, combat, rewards and save/reload remain acceptance gates.\n'
            'This update addresses host networking poll starvation; it is a test candidate.\n'
            'The existing menu dependency fix is still required for older installations.\n')
    with zipfile.ZipFile(temporary) as z:
        if z.testzip():raise RuntimeError('Runtime update ZIP is corrupt')
    os.replace(temporary,output);digest=sha(output)
    output.with_suffix('.zip.sha256.txt').write_text(digest+'  '+output.name+'\n')
    print(json.dumps(dict(zip=str(output),size=output.stat().st_size,sha256=digest,executable_sha256=record['executable_sha256'],crc_verified=True),indent=2))
if __name__=='__main__':main()
