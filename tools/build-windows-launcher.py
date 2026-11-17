"""Build the small Windows GUI launcher; no game payload or Python is embedded."""
import argparse,hashlib,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(output,compiler=None,icon=None):
    output=Path(output).resolve()
    compiler=Path(compiler) if compiler else ROOT/'private/toolchain/prerequisites/msys64/ucrt64/bin/gcc.exe'
    if not compiler.is_file():
        found=shutil.which('gcc')
        if not found:raise FileNotFoundError('A local Windows x64 GCC compiler is needed to rebuild the launcher.')
        compiler=Path(found)
    output.parent.mkdir(parents=True,exist_ok=True)
    command=[str(compiler),'-std=c11','-O2','-Wall','-Wextra','-municode','-mwindows','-static-libgcc','-s',
        '-Wl,--no-insert-timestamp',str(ROOT/'tools/windows-launcher.c'),'-o',str(output),'-lshell32','-lgdi32','-luser32']
    env=dict(os.environ);env['PATH']=str(compiler.parent)+os.pathsep+env.get('PATH','')
    icon=Path(icon) if icon else ROOT/'private/branding/launcher.ico'
    if icon.is_file():
        resource=ROOT/'private/launcher/icon.rc';resource.parent.mkdir(parents=True,exist_ok=True)
        resource.write_text('1 ICON "'+icon.resolve().as_posix()+'"\n',encoding='utf-8')
        obj=resource.with_suffix('.o')
        result=subprocess.run([str(compiler.with_name('windres.exe')),'--preprocessor=gcc.exe',
            '--preprocessor-arg=-E','--preprocessor-arg=-xc','--preprocessor-arg=-DRC_INVOKED',
            '-i',str(resource),'-o',str(obj)],env=env,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        command.insert(command.index('-o'),str(obj))
    subprocess.run(command,env=env,check=True,capture_output=True,text=True)
    raw=output.read_bytes();pe=int.from_bytes(raw[0x3c:0x40],'little')
    if raw[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',raw,pe+4)[0]!=0x8664:raise ValueError('Expected AMD64 PE')
    if struct.unpack_from('<H',raw,pe+24+68)[0]!=2:raise ValueError('Expected Windows GUI subsystem')
    return dict(path=str(output),size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),subsystem='Windows GUI',machine='AMD64',game_data_embedded=False,icon_embedded=icon.is_file())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'LordOfApocalypse.exe');p.add_argument('--compiler',type=Path);p.add_argument('--icon',type=Path);a=p.parse_args()
    print(json.dumps(build(a.output,a.compiler,a.icon),indent=2))
if __name__=='__main__':main()
