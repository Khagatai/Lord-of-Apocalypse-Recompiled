"""Verify actual before/after player PNG alpha and bounded RGB detail locally."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
def main():
    title.verify_inputs();folder=ROOT/'private/player-clarity'
    report=json.loads((folder/'result.json').read_text());exe=folder/'decode.exe'
    subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),
        str(ROOT/'tools/decode-private-png.c'),'-o',str(exe)],env=title.environment(),check=True,capture_output=True)
    checks=[]
    for row in report['files']:
        buffers=[]
        for label,path in [('before',folder/'rollback'/row['file']),('after',ROOT/'private/hd-remaster-pack'/row['file'])]:
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row[label+'_sha256']:raise ValueError('PNG identity changed')
            raw=folder/(label+'.rgba');w,h=row['width'],row['height']
            subprocess.run([str(exe),str(path),str(raw),str(w),str(h),'0','0',str(w),str(h)],check=True)
            buffers.append(raw.read_bytes());raw.unlink()
        before,after=buffers
        alpha=before[3::4]==after[3::4]
        peak=max(abs(a-b) for a,b in zip(before,after))
        if not alpha or peak>6:raise ValueError('Detail exceeds RGB/alpha contract: '+row['file'])
        checks.append(dict(file=row['file'],alpha_unchanged=alpha,max_channel_delta=peak))
    result=dict(scope='actual-player-png-detail-verification',passed=True,files=len(checks),checks=checks,
        visual_quality_validated=False,geometry_modified=False)
    (folder/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:',len(checks),'player PNGs; exact alpha and RGB delta <= 6')
if __name__=='__main__':main()
