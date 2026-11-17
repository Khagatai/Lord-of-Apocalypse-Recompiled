"""Bind HD processing recipes to locally rasterized English UI and current keys.

World/model source pixels must still exist exactly. Only resources explicitly
listed by the guarded UI renderer may acquire new pixel identities. Their new
keys use faithful original-art scaling; dialogue portraits remain excluded.
"""
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import remaster_policy,sampler_pack


def sha(raw):return hashlib.sha256(raw).hexdigest()
def signature(job):return tuple((w,h,digest) for (w,h),digest in zip(job['dimensions'],job['source_rgba_sha256'],strict=True))


def rebase(original,catalog,report,rendered):
    module=importlib.util.spec_from_file_location('rebase_hd_selector',ROOT/'tools/build-archive-remaster.py')
    selector=importlib.util.module_from_spec(module);module.loader.exec_module(selector)
    if rendered.get('ISO_only_texture_generation_complete') is not True or rendered.get('source_identity_and_edit_region_guards') is not True:
        raise ValueError('Local UI reconstruction has not passed its source/edit-region guards')
    changed={r['resource_id'] for r in rendered.get('platform_rasterization_variants',[])}
    originals=original['jobs'];old_groups={g['key']:g for g in original['groups']}
    available={selector.signature(row) for row in catalog}
    missing=[]
    for job_id,job in originals.items():
        if job['method']=='restore' and signature(job) not in available and job['reference']['resource_id'] not in changed:
            missing.append(job_id)
    if missing:raise ValueError('Unchanged world/model source mip chains are missing: '+str(len(missing)))
    by_signature={}
    for job in originals.values():by_signature.setdefault(signature(job),[]).append(job)
    chosen,excluded=selector.select(catalog,re.compile('.*'),True,minimum_dimension=1,allow_zero_source_hash=True)
    chosen,portraits=remaster_policy.exclude_portraits(chosen,catalog);excluded.extend(portraits)
    jobs={};groups={};preserved=0;new_ui=0
    for sig,rows,keys in chosen:
        dimensions=[[w,h] for w,h,_ in sig];hashes=[h for _,_,h in sig]
        ref={k:rows[0][k] for k in ('resource_id','source_sha256','texture_index','name')}
        for key in keys:
            for wrap in (0,1,256,257):
                tagged=sampler_pack.tagged_key(key,wrap);old=old_groups.get(tagged) or old_groups.get(key)
                job=originals[old['job']] if old and signature(originals[old['job']])==sig else None
                if job is None:
                    matches=[j for j in by_signature.get(sig,[]) if j['wrap']==wrap and not j.get('detail_pass')]
                    if matches:job=next((j for j in matches if j['method']=='restore'),matches[0])
                if job:
                    method,model,detail=job['method'],job['model'],job.get('detail_pass');preserved+=1
                else:
                    method,model,detail='scale',None,None;new_ui+=1
                value=dict(dimensions=dimensions,source_rgba_sha256=hashes,wrap=wrap,method=method,model=model,detail_pass=detail)
                job_id=sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
                if job_id not in jobs:jobs[job_id]=dict(value,reference=ref)
                if tagged in groups and groups[tagged]['job']!=job_id:raise ValueError('Local HD key conflict')
                groups[tagged]=dict(key=tagged,canonical_key=key,job=job_id)
                if key in old_groups and signature(originals[old_groups[key]['job']])==sig and wrap==originals[old_groups[key]['job']]['wrap']:
                    groups[key]=dict(key=key,job=job_id)
    if not 1<=len(groups)<=65536:raise ValueError('Local HD group count exceeds runtime bounds')
    return dict(schema=1,scope='ISO-local HD generation recipes',archive_sha256=report['archive_sha256'],index_sha256=report['index_sha256'],
        jobs=jobs,groups=list(groups.values()),game_pixels_included=False,original_2D_UI=True,original_dialogue_portraits=True,
        audio_modified=False,platform_UI_variants=len(rendered.get('platform_rasterization_variants',[])),
        exact_source_processing_preserved=preserved,new_current_keys_scaled_from_original_art=new_ui,exclusions=excluded,
        complete_campaign_visual_validation=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('recipes','catalog','rendered','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for path in (a.recipes,a.catalog,a.rendered,a.output):
        if not path.resolve().is_relative_to(ROOT/'private'):raise ValueError('Keep local HD recipes private')
    load=lambda path:json.loads(path.read_text(encoding='utf-8'))
    result=rebase(load(a.recipes),load(a.catalog/'catalog.json'),load(a.catalog/'result.json'),load(a.rendered))
    data=json.dumps(result,indent=2)+'\n'
    if a.output.exists() and a.output.read_text()!=data:raise ValueError('Existing locally rebased HD recipe differs')
    a.output.write_text(data)
    print(json.dumps({k:v for k,v in result.items() if k not in ('jobs','groups','exclusions')},indent=2),flush=True)


if __name__=='__main__':main()
