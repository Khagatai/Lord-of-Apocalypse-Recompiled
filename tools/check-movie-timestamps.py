"""Compare compiled PSMF timestamp decoding with the locally pinned PPSSPP code."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import media_runtime_patch,title

def main():
    title.verify_inputs()
    oracle=ROOT/'private/tools/ppsspp'
    revision=subprocess.check_output(['git','-c','safe.directory='+oracle.as_posix(),'-C',str(oracle),'rev-parse','HEAD'],text=True).strip()
    if revision!=title.CONFIG['tools']['ppsspp']['commit']:raise ValueError('PPSSPP pin differs')
    header=oracle/'Core/HW/MediaEngine.h';reference=header.read_text()
    ref=re.search(r'inline s64 getMpegTimeStamp\(const u8 \*buf\) \{.*?\n\}',reference,re.S)
    if not ref:raise ValueError('Reference decoder not found')
    patched=media_runtime_patch.render((title.FRAMEWORK/'src/rt/mpeg.c').read_bytes())
    fn=re.search(r'static int64_t mpeg_ts\(uint32_t a\) \{.*?\n\}',patched,re.S)
    if not fn:raise ValueError('Patched decoder not found')
    folder=ROOT/'private/movie-timestamp-oracle';folder.mkdir(exist_ok=True)
    source='''#include <stdint.h>
#include <stdio.h>
typedef int64_t s64; typedef uint8_t u8;
static uint8_t memory[6];
#define MEM_R8(a) memory[(a)]
'''+ref.group(0)+'\n'+fn.group(0)+'''
int main(void){
    const uint64_t known[]={0,1,255,256,90000,0xffffffffULL,0x100000000ULL,0x1ffffffffULL};
    unsigned count=0;
    for(unsigned j=0;j<8;j++){
        uint64_t v=known[j];
        for(int i=5;i>=0;i--){memory[i]=(uint8_t)v;v>>=8;}
        if(mpeg_ts(0)!=(int64_t)known[j] || mpeg_ts(0)!=getMpegTimeStamp(memory))return 1;
        count++;
    }
    uint32_t random=314159;
    for(unsigned j=0;j<4096;j++){
        for(int i=0;i<6;i++){random=random*1664525u+1013904223u;memory[i]=random>>24;}
        if(mpeg_ts(0)!=getMpegTimeStamp(memory))return 2;
        count++;
    }
    printf("%u timestamp cases passed\\n",count);return 0;
}
'''
    cpp=folder/'timestamps.cpp';exe=folder/'timestamps.exe';cpp.write_text(source)
    command=[str(title.SDK/'bin/g++.exe'),'-O2',str(cpp),'-o',str(exe)]
    subprocess.run(command,check=True,env=title.environment(),capture_output=True)
    result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    report=dict(scope='compiled-reference-source-comparison-not-gameplay-trace',passed=True,cases=4104,
        ppsspp_revision=revision,reference_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(cpp.read_bytes()).hexdigest(),stdout=result.stdout.strip())
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(result.stdout.strip())

if __name__=='__main__':main()
