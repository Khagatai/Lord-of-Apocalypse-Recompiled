"""Rebind verified checkpoints after a reviewed recipe-only correction.

No pixels are copied or assumed complete: source/archive/model identities,
shared processing recipes and every retained PNG are verified before promotion.
"""
import hashlib,json,re,struct
from pathlib import Path
FIELDS=('dimensions','source_rgba_sha256','wrap','method','model','detail_pass')
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(path):return json.loads(Path(path).read_text())
def write(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)

def rebind(old_path,new_path,pack,work,framework,models,allowed_sources):
    pack,work=Path(pack).resolve(),Path(work).resolve()
    if (work/'completed').resolve().parent!=work or (work/'retired-completed').resolve().parent!=work:
        raise ValueError('Checkpoint directories escape owned work folder')
    old,new=load(old_path),load(new_path);old_sha,new_sha=sha(old_path),sha(new_path)
    if any(p.get('schema')!=1 or p.get('game_pixels_included') is not False for p in (old,new)):raise ValueError('Unknown HD recipe')
    if any(old[k]!=new[k] for k in ('archive_sha256','index_sha256')):raise ValueError('Archive changed; recipe checkpoints cannot be rebound')
    for identity in old['jobs'].keys() & new['jobs'].keys():
        if any(old['jobs'][identity].get(k)!=new['jobs'][identity].get(k) for k in FIELDS):raise ValueError('Shared processing job changed')
    owners=[load(folder/'owner.json') for folder in (pack,work)]
    for owner in owners:
        if (owner.get('tool')!='ISO-local-HD-v1' or owner.get('framework_commit')!=framework or owner.get('model_pins')!=models
            or owner.get('archive_sha256')!=new['archive_sha256'] or owner.get('processing_sources') not in allowed_sources
            or owner.get('recipe_sha256') not in (old_sha,new_sha)):raise ValueError('Unknown/incompatible checkpoint owner')
    verified={};retired=[];count=0
    completed=work/'completed'
    for path in completed.glob('*.json'):
        if path.is_symlink():raise ValueError('Linked checkpoint')
        row=load(path);identity=path.stem
        if row.get('job')!=identity or identity not in old['jobs']:raise ValueError('Unexpected completed HD job')
        dims=old['jobs'][identity]['dimensions']
        if len(row['levels'])!=len(dims):raise ValueError('Completed mip count changed')
        for level,(w,h) in zip(row['levels'],dims,strict=True):
            name=level['file'];png=pack/name
            if not re.fullmatch(r'tex-[0-9]{5}-[0-7]\.png',name) or png.is_symlink() or png.resolve().parent!=pack.resolve():raise ValueError('Unsafe checkpoint image')
            if (level['width'],level['height'])!=(w*4,h*4):raise ValueError('Completed mip dimensions changed')
            if name in verified:
                if verified[name]!=level['sha256']:raise ValueError('Conflicting image alias')
            else:
                if sha(png)!=level['sha256']:raise ValueError('Completed PNG changed')
                with png.open('rb') as stream:header=stream.read(24)
                if len(header)!=24 or header[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',header[16:24])!=(w*4,h*4):raise ValueError('Completed PNG header differs')
                verified[name]=level['sha256']
        if identity not in new['jobs']:retired.append(path)
        else:count+=1
    result=dict(status='VERIFIED_RECIPE_REBIND',old_recipe_sha256=old_sha,new_recipe_sha256=new_sha,
        retained_completed_jobs=count,retired_jobs=[p.stem for p in retired],verified_unique_PNGs=len(verified),
        newly_required_jobs=len(new['jobs'].keys()-old['jobs'].keys()),previous_owners=owners,pixel_files_copied=0)
    write(work/'recipe-rebind.json',result)
    if retired:
        archive=work/'retired-completed';archive.mkdir(exist_ok=True)
        for path in retired:
            target=archive/path.name
            if target.exists():
                if target.read_bytes()!=path.read_bytes():raise ValueError('Retired checkpoint collision')
                path.unlink()
            else:path.replace(target)
    for folder,owner in zip((pack,work),owners):write(folder/'owner.json',dict(owner,recipe_sha256=new_sha))
    return result

def migrate(root,new_path):
    root=Path(root).resolve();work=root/'private/local-build/HD-work';pack=root/'private/hd-remaster-pack'
    if any(not p.resolve().is_relative_to(root/'private') for p in (work,pack,Path(new_path))):raise ValueError('Keep recipe migration private')
    if not (work/'owner.json').is_file():return None
    new_sha=sha(new_path);owners=[load(folder/'owner.json') for folder in (pack,work)]
    old_sha=next((v['recipe_sha256'] for v in owners if v['recipe_sha256']!=new_sha),None)
    if old_sha is None:return None
    candidates=[root/'private/local-build/local-HD-recipes.json',root/'private/distribution/recipes/HD.json']
    old_path=next((p for p in candidates if p.is_file() and sha(p)==old_sha),None)
    if old_path is None:raise ValueError('Previous recipe proof is unavailable; existing HD files preserved')
    names=('build-local-hd-pack.py','neural_texture.py','scale-mip-texture.c','decode-private-png.c','sharpen-model-texture.c','inventory-textures.py',
        'hd_native.py','hd-native.c','model-detail.h','hd_work.py')
    current={name:sha(root/'tools'/name) for name in names}
    allowed=[current,*load(root/'config/hd-compatible-pipelines.json')['legacy_processing_sources']]
    import title
    from graphics_settings import preference_lock
    with preference_lock(root/'private/local-build/HD-generation.lock'):
        return rebind(old_path,new_path,pack,work,title.CONFIG['runtime']['commit'],load(root/'config/remaster-upscaler.json')['files'],allowed)
