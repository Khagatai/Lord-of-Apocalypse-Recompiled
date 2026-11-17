"""Export development source only; preserve the destination README and Git history."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXTENSIONS={'.py','.c','.cpp','.cs','.h','.mk','.ps1','.json','.toml','.ini','.manifest','.txt','.md'}
HISTORY={'AGENTS.MD','CLAUDE.MD','GEMINI.MD','STATUS.MD','FINDINGS.MD','PLAN.MD','INTAKE.MD','UPSTREAM.MD'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def selected():
    files={name:ROOT/name for name in ('README.md','LICENSE','CREDITS.md','.gitignore','.gitmodules')}
    for folder in ('config','tools','tests','docs'):
        for path in (ROOT/folder).rglob('*'):
            if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts:continue
            if path.name.upper() in HISTORY or path.suffix not in EXTENSIONS:continue
            if any(part in ('.agents','.codex','.github') for part in path.parts):continue
            files[path.relative_to(ROOT).as_posix()]=path
    for path in (ROOT/'.github/ISSUE_TEMPLATE').glob('*.yml'):
        if path.is_file() and not path.is_symlink():files[path.relative_to(ROOT).as_posix()]=path
    return files

def export(destination):
    destination=destination.resolve()
    if destination==ROOT or destination.is_relative_to(ROOT):raise ValueError('Use a separate export destination')
    destination.mkdir(parents=True,exist_ok=True)
    if destination.is_symlink():raise ValueError('Export must not be a symlink')
    readme=destination/'README.md';before=sha(readme) if readme.exists() else None
    records=[]
    for name,source in sorted(selected().items()):
        target=destination/name
        if not target.resolve().is_relative_to(destination):raise ValueError('Unsafe export path')
        if name=='README.md' and target.exists():pass
        else:
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        records.append(dict(path=name,sha256=sha(target),size=target.stat().st_size))
    # Remove only agent instructions/history documents explicitly excluded here.
    removed=[]
    for path in destination.rglob('*.md'):
        relative=path.relative_to(destination)
        if '.git' in relative.parts or relative.parts[0]=='external':continue
        if path.name.upper() in HISTORY:
            if not path.resolve().is_relative_to(destination) or path.is_symlink():raise ValueError('Unsafe note path')
            path.unlink();removed.append(path.relative_to(destination).as_posix())
    git=['git','-c','safe.directory='+destination.as_posix(),'-C',str(destination)]
    if not (destination/'.git').exists():subprocess.run(git+['init'],check=True,capture_output=True)
    tracked=subprocess.check_output(git+['ls-files','-z'],text=True).split('\0')
    tracked_notes=[name for name in tracked if name and not name.startswith('external/') and Path(name).name.upper() in HISTORY]
    for name in tracked_notes:
        path=destination/name
        if path.exists():
            if path.is_symlink() or not path.resolve().is_relative_to(destination):raise ValueError('Unsafe indexed note path')
            path.unlink()
        if name not in removed:removed.append(name)
    if tracked_notes:subprocess.run(git+['add','-u','--',*tracked_notes],check=True,capture_output=True)
    subprocess.run(git+['add','--',*(row['path'] for row in records)],check=True,capture_output=True)
    import tomllib
    config=tomllib.loads((ROOT/'config/lordofapocalypse.toml').read_text())
    pins={'external/nakagawa-recomp':config['runtime']['commit'],'external/psp-recomp':config['previous_runtime']['commit']}
    for name,pin in pins.items():
        (destination/name).mkdir(parents=True,exist_ok=True)
        subprocess.run(git+['update-index','--add','--cacheinfo','160000,'+pin+','+name],check=True,capture_output=True)
    after=sha(readme)
    if before and after!=before:raise ValueError('Destination README changed')
    report=dict(status='PASS',destination=str(destination),source_files=len(records),files=records,
                pinned_frameworks=pins,existing_README_preserved=before is not None,README_sha256=after,
                source_README_unchanged=sha(ROOT/'README.md')==next(r['sha256'] for r in records if r['path']=='README.md'),
                excluded_notes=sorted(HISTORY),removed_notes=removed,committed=False,pushed=False,
                excludes=['game files','generated game C','ISOs','saves','personal settings','SDKs','toolchains','binaries','local logo artwork'])
    work=ROOT/'private/distribution-test';work.mkdir(parents=True,exist_ok=True)
    (work/'source-export-result.json').write_text(json.dumps(report,indent=2)+'\n')
    return {k:v for k,v in report.items() if k!='files'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',type=Path,required=True)
    print(json.dumps(export(parser.parse_args().destination),indent=2))
