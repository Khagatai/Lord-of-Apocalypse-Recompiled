"""Link a private observer executable, without replacing the normal release."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
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
    output.mkdir(parents=True)
    original=title.build_directory('release')/'lordofapocalypse.exe'
    before=hashlib.sha256(original.read_bytes()).hexdigest()
    renderer_root=output
    renderer=mip_runtime_patch.prepare(title.FRAMEWORK,renderer_root/'ge_gpu.c')
    executable=output/'texture-probe.exe'
    # Make works with whitespace-free paths relative to the pinned framework.
    relative='../../'+executable.relative_to(ROOT).as_posix()
    renderer_relative='../../'+output.relative_to(ROOT).as_posix()
    fragment=output/'renderer.mk'
    fragment.write_text(f'''RT_OBJS := $(filter-out $(BUILD_DIR)/ge_gpu.o,$(RT_OBJS))
LINK_OBJECTS += {renderer_relative}/ge_gpu.o
compile: {renderer_relative}/ge_gpu.o
{renderer_relative}/ge_gpu.o: {renderer_relative}/ge_gpu.c {renderer_relative}/mip_gpu.c {renderer_relative}/mip_chain.c {renderer_relative}/sampler_pack.c
\t$(CC) $(CFLAGS) -Isrc/rt/gpu_sdl3vk -I../../tools -c $< -o $@
''')
    command=[str(title.SDK/'bin/mingw32-make.exe'),'-f','Makefile','-f','../../tools/overlay-settings.mk',
             '-f',renderer_relative+'/renderer.mk',
             '-f','../../tools/texture-probe.mk',*title.make_arguments('release'),
             'TITLE_OUTPUT='+relative,'-j4','compile']
    with (output/'build.log').open('w') as log:
        run=subprocess.run(command,cwd=title.FRAMEWORK,env=title.environment(),stdout=log,stderr=subprocess.STDOUT)
    if run.returncode:
        print('\n'.join((output/'build.log').read_text(errors='replace').splitlines()[-10:]))
        raise SystemExit(run.returncode)
    after=hashlib.sha256(original.read_bytes()).hexdigest()
    report={'framework_commit':revision,'original_executable_sha256':before,'original_executable_unchanged':before==after,
            'probe_executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
            'observer_source_sha256':hashlib.sha256((ROOT/'tools/texture-probe.c').read_bytes()).hexdigest(),
            'renderer':renderer,'normal_release_modified':False}
    (output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if before!=after:
        raise RuntimeError('Normal release executable changed')


if __name__=='__main__':
    main()
