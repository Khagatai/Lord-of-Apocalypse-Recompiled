"""Build the game-independent, read-only PSMF survey helper from pinned sources."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title

def main():
    folder=ROOT/'private/local-build/movie-helper';folder.mkdir(parents=True,exist_ok=True)
    rt=title.FRAMEWORK/'src/rt';sources=[ROOT/'tools/movie-caption-survey.c',rt/'h264_null.c',rt/'h264_mf.c',rt/'psmf_producer.c']
    output=folder/'movie-survey.exe'
    command=[str(title.SDK/'bin/gcc.exe'),'-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-I'+str(rt),*map(str,sources),'-lmfplat','-lole32','-o',str(output)]
    result=subprocess.run(command,env=title.environment(),capture_output=True,text=True)
    (folder/'build.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr)
    report=dict(status='PASS',sha256=hashlib.sha256(output.read_bytes()).hexdigest(),game_data_embedded=False,sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
