"""Build a separate Windows mip-scaling experiment, preserving release and upstream."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import title
import mip_runtime_patch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    revision=title.verify_inputs()
    original=title.build_directory('release')/'lordofapocalypse.exe'
    before=hashlib.sha256(original.read_bytes()).hexdigest()
    output.mkdir(parents=True)
    env=title.environment()
    patch=mip_runtime_patch.prepare(title.FRAMEWORK,output/'ge_gpu.c')
    test_source=output/'mip-chain-selftest.c'
    test_source.write_bytes((ROOT/'tools/mip-chain-selftest.c').read_bytes())
    gpu=title.FRAMEWORK/'src/rt/gpu_sdl3vk'
    test=output/'mip-chain-selftest.exe'
    command=[str(title.SDK/'bin/gcc.exe'),'-O2','-Wall','-Wextra','-ffunction-sections','-fdata-sections',
             '-Wl,--gc-sections','-I'+str(gpu),'-I'+str(title.SDK/'include'),
             str(test_source),str(gpu/'tex_scale.c'),
             str(title.FRAMEWORK/'third_party/xbrz/xbrz.c'),'-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(test)]
    with (output/'selftest-build.log').open('w') as log:
        subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    run=subprocess.run([str(test)],env=env,capture_output=True,text=True)
    (output/'selftest.log').write_text(run.stdout+run.stderr)
    print(run.stdout+run.stderr,flush=True)
    run.check_returncode()
    # Include paths are passed relative to the pinned framework, avoiding shell
    # interpolation of user paths. Only a private object replaces ge_gpu.o here.
    relative='../../'+output.relative_to(ROOT).as_posix()
    make=output/'prototype.mk'
    make.write_text(f'''# Private experiment; the normal Make entry point never includes this file.
RT_OBJS := $(filter-out $(BUILD_DIR)/ge_gpu.o,$(RT_OBJS))
LINK_OBJECTS += {relative}/ge_gpu_mip.o
compile: {relative}/ge_gpu_mip.o
{relative}/ge_gpu_mip.o: {relative}/ge_gpu.c {relative}/mip_gpu.c {relative}/mip_chain.c {relative}/sampler_pack.c
\t$(CC) $(CFLAGS) -Isrc/rt/gpu_sdl3vk -I../../tools -c $< -o $@
''',encoding='utf-8')
    executable=output/'mip-prototype.exe'
    command=[str(title.SDK/'bin/mingw32-make.exe'),'-f','Makefile','-f','../../tools/overlay-settings.mk',
             '-f',relative+'/prototype.mk',*title.make_arguments('release'),
             'TITLE_OUTPUT='+relative+'/mip-prototype.exe','-j4','compile']
    with (output/'build.log').open('w') as log:
        subprocess.run(command,cwd=title.FRAMEWORK,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    unchanged=hashlib.sha256(original.read_bytes()).hexdigest()==before
    report={'framework_commit':revision,'source_patch':patch,'selftest_returncode':run.returncode,
            'original_executable_sha256':before,'original_executable_unchanged':unchanged,
            'prototype_executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
            'experimental':True,'runtime_validated':False}
    (output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not unchanged:raise RuntimeError('Normal release executable changed')


if __name__=='__main__':main()
