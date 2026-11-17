"""Rekey identical private artwork for native sampler-namespace regression checks.

This fixture does not claim four independently restored sampling contexts.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import texture_pack
import sampler_pack


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();source=args.pack.resolve()
    if not out.is_relative_to(ROOT/'private') or out.exists():p.error('Use a fresh private output directory')
    checked=texture_pack.verify_sample(source)
    if checked['scope']!='verified-mip-texture-pack' or checked.get('sampler_namespace'):
        raise ValueError('Use a verified legacy-identity mip pack')
    report=json.loads((source/'sample.json').read_text());out.mkdir(parents=True)
    groups=[];copied=set();lines=['[options]','hash = quick','[games]','NPJH50503 = textures.ini','[hashes]']
    for group in report['textures']:
        for entry in group['levels']:
            if entry['file'] not in copied:
                shutil.copyfile(source/entry['file'],out/entry['file']);copied.add(entry['file'])
        for wrap in ((None,) if group.get('origin')=='base-ui' else (0,1,256,257)):
            row=copy.deepcopy(group)
            if wrap is not None:
                row.update(key=sampler_pack.tagged_key(group['key'],wrap),original_key=group['key'],sampler_wrap=wrap)
            groups.append(row)
            for level,entry in enumerate(row['levels']):lines.append(row['key']+'_'+str(level)+' = '+entry['file'])
    ini=('\n'.join(lines)+'\n').encode('ascii');(out/'textures.ini').write_bytes(ini)
    report.update(textures=groups,ini_sha256=hashlib.sha256(ini).hexdigest(),sampler_namespace=sampler_pack.NAMESPACE,
                  sampler_fixture=True,source_manifest_sha256=checked['sample_manifest_sha256'],
                  independent_context_restorations=False,complete_hd_pack=False,visual_quality_validated=False)
    (out/'sample.json').write_text(json.dumps(report,indent=2)+'\n')
    result=texture_pack.verify_sample(out)
    print(json.dumps({k:v for k,v in result.items() if k!='textures'},indent=2))


if __name__=='__main__':main()
