"""Build the small Windows online installer from verified release asset hashes."""
import argparse,hashlib,json,os,subprocess,zipfile
from pathlib import Path
from player_update import version_key
ROOT=Path(__file__).resolve().parents[1]
CSC=Path(os.environ.get('SystemRoot','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
def build(manifest,output,tests=None):
    args=[str(CSC),'/nologo','/optimize+','/platform:x64','/target:'+('exe' if tests else 'winexe'),'/out:'+str(output),
          '/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll']
    if tests:args+=['/define:INSTALLER_TEST',str(tests)]
    else:args+=['/resource:'+str(manifest)+',release.json']
    icon=ROOT/'private/branding/launcher.ico'
    if icon.is_file():args+=['/win32icon:'+str(icon)]
    args+=[str(ROOT/'tools/windows-online-setup.cs')]
    result=subprocess.run(args,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path,default=ROOT/'private/distribution-test/github-assets-result.json')
    parser.add_argument('--local-tester-candidate',action='store_true',help='Explicitly build against an uncleared local tester payload; never authorizes upload')
    args=parser.parse_args()
    report=json.loads(args.report.read_text());assets=[];expanded=0;longest=0
    version=report.get('version','0.9.0-beta.1')
    version_key(version)
    if version.startswith('v'):raise ValueError('Installer version must omit the leading v')
    if report.get('builds_native_game_locally') is True:
        if report.get('iso_only_publication_checks_complete') is not True or report.get('clean_install_verified') is not True or report.get('game_payloads_included') is not False:
            raise RuntimeError('Release installer blocked: ISO-only payload, complete first-run generation and clean-install checks must pass before preparing the publishing installer.')
    elif report.get('public_distribution_review_complete') is not True and not args.local_tester_candidate:
        raise RuntimeError('Release installer blocked: the current payload is an uncleared local tester candidate containing game-derived files. Complete the ISO-only generation pipeline first. --local-tester-candidate is for explicit private testing only.')
    for record in report['assets']:
        path=Path(record['path'])
        with path.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==record['sha256']
        assets.append(dict(name=path.name,size=record['size'],sha256=record['sha256'],url=f'https://github.com/Khagatai/Lord-of-Apocalypse-Recompiled/releases/download/v{version}/'+path.name))
        with zipfile.ZipFile(path) as z:
            expanded+=sum(i.file_size for i in z.infolist())
            longest=max(longest,max(len(i.filename.removeprefix('LordOfApocalypse-Recomp/')) for i in z.infolist()))
    manifest=ROOT/'private/distribution-test/online-installer.json'
    manifest.write_text(json.dumps(dict(schema=1,version=version,expanded_size=expanded+1024*1024,max_relative_path=longest,assets=assets,
        local_build_extra_bytes=14*1024**3 if report.get('builds_native_game_locally') else 0),indent=2))
    output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True);build(manifest,output)
    source=output.with_name('LordOfApocalypse-Setup-Source.zip')
    with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT/'tools/windows-online-setup.cs','windows-online-setup.cs');z.write(ROOT/'tools/build-online-setup.py','build-online-setup.py');z.write(ROOT/'tools/player_update.py','player_update.py');z.write(manifest,'release.json');z.write(ROOT/'LICENSE','LICENSE')
        icon=ROOT/'private/branding/launcher.ico'
        if icon.is_file():z.write(icon,'branding/launcher.ico')
        z.writestr('BUILD.txt','Windows .NET Framework 4.x C# compiler; no game code is embedded.\nCompile windows-online-setup.cs as x64 winexe, embed release.json named release.json,\nand reference System.Windows.Forms, System.Drawing, System.Web.Extensions,\nSystem.IO.Compression and System.IO.Compression.FileSystem.\nGPL-3.0-or-later.\n')
    if report.get('builds_native_game_locally') is True:
        (output.parent/'Launcher-Update-v1.txt').write_text(f'Lord of Apocalypse Recompiled v{version}\nSupports verified in-place updates through Setup.exe.\n',encoding='utf-8')
    print(json.dumps(dict(installer=str(output),size=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),source=str(source),version=version,payload_assets=len(assets),public_downloads_tested=False),indent=2))
if __name__=='__main__':main()
