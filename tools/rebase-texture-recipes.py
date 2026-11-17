"""Verify whether the current text-region edits apply directly to Japanese XET/layout resources.

This does not declare rendered pixel files distributable or regenerate them.
It isolates the remaining local-rendering dependency from the upstream patch.
"""
import argparse,collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from rgf_archive import parse_index,resources
from texture_text import reconstruct,digest

def read(folder,wanted):
    result={};counts=collections.Counter()
    with (folder/'REGFILE.RZP').open('rb') as stream:
        for group,identity,raw in resources(stream,parse_index((folder/'REGFILE.RZL').read_bytes(),(folder/'REGFILE.RZP').stat().st_size)):
            occurrence=counts[group,identity];counts[group,identity]+=1
            if identity in wanted:result[group,identity,occurrence]=raw
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'private/local-build/japanese-textures.json');args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'private'):raise ValueError('Keep rendered-text dependencies private')
    rows=json.loads((ROOT/'private/translation/english-review/full-textures.json').read_text())['resources']
    plans={(int(row['resource_id'],16),row['target_sha256']):row for row in rows}
    wanted={key[0] for key in plans}
    before=read(ROOT/'private/translation/archives/japanese',wanted);after=read(ROOT/'private/translation/text-pass-16-archives',wanted)
    if set(before)!=set(after):raise ValueError('Text resource occurrence topology changed')
    rebuilt=[];failures=[];unchanged=0
    for key,source in before.items():
        target=after[key]
        if source==target:unchanged+=1;continue
        plan=plans.get((key[1],digest(target)))
        if plan is None:failures.append(dict(group_index=key[0],resource_id=f'{key[1]:08x}',reason='No target rendering/layout recipe'));continue
        recipe=dict(plan,source_sha256=digest(source),group_index=key[0],occurrence=key[2])
        try:
            raw=reconstruct(source,recipe,ROOT/'private')
            if raw!=target:raise ValueError('Japanese-source text-region reconstruction differs from WIP target')
            rebuilt.append(recipe)
        except ValueError as error:failures.append(dict(group_index=key[0],resource_id=f'{key[1]:08x}',reason=str(error)))
    result=dict(schema=1,status='PASS' if not failures else 'INCOMPLETE',scope='Japanese-source text-region reconstruction using current private rendered pixels',
        resources=rebuilt,failures=failures,unchanged_occurrences=unchanged,rendered_pixels_still_required=True,
        ISO_only_texture_generation_complete=False,archives_created=False)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],verified_resources=len(rebuilt),failures=len(failures),rendered_pixels_still_required=True),indent=2))
if __name__=='__main__':main()
