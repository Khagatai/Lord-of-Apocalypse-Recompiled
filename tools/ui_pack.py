"""Combine verified local atlas samples; no game-derived files enter source control."""
import configparser
import hashlib
import json
from pathlib import Path
import re
import texture_pack


def merge(sources, output, private_root=texture_pack.ROOT/'private'):
    output=Path(output).resolve()
    private_root=Path(private_root).resolve()
    if not output.is_relative_to(private_root) or output.exists():
        raise ValueError('Use a fresh private output directory')
    if not 1<=len(sources)<=256:
        raise ValueError('Use 1 to 256 private atlas samples')
    pending=[]
    keys=set()
    for source in sources:
        source=Path(source).resolve()
        verified=texture_pack.verify_sample(source,private_root)
        if verified['scope']=='verified-ui-texture-pack':
            raise ValueError('Merge individual atlas samples, not merged packs')
        ini=configparser.ConfigParser(interpolation=None)
        ini.read(source/'textures.ini',encoding='utf-8-sig')
        if ini.get('options','hash',fallback='')!='quick' or not ini.has_section('hashes') or len(ini['hashes'])!=1:
            raise ValueError('Expected one quick-hash texture per sample')
        key,file=next(iter(ini['hashes'].items()))
        if not re.fullmatch(r'[0-9a-fA-F]{24}',key) or file!='ui-sample.png' or key in keys:
            raise ValueError('Invalid or duplicate texture identity')
        keys.add(key)
        metadata=json.loads((source/'sample.json').read_text(encoding='utf-8-sig'))
        pending.append((source,key,metadata,verified))
    output.mkdir(parents=True)
    entries=[]
    lines=['[options]','hash = quick','[hashes]']
    for index,(source,key,metadata,verified) in enumerate(pending):
        name=f'ui-{index:03d}.png'
        data=(source/'ui-sample.png').read_bytes()
        (output/name).write_bytes(data)
        lines.append(key+' = '+name)
        entries.append({'file':name,'sha256':hashlib.sha256(data).hexdigest(),'width':metadata['width'],
                        'height':metadata['height'],'factor':metadata['factor'],'region_count':metadata.get('region_count',1),
                        'source_manifest_sha256':verified['sample_manifest_sha256']})
    ini=output/'textures.ini'
    ini.write_text('\n'.join(lines)+'\n',encoding='ascii')
    report={'scope':'verified-ui-texture-pack','textures':entries,'ini_sha256':hashlib.sha256(ini.read_bytes()).hexdigest(),
            'complete_hd_pack':False,'visual_quality_validated':False}
    (output/'sample.json').write_text(json.dumps(report,indent=2)+'\n')
    texture_pack.verify_sample(output,private_root)
    return report
