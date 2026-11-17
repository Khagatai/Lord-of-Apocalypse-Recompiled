"""Independently decode changed PNGs and compare their complete alpha planes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import texture_pack
import title


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private') or out.exists():p.error('Use a fresh private output directory')
    before=texture_pack.verify_sample(args.baseline);after=texture_pack.verify_sample(args.candidate)
    old={g['key']:g for g in before['textures']};new={g['key']:g for g in after['textures']}
    if set(old)!=set(new):raise ValueError('Pack identities differ; compare matching packs')
    out.mkdir(parents=True);title.verify_inputs();env=title.environment();decoder=out/'decode-png.exe'
    with (out/'build.log').open('w') as log:
        subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),
                        str(ROOT/'tools/decode-private-png.c'),'-o',str(decoder)],env=env,
                        stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    records=[];same=0
    for key,group in new.items():
        original=old[key]
        if len(original['levels'])!=len(group['levels']):raise ValueError('Mip count changed')
        for level,(base,changed) in enumerate(zip(original['levels'],group['levels'])):
            if (base['width'],base['height'])!=(changed['width'],changed['height']):raise ValueError('Mip dimensions changed')
            if base['sha256']==changed['sha256']:same+=1;continue
            if group['origin'] not in ('offline-restored-cutout','offline-restored-masked'):
                raise ValueError('Unrelated artwork changed during alpha-constrained update')
            width,height=base['width'],base['height'];decoded=[]
            for folder,entry,tag in ((args.baseline,base,'baseline'),(args.candidate,changed,'candidate')):
                target=out/(tag+'.rgba')
                subprocess.run([str(decoder),str((folder/entry['file']).resolve()),str(target),str(width),str(height),
                                '0','0',str(width),str(height)],env=env,check=True,timeout=30)
                decoded.append(target.read_bytes())
            a,b=decoded
            equal=a[3::4]==b[3::4]
            records.append(dict(key=key,level=level,pixels=width*height,alpha_equal=equal,
                                original_alpha_sha256=hashlib.sha256(a[3::4]).hexdigest(),
                                candidate_alpha_sha256=hashlib.sha256(b[3::4]).hexdigest(),
                                changed_rgb_pixels=sum(a[i:i+3]!=b[i:i+3] for i in range(0,len(a),4))))
    report=dict(scope='decoded-png-alpha-preservation',baseline_manifest=before['sample_manifest_sha256'],
                candidate_manifest=after['sample_manifest_sha256'],unchanged_pngs=same,changed_pngs=len(records),
                passed=bool(records) and all(r['alpha_equal'] for r in records),images=records)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='images'},indent=2))
    if not report['passed']:raise SystemExit('Alpha preservation failed or was not exercised')


if __name__=='__main__':main()
