"""Test zero-hash namespacing and shared mip prefixes using the pinned pack reader."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title

PROGRAM=r'''
#include <stdio.h>
#include <string.h>
#include "texrepl.h"
#include "sampler_pack.c"
static NkTexReplId original(void) {
    NkTexReplId id={0};id.addr=0x04010000u;id.format=5u;id.dim=0x0303u;id.clut_hash=0x12345678u;
    return id;
}
int main(int argc,char **argv) {
    const unsigned wraps[4]={0,1,256,257};
    if(argc!=2)return 2;
    if(strcmp(argv[1],"keys")==0) {
        NkTexReplId id=original();
        for(int i=0;i<4;i++)printf("%016llx%08x\n",(unsigned long long)nk_texrepl_cache_key(id.addr,id.format,id.dim,id.clut_hash),loa_sampler_tag(wraps[i]));
        return 0;
    }
    char err[256];NkTexRepl *p=nk_texrepl_open(argv[1],0,err,sizeof err);
    if(!p){fprintf(stderr,"%s\n",err);return 3;}
    s_loa_sampler_pack=1;
    for(int i=0;i<4;i++) {
        NkTexReplId id=original();NkTexReplHit hit={0};
        if(!loa_sampler_lookup(p,&id,&hit,wraps[i]) || !id.hash || id.hash!=loa_sampler_tag(wraps[i]) || nk_texrepl_factor(&hit,8,8)!=4)return 4;
        nk_texrepl_unpin(p,&hit);
        /* A single-level guest uses level zero; a three-level guest uses the
           exact same prefix plus the two additional authored levels. */
        if(nk_texrepl_level_count(p,&id)!=3)return 5;
        for(int requested=1;requested<=3;requested+=2)for(int l=0;l<requested;l++) {
            if(!nk_texrepl_lookup_level(p,&id,l,&hit) || hit.w!=(32>>l) || hit.h!=(32>>l))return 6;
            for(int n=0;n<hit.w*hit.h;n++)if(hit.rgba[n]!=(0xff000000u|(0x11u*(i+1))))return 7;
            nk_texrepl_unpin(p,&hit);
        }
        id=original();id.hash=0x12345678u;
        if(loa_sampler_lookup(p,&id,&hit,wraps[i]))return 8;
    }
    nk_texrepl_close(p);
    puts("PASS: zero source hash maps to four exact nonzero keys; 1/3-level prefixes work; unrelated data never matches");
    return 0;
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private') or out==ROOT/'private':p.error('Use private output')
    if out.exists() and (not (out/'check.c').is_file() or (out/'check.c').read_text()!=PROGRAM):
        p.error('Reuse only this test\'s owned output directory')
    revision=title.verify_inputs();out.mkdir(parents=True,exist_ok=True)
    source=out/'check.c';source.write_text(PROGRAM)
    rt=title.FRAMEWORK/'src/rt';core=title.FRAMEWORK/'src/core';exe=out/'check.exe'
    sources=[rt/'texrepl.c',core/'nk_zip.c',core/'nk_psp_inflate.c',core/'nk_platform_win32.c',core/'nk_shared_helpers.c']
    cmd=[str(title.SDK/'bin/gcc.exe'),'-std=c11','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
         '-I'+str(rt),'-I'+str(core),'-I'+str(ROOT/'tools'),str(source),*[str(s) for s in sources],
         '-lshell32','-lole32','-luuid','-ladvapi32','-luser32','-o',str(exe)]
    env=title.environment()
    with (out/'build.log').open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    keys=subprocess.check_output([str(exe),'keys'],env=env,text=True).splitlines()
    spec=importlib.util.spec_from_file_location('png',ROOT/'tools/inventory-textures.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    pack=out/'fixture';pack.mkdir(exist_ok=True);lines=['[options]','hash = quick','[hashes]']
    for i,key in enumerate(keys):
        for level in range(3):
            side=32>>level;file=f'context-{i}-{level}.png'
            (pack/file).write_bytes(m.png(side,side,bytes((0x11*(i+1),0,0,255))*(side*side)))
            lines.append(f'{key}_{level} = {file}')
    (pack/'textures.ini').write_text('\n'.join(lines)+'\n')
    run=subprocess.run([str(exe),str(pack)],env=env,capture_output=True,text=True,timeout=30)
    (out/'run.log').write_text(run.stdout+run.stderr)
    result=dict(scope='pinned-pack-reader-source-alias-test',framework_commit=revision,returncode=run.returncode,
        passed=run.returncode==0,keys=keys,source_sha256={str(s.relative_to(ROOT)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources+[ROOT/'tools/sampler_pack.c']},
        runtime_modified=False,game_assets_used=False,gpu_draw_validated=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run.stdout+run.stderr);print(json.dumps(result,indent=2))
    if run.returncode:raise SystemExit(run.returncode)


if __name__=='__main__':main()
