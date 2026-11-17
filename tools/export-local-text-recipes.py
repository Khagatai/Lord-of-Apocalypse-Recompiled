"""Export private portable English text/layout plans, without source or rendered pixels."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'private/local-build/portable-text-recipes.json')
    a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(ROOT/'private') or out.exists():raise ValueError('Use a fresh private recipe file')
    recipes=json.loads((ROOT/'private/local-build/japanese-textures.json').read_text())
    index=json.loads((ROOT/'private/local-build/render-spec-audit.json').read_text())
    jobs={};mapping={}
    def add(old,path,renderer,operation):
        if path:
            plan=json.loads(Path(path).read_text(encoding='utf-8-sig'))
            plan.pop('source_png',None)
        else:plan=None
        job=dict(renderer=renderer,operation=operation,plan=plan)
        identity=hashlib.sha256(canonical(job)).hexdigest()
        jobs[identity]=job;mapping[old]='recipe:'+identity
    for row in index['found']:
        path=Path(row['path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['spec_sha256']:raise ValueError('Rendering plan changed')
        for item in row['outputs']:add(item['pixels'],path,'regular','none')
    for special in index['special']:
        path=Path(special['pixels']);candidate=path.parent.with_suffix('.json');operation='none'
        if path.name=='logo-wordmark.rgba':add(str(path),None,'neutral-wordmark','none');continue
        if path.parent.name=='conq09-english':candidate=path.parent/'letters.json';operation='zero-transparent'
        elif path.name=='composite.rgba':operation='thumbnail-plate'
        if not candidate.is_file():raise FileNotFoundError('Missing special text renderer plan')
        add(str(path),candidate,'caption',operation)
    rows=copy.deepcopy(recipes['resources']);edits=0
    for row in rows:
        for edit in row.get('edits',[]):
            edit['rgba_path']=mapping[edit['rgba_path']];edits+=1
    result=dict(schema=1,scope='portable English text and layout generation instructions',resources=rows,render_jobs=jobs,
        source_recipe_sha256=hashlib.sha256((ROOT/'private/local-build/japanese-textures.json').read_bytes()).hexdigest(),
        source_pixels_included=False,rendered_pixels_included=False,complete_player_installer=False)
    data=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    # Do not accidentally carry workstation paths into the portable plan.
    if str(ROOT) in data or 'C:\\\\Users\\\\' in data:raise ValueError('Workstation path remains in recipe')
    out.write_text(data,encoding='utf-8')
    print(json.dumps(dict(resources=len(rows),render_jobs=len(jobs),edits=edits,pixel_payloads=0),indent=2))


if __name__=='__main__':main()
