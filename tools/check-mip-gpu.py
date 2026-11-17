"""Run synthetic authored-mip Vulkan tests through an isolated patched renderer."""
import argparse
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
    parser.add_argument('--mutant-base-only',action='store_true',help='Negative test: require the wrong base-only sampler to fail')
    parser.add_argument('--mutant-sampler-namespace',action='store_true',help='Negative test: force the wrong wrap variant and require detection')
    args=parser.parse_args()
    if args.mutant_base_only and args.mutant_sampler_namespace:parser.error('Choose one negative control')
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    title.verify_inputs();output.mkdir(parents=True)
    patch=mip_runtime_patch.prepare(title.FRAMEWORK,output/'ge_gpu.c')
    relative='../../'+output.relative_to(ROOT).as_posix()
    define='-DLOA_MIP_MUTANT_BASE_ONLY' if args.mutant_base_only else ''
    if args.mutant_sampler_namespace:define='-DLOA_WRAP_MUTANT_IGNORE_SAMPLER'
    make=output/'check.mk'
    make.write_text(f'''GEGPU_SRCS := $(filter-out src/rt/gpu_sdl3vk/ge_gpu.c,$(GEGPU_SRCS)) {relative}/ge_gpu.c
.PHONY: loa-mip-gpu-check
loa-mip-gpu-check: $(RT_GE_O)
\t$(GPU_TEXSCALE_BUILD) -Isrc/rt/gpu_sdl3vk -I../../tools {define} -o {relative}/mip-gpu-check.exe
''')
    command=[str(title.SDK/'bin/mingw32-make.exe'),'-f','Makefile','-f',relative+'/check.mk',
             *title.make_arguments('release'),'-j4','loa-mip-gpu-check']
    env=title.environment()
    with (output/'build.log').open('w') as log:
        subprocess.run(command,cwd=title.FRAMEWORK,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    results=[]
    env['LOA_MIP_TEXTURES']='1'
    for scale,factor in ((1,2),(4,4)):
        command=[str(output/'mip-gpu-check.exe'),'--scale',str(scale),'--tex-scale',str(factor)]
        run=subprocess.run(command,cwd=title.FRAMEWORK,env=env,capture_output=True,text=True,timeout=60)
        log=run.stdout+run.stderr
        (output/f'scale-{scale}-factor-{factor}.log').write_text(log)
        if run.returncode==77:raise RuntimeError('Vulkan test skipped; no pass claimed')
        detected=run.returncode!=0 and 'LOA mip GPU: FAIL authored level selection' in log
        if args.mutant_sampler_namespace:detected=run.returncode!=0 and 'LOA mip GPU: FAIL sampler namespace' in log
        passed=detected if (args.mutant_base_only or args.mutant_sampler_namespace) else run.returncode==0 and log.count('LOA mip GPU: PASS')==11
        results.append({'render_scale':scale,'texture_factor':factor,'returncode':run.returncode,'passed':passed,
                        'evidence':[line for line in log.splitlines() if line.startswith('LOA mip GPU:')]})
        if not passed:
            print(log[-3500:]);break
    report={'scope':'synthetic-authored-mip-vulkan-check','source_patch':patch,
            'negative_control':args.mutant_base_only or args.mutant_sampler_namespace,
            'negative_kind':'sampler-namespace' if args.mutant_sampler_namespace else ('base-only' if args.mutant_base_only else None),
            'results':results,'passed':len(results)==2 and all(r['passed'] for r in results)}
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
