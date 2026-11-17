"""Sharpen observed player atlases in place, retaining one scoped pixel rollback."""
import argparse,copy,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import pack_update,texture_pack,title
RECIPE='gaussian5-detail25-cap6-alpha-preserved-v1'
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    args=parser.parse_args();capture=args.capture.resolve()
    if not capture.is_relative_to(ROOT/'private'):parser.error('Capture must remain local/private')
    title.verify_inputs();folder=ROOT/'private/hd-remaster-pack'
    checked=texture_pack.verify_sample(folder);old=json.loads((folder/'sample.json').read_text());new=copy.deepcopy(old)
    catalog=json.loads((ROOT/'private/remaster-coverage-08/catalog.json').read_text())
    observed={('00000000'+r['key'][8:]) for r in map(json.loads,(capture/'art-capture.jsonl').read_text().splitlines()) if not r['through']}
    names={r['name'] for r in catalog if observed.intersection(r['candidate_keys']) and re.fullmatch(r'P[BHFW][0-9_]+',r['name'])}
    if not names:raise ValueError('No identified player model textures were observed')
    owners={}
    for row in new['textures']:
        for level in row['levels']:owners.setdefault(level['file'],[]).append(row)
    selected={level['file'] for row in new['textures'] if any(ref['name'] in names for ref in row.get('archive_references',[])) for level in row['levels']}
    # Refuse to edit files shared with any non-player archive asset.
    for name in selected:
        if any(not re.fullmatch(r'P[BHFW][0-9_]+',ref['name']) for row in owners[name] for ref in row.get('archive_references',[])):
            raise ValueError('Player atlas shared with unrelated art: '+name)
    states={row.get('detail_pass') for name in selected for row in owners[name]}
    if states=={RECIPE}:print('Observed player textures already sharpened');return
    if states!={None}:raise ValueError('Mixed or unrecognized previous detail pass')
    work=ROOT/'private/player-clarity';work.mkdir(exist_ok=True)
    rollback=work/'rollback';rollback.mkdir(exist_ok=True)
    if any(rollback.iterdir()):raise ValueError('Review existing scoped rollback before another pass')
    exe=work/'sharpen.exe';source=ROOT/'tools/sharpen-model-texture.c'
    subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(title.FRAMEWORK/'third_party/stb'),str(source),'-o',str(exe)],env=title.environment(),check=True,capture_output=True)
    selftest=subprocess.run([str(exe),'--self-test'],check=True,capture_output=True,text=True)
    spec=importlib.util.spec_from_file_location('png_writer',ROOT/'tools/inventory-textures.py');png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)
    report=dict(recipe=RECIPE,observed_player_names=sorted(names),selftest=selftest.stdout.strip(),files=[],visual_quality_validated=False)
    raw=work/'result.rgba'
    try:
        for name in sorted(selected):
            path=folder/name;before=path.read_bytes();(rollback/name).write_bytes(before)
            level=next(l for l in owners[name][0]['levels'] if l['file']==name);w,h=level['width'],level['height']
            subprocess.run([str(exe),str(path),str(raw)],check=True,env=title.environment())
            pixels=raw.read_bytes()
            if len(pixels)!=w*h*4:raise ValueError('Sharpened dimensions differ')
            after=png.png(w,h,pixels);pack_update.atomic_write(path,after)
            for row in owners[name]:
                row['detail_pass']=RECIPE
                for item in row['levels']:
                    if item['file']==name:item['sha256']=digest(after)
            report['files'].append(dict(file=name,before_sha256=digest(before),after_sha256=digest(after),width=w,height=h))
        new['base_manifest_sha256']=checked['sample_manifest_sha256']
        pack_update.commit(folder,new,(folder/'textures.ini').read_bytes())
    except BaseException:
        for path in rollback.glob('*.png'):pack_update.atomic_write(folder/path.name,path.read_bytes())
        raise
    finally:raw.unlink(missing_ok=True)
    report['manifest_sha256']=digest((folder/'sample.json').read_bytes())
    report['source_sha256']=digest(source.read_bytes());(work/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(player_names=sorted(names),changed_pngs=len(report['files']),visual_quality_validated=False)))
if __name__=='__main__':main()
