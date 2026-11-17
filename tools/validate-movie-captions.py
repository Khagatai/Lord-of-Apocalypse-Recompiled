"""Exercise the actual C caption writer on every private cue in four formats.

This is bounded host-memory validation, not a claim of campaign route testing.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 private=(ROOT/'private').resolve();bundle=a.bundle.resolve();out=a.output.resolve()
 if not bundle.is_relative_to(private) or not out.is_relative_to(private) or out.is_symlink():p.error('Keep private pixels and diagnostics private')
 if out.exists() and not(out/'recomp.h').is_file():raise ValueError('Existing output is not an owned writer diagnostic')
 out.mkdir(parents=True,exist_ok=True)
 (out/'recomp.h').write_text('#include <stdint.h>\nint sr_guest_span_readable(uint32_t,uint32_t);\nint sr_guest_span_writable_any_view(uint32_t,uint32_t);\nint sr_guest_copy_in(void*,uint32_t,uint32_t);\nint sr_guest_copy_out(uint32_t,const void*,uint32_t);\n')
 exe=out/'caption-check.exe';env=title.environment()
 compile=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-std=c11','-Wall','-Wextra','-I'+str(out),'-I'+str(ROOT/'tools'),str(ROOT/'tools/movie-caption-check.c'),str(ROOT/'tools/movie_subtitles.c'),'-o',str(exe)],env=env,capture_output=True,text=True)
 (out/'build.log').write_text(compile.stdout+compile.stderr)
 if compile.returncode:raise RuntimeError('Caption checker compile failed; see build.log')
 env['LOA_MOVIE_CAPTIONS']=str(bundle);run=subprocess.run([str(exe),str(bundle)],env=env,capture_output=True,text=True,timeout=90)
 (out/'stderr.log').write_text(run.stderr);(out/'stdout.log').write_text(run.stdout)
 result=dict(status='PASS' if run.returncode==0 else 'FAIL',returncode=run.returncode,bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),campaign_routes_tested=False,audio_tested=False)
 if run.returncode==0:result.update(json.loads(run.stdout))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 if run.returncode:raise RuntimeError('Caption writer validation failed')
if __name__=='__main__':main()
