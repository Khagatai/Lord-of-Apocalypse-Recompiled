"""Prepare one verified Japanese-dump -> current-WIP delta, without ISO copies."""
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
from tester_setup import patcher_paths
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    work=ROOT/'private/distribution-test';target=work/'patches/english-wip.vcdiff';temporary=target.with_suffix('.vcdiff.tmp')
    source=title.disc_image('japanese');original_sha=title.verify_disc_image(source,'japanese')
    image=ROOT/'private/translation/text-pass-16-image/LordOfApocalypse-English-WIP.iso';report=json.loads(image.with_name('result.json').read_text())
    expected=report['candidate_iso_sha256'];assert sha(image)==expected and not temporary.exists()
    tool=ROOT/'private/tools/xdelta/xdelta3.exe';started=time.monotonic()
    with patcher_paths(source,image,temporary) as (src,dst,delta):
        subprocess.run([str(tool),'-e','-9','-B','1073741824','-s',src,dst,delta],check=True,capture_output=True)
    digest=hashlib.sha256();size=0
    with patcher_paths(source,temporary) as (src,delta),tempfile.TemporaryFile() as errors:
        process=subprocess.Popen([str(tool),'-d','-c','-s',src,delta],stdout=subprocess.PIPE,stderr=errors)
        for block in iter(lambda:process.stdout.read(1024*1024),b''):digest.update(block);size+=len(block)
        code=process.wait();errors.seek(0);error=errors.read().decode(errors='replace')
        if code:raise RuntimeError(error)
    assert digest.hexdigest()==expected and size==image.stat().st_size
    assert sha(source)==original_sha and sha(image)==expected
    old_sha=sha(target) if target.exists() else None;os.replace(temporary,target)
    row=dict(name='english-wip',source_sha256=original_sha,target_sha256=expected,target_size=size,patch_sha256=sha(target),patch_size=target.stat().st_size,decoded_payload_hash_verified=True,source_unchanged=True)
    proof=dict(status='PASS',patches=[row],direct_from_japanese=True,superseded_wip_patch_sha256=old_sha,seconds=round(time.monotonic()-started,1))
    (work/'patch-verification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
