"""Export pixel-free HD recipes bound to the current ISO-built English archive.

Keep the reviewed world/model processing. Regenerate UI fallback atlases by
faithful xBRZ scaling of current English artwork; actual 2D draws retain original
resolution in the runtime. Obsolete UI keys and source-less base UI are retired.
"""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import remaster_policy,sampler_pack


def sha(raw):return hashlib.sha256(raw).hexdigest()


def export(pack,audit,catalog):
    spec=importlib.util.spec_from_file_location('hd_selector',ROOT/'tools/build-archive-remaster.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    jobs={};groups={};retired=[];world=0
    portraits=remaster_policy.portrait_keys(catalog)
    def add(key,ref,dimensions,hashes,wrap,method,model=None,detail=None,canonical=None):
        if key in portraits or remaster_policy.original_portrait(ref['name']):return
        recipe=dict(dimensions=dimensions,source_rgba_sha256=hashes,wrap=wrap,method=method,model=model,detail_pass=detail)
        identity=sha(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode())
        if identity not in jobs:jobs[identity]=dict(recipe,reference={k:ref[k] for k in ('resource_id','source_sha256','texture_index','name')})
        value=dict(key=key,job=identity)
        if canonical:value['canonical_key']=canonical
        if key in groups and groups[key]!=value:raise ValueError('Competing HD key recipes')
        groups[key]=value
    for group in pack['textures']:
        refs=audit['bindings'].get(group['key'])
        if not refs:
            if group['origin'] not in ('base-ui','scaled-authored-ui','vector-typeset-existing-english'):
                raise ValueError('Missing world/model source: '+group['key'])
            retired.append(dict(key=group['key'],origin=group['origin'],reason='obsolete or source-less UI; replaced from current English catalog'))
            continue
        original_ui=group['origin'] in ('scaled-authored-ui','vector-typeset-existing-english')
        method='scale' if original_ui or group['origin']=='scaled-authored-world' else 'restore'
        if not original_ui:world+=1
        add(group['key'],refs[0],refs[0]['dimensions'],group['source_rgba_sha256'],group['wrap'],method,
            group.get('model','realesrgan-x4plus') if method=='restore' else None,
            group.get('detail_pass'),group.get('canonical_key'))
    chosen,excluded=builder.select(catalog,re.compile('.*'),True,minimum_dimension=1,allow_zero_source_hash=True)
    chosen,originals=remaster_policy.exclude_portraits(chosen,catalog);excluded.extend(originals)
    for sig,rows,keys in chosen:
        ref=rows[0];dimensions=[[w,h] for w,h,_ in sig];hashes=[digest for _,_,digest in sig]
        for canonical in keys:
            for wrap in (0,1,256,257):
                key=sampler_pack.tagged_key(canonical,wrap)
                if key in groups:continue
                add(key,ref,dimensions,hashes,wrap,'scale',canonical=canonical)
    if not 1<=len(groups)<=65536:raise ValueError('HD key count exceeds runtime limits')
    return dict(schema=1,scope='ISO-local HD generation recipes',archive_sha256=audit['archive_sha256'],index_sha256=audit['index_sha256'],
        jobs=jobs,groups=list(groups.values()),retired_UI_entries=retired,retained_world_model_entries=world,
        original_2D_UI=True,original_dialogue_portraits=True,audio_modified=False,game_pixels_included=False,
        exclusions=excluded,complete_campaign_visual_validation=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'private/local-build/portable-hd-recipes.json');a=p.parse_args()
    if not a.output.resolve().is_relative_to(ROOT/'private') or a.output.exists():raise ValueError('Use fresh private recipe output')
    load=lambda name:json.loads((ROOT/name).read_text())
    pack_raw=(ROOT/'private/hd-remaster-pack/sample.json').read_bytes();audit=load('private/local-build/hd-source-audit.json')
    if sha(pack_raw)!=audit['pack_manifest_sha256']:raise ValueError('Pack reference changed')
    result=export(json.loads(pack_raw),audit,load('private/local-build/current-HD-catalog/catalog.json'))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(groups=len(result['groups']),unique_processing_jobs=len(result['jobs']),
        methods={m:sum(j['method']==m for j in result['jobs'].values()) for m in ('scale','restore')},
        retired_UI_entries=len(result['retired_UI_entries']),retained_world_model_entries=result['retained_world_model_entries'],pixel_payloads=0),indent=2))


if __name__=='__main__':main()
