"""Compile the local game-independent PRX decryptor with the portable GCC toolchain."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

def main():
    from source_identity import verify
    if verify(ROOT,'decryptor')!='c156627db7634d395c380c0a9589130f603307fc':raise ValueError('Decryptor source pin mismatch')
    source=ROOT/'private/tools/pspdecrypt';sdk=ROOT/'private/toolchain/prerequisites/msys64/ucrt64/bin'
    out=ROOT/'private/tools/decrypt-build';out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ);env['PATH']=str(sdk)+os.pathsep+env.get('PATH','')
    objects=[]
    for name in ('AES','SHA1','bn','ec','kirk_engine'):
        obj=out/(name+'.o');objects.append(str(obj))
        subprocess.run([str(sdk/'gcc.exe'),'-O2','-c',str(source/'libkirk'/(name+'.c')),'-o',str(obj)],env=env,check=True)
    output=out/'prx-decrypt.dll'
    subprocess.run([str(sdk/'g++.exe'),'-O2','-shared','-static-libgcc','-static-libstdc++','-I'+str(source),
                    str(ROOT/'tools/prx-decrypt.cpp'),str(source/'PrxDecrypter.cpp'),*objects,'-o',str(output)],env=env,check=True)
    print(json.dumps(dict(status='PASS',path=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),game_data_embedded=False),indent=2))
if __name__=='__main__':main()
