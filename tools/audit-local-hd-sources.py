"""Prove HD recipe source pixels are obtainable from locally built English archives.

Reads the existing private pack as a reference only. No PNGs are copied or changed.
Missing and stale recipe inputs remain explicit failures, not substituted textures.
"""
import argparse, collections, hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from rgf_archive import parse_index, resources
from xet_codec import Xet


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify_reference(raw,reference,expected):
    if sha(raw)!=reference['source_sha256']:
        raise ValueError('HD archive resource identity differs')
    texture=Xet.parse(raw)
    index=reference['texture_index']
    if type(index) is not int or not 0<=index<len(texture.textures):
        raise ValueError('HD texture index differs')
    item=texture.textures[index]
    if item.name!=reference['name']:
        raise ValueError('HD texture name differs')
    hashes=[];dimensions=[]
    for level in range(len(item.mips)):
        w,h,pixels=texture.preview_mip(index,level,limit=512)
        hashes.append(sha(pixels));dimensions.append([w,h])
    if hashes!=expected:
        raise ValueError('HD authored mip pixels differ')
    return dimensions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archives',type=Path,required=True)
    p.add_argument('--pack',type=Path,default=ROOT/'private/hd-remaster-pack')
    p.add_argument('--recovered',type=Path,default=ROOT/'private/local-build/HD-reference-audit.json')
    p.add_argument('--output',type=Path,default=ROOT/'private/local-build/hd-source-audit.json')
    a=p.parse_args()
    for path in (a.archives,a.pack,a.recovered,a.output):
        if not path.resolve().is_relative_to(ROOT/'private'):
            raise ValueError('Keep game-derived work private')
    manifest_raw=(a.pack/'sample.json').read_bytes();pack=json.loads(manifest_raw)
    recovered={r['key']:r['references'] for r in json.loads(a.recovered.read_text())['recovered']}
    wanted={};wanted_ids={};bindings={};missing=[];all_groups=pack['textures'];rebound=set()
    for group in all_groups:
        refs=group.get('archive_references') or recovered.get(group['key'],[])
        hashes=group.get('source_rgba_sha256')
        if not refs or not hashes:
            missing.append(dict(key=group['key'],origin=group['origin'],reason='no source pixel provenance'))
            continue
        bindings[group['key']]=[]
        for ref in refs:
            identity=(int(ref['resource_id'],16),ref['source_sha256'])
            wanted.setdefault(identity,[]).append((group,ref))
            wanted_ids.setdefault(identity[0],[]).append((group,ref))
    rzl=a.archives/'REGFILE.RZL';rzp=a.archives/'REGFILE.RZP'
    groups=parse_index(rzl.read_bytes(),rzp.stat().st_size);seen=set();matched=set();decoded={}
    with rzp.open('rb') as stream:
        for number,identity,raw in resources(stream,groups):
            if identity>>16!=2:continue
            signature=(identity,sha(raw))
            if identity not in wanted_ids or signature in seen:continue
            seen.add(signature)
            candidates=wanted.get(signature) or wanted_ids[identity]
            for group,old_ref in candidates:
                ref=dict(old_ref,source_sha256=signature[1])
                token=(*signature,ref['texture_index'])
                if token not in decoded:
                    try:dimensions=verify_reference(raw,ref,group['source_rgba_sha256'])
                    except ValueError:
                        if signature in wanted:raise
                        continue
                    decoded[token]=(dimensions,group['source_rgba_sha256'])
                else:
                    # The same resource/index must not assert competing pixel chains.
                    if decoded[token][1]!=group['source_rgba_sha256']:
                        if signature in wanted:raise ValueError('Conflicting HD source mip identity')
                        continue
                if ref['source_sha256']!=old_ref['source_sha256']:rebound.add(group['key'])
                bindings[group['key']].append(dict(ref,group_index=number,dimensions=decoded[token][0]))
                matched.add(group['key'])
            if len(seen)%200==0:print('Verified source resources:',len(seen),flush=True)
    for group in all_groups:
        if group['key'] in bindings and group['key'] not in matched:
            missing.append(dict(key=group['key'],origin=group['origin'],reason='referenced resource not present in current English archives'))
    by_origin=collections.Counter(g['origin'] for g in all_groups if g['key'] in matched)
    with rzp.open('rb') as source:archive_digest=hashlib.file_digest(source,'sha256').hexdigest()
    result=dict(status='INCOMPLETE' if missing else 'SOURCE_PIXELS_VERIFIED',pack_manifest_sha256=sha(manifest_raw),
        index_sha256=sha(rzl.read_bytes()),archive_sha256=archive_digest,total_groups=len(all_groups),
        source_verified_groups=len(matched),source_verified_by_origin=dict(by_origin),
        decoded_unique_textures=len(decoded),source_hash_rebound_with_exact_mip_proof=len(rebound),missing_groups=len(missing),missing_by_origin=dict(collections.Counter(r['origin'] for r in missing)),
        missing=missing,bindings=bindings,PNGs_copied=0,active_pack_changed=False,
        HD_regenerated=False,complete_player_installer=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('bindings','missing')},indent=2))


if __name__=='__main__':main()
