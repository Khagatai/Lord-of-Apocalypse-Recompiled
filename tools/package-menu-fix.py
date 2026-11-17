"""Create a small dependency-only repair ZIP; contains no game-derived payloads."""
import argparse,hashlib,importlib.util,json,os,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_test_build',ROOT/'tools/package-test-build.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    output=args.output.resolve()
    if output.exists():raise FileExistsError('Refusing to replace an existing repair ZIP')
    sdk=package.SDK
    files=package.dll_closure([sdk/n for n in package.DYNAMIC_DLLS],sdk,Path(os.environ['SystemRoot'])/'System32')
    for name in package.MENU_LICENSES:
        folder=sdk.parent/'share/licenses'/name
        if not folder.is_dir():raise FileNotFoundError('Missing licence: '+name)
        files.update(p for p in folder.rglob('*') if p.is_file())
    fonts=ROOT/'external/nakagawa-recomp/assets/fonts/ui'
    files.update(p for p in fonts.rglob('*') if p.is_file())
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.zip.part')
    if temporary.exists():raise FileExistsError('Unfinished repair ZIP already exists')
    records=[]
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files):
            name=path.relative_to(ROOT).as_posix()
            if path.is_symlink() or not (name.startswith('private/toolchain/') or name.startswith('external/nakagawa-recomp/assets/fonts/ui/')):
                raise ValueError('Unexpected repair payload: '+name)
            archive.write(path,name)
            records.append(dict(path=name,size=path.stat().st_size,sha256=package.sha(path)))
        archive.writestr('READ-ME-MENU-FIX.txt',
            'Close the game and launcher.\n'
            'Extract this ZIP INTO the folder containing Start-Game.cmd.\n'
            'Merge the private and external folders and replace matching DLL/font files.\n'
            'Start the game normally. F1 or Escape should now draw the menu.\n'
            'Do not copy SDL3_ttf.dll alone: its dependencies must be installed together.\n'
            'This repair contains runtime libraries, public UI fonts and licence notices.\n'
            'It contains no game files, saves, settings, ISO or replacement game executable.\n')
        archive.writestr('MENU-FIX-MANIFEST.json',json.dumps(dict(schema=1,reason='missing dynamic SDL3_ttf menu dependency and transitive DLLs',files=records),indent=2))
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip():raise RuntimeError('Repair ZIP failed CRC verification')
    os.replace(temporary,output)
    digest=package.sha(output)
    output.with_suffix('.zip.sha256.txt').write_text(digest+'  '+output.name+'\n')
    print(json.dumps(dict(zip=str(output),size=output.stat().st_size,sha256=digest,files=len(records)+2,crc_verified=True),indent=2))

if __name__=='__main__':main()
