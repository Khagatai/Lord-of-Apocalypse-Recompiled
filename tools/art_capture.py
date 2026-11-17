"""Admit observed single-level 3D art only when exact archive pixels agree."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def observed_art(capture,catalog):
    capture=Path(capture).resolve();catalog=Path(catalog).resolve()
    if not capture.is_relative_to(ROOT/'private') or not catalog.is_relative_to(ROOT/'private'):
        raise ValueError('Artwork inputs must remain private')
    raw=(catalog/'catalog.json').read_bytes();archive=json.loads(raw)
    identities={}
    for entry in archive:
        if entry['mip_levels']!=1:continue
        base=entry['authored_levels'][0]
        if 'rgba_sha256' not in base:continue
        signature=(entry['width'],entry['height'],base['rgba_sha256'])
        for key in entry['candidate_keys']:
            identities.setdefault((key,signature),[]).append(dict(resource_id=entry['resource_id'],
                source_sha256=entry['source_sha256'],texture_index=entry['texture_index'],name=entry['name']))
    metadata=(capture/'art-capture.jsonl').read_bytes();rows=[json.loads(x) for x in metadata.splitlines()]
    if not 1<=len(rows)<=512:raise ValueError('Invalid bounded artwork capture count')
    variants={};unmatched=[]
    for row in rows:
        key=row.get('key','');content=row.get('content','');wrap=row.get('wrap')
        if not re.fullmatch('[0-9a-f]{24}',key) or not re.fullmatch('[0-9a-f]{16}',content):raise ValueError('Invalid artwork identity')
        if type(wrap) is not int or wrap not in (0,1,256,257):raise ValueError('Invalid artwork wrap')
        if row.get('written') is not True or row.get('decoded') is not True:raise ValueError('Artwork capture write/decode failed')
        if row.get('levels')!=1 or row.get('level')!=0 or row.get('through') is not False:raise ValueError('Expected single-level 3D art')
        width,height=row.get('width'),row.get('height')
        if any(type(x) is not int or not 32<=x<=512 for x in (width,height)):raise ValueError('Invalid artwork dimensions')
        name=f'art-{key}-{content}-{wrap:03x}.rgba'
        if row.get('file')!=name:raise ValueError('Invalid artwork filename')
        path=(capture/name).resolve()
        if not path.is_relative_to(capture):raise ValueError('Artwork path escapes capture')
        data=path.read_bytes()
        if len(data)!=width*height*4:raise ValueError('Artwork RGBA extent differs')
        digest=hashlib.sha256(data).hexdigest();canonical='00000000'+key[8:]
        signature=(width,height,digest);references=identities.get((canonical,signature))
        if not references:
            unmatched.append(dict(key=canonical,rgba_sha256=digest,width=width,height=height));continue
        item=dict(row,path=path,sha256=digest,references=references)
        variants.setdefault(canonical,[]).append((wrap,[item]))
    chosen=[];ambiguous=[];unmatched_keys={r['key'] for r in unmatched}
    for key,entries in variants.items():
        signatures={(wrap,tuple((r['width'],r['height'],r['sha256']) for r in levels)) for wrap,levels in entries}
        if len(signatures)!=1 or key in unmatched_keys:ambiguous.append(key);continue
        wrap,levels=entries[0];chosen.append((key,wrap,levels))
    chosen.sort(key=lambda item:(-item[2][0]['width']*item[2][0]['height'],item[0]))
    report=dict(scope='observed-single-level-3d-archive-matches',captured=len(rows),matched_keys=len(chosen),
                ambiguous=sorted(ambiguous),unmatched=unmatched,catalog_sha256=hashlib.sha256(raw).hexdigest(),
                capture_sha256=hashlib.sha256(metadata).hexdigest())
    return chosen,report
