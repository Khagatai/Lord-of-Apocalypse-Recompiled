"""Verify a private sample's exact files and enable the real host pack reader."""
import hashlib
import json
from pathlib import Path
import struct
import re
import configparser
import sampler_pack

ROOT=Path(__file__).resolve().parents[1]


def selected_folder(graphics, renderer, namespace, explicit=None):
    """Keep the WIP pack out of the Japanese/v1.6 image and software renderer."""
    if explicit is not None:
        if renderer!='vulkan' or namespace!='english-text-test':
            raise ValueError('The HD world/model pack requires Vulkan and the WIP English variant')
        return Path(explicit)
    if graphics['hd_ui'] and renderer=='vulkan' and namespace=='english-text-test':
        return ROOT/'private/hd-remaster-pack'
    return None


def verify_sample(folder, private_root=ROOT/'private',cache_path=None):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(Path(private_root).resolve()) or not folder.is_dir():
        raise ValueError('Texture sample must be a folder under private/')
    manifest=folder/'sample.json'
    report=json.loads(manifest.read_text(encoding='utf-8-sig'))
    if report.get('scope')=='verified-mip-texture-pack':
        if cache_path is None:return verify_mip_pack(folder,report,manifest)
        from texture_cache import PackCache,PackChangedDuringVerification
        cache_path=Path(cache_path).resolve()
        if not cache_path.is_relative_to(Path(private_root).resolve()) or cache_path.is_relative_to(folder):
            raise ValueError('Keep the verification cache private and outside the pack')
        for attempt in range(2):
            cache=PackCache(folder,cache_path)
            # Following a race, rehash every PNG rather than accepting old hits.
            if attempt:cache.old={}
            try:
                result=verify_mip_pack(folder,report,manifest,cache=cache)
                result['verification_cache']['validation_retries']=attempt
                return result
            except PackChangedDuringVerification:
                if attempt:raise
    if report.get('scope')=='verified-ui-texture-pack':
        entries=report.get('textures')
        if not isinstance(entries,list) or not 1<=len(entries)<=256:
            raise ValueError('Invalid texture pack image count')
        names=set()
        for entry in entries:
            if not isinstance(entry,dict):
                raise ValueError('Invalid texture pack entry')
            name=entry.get('file','')
            if not isinstance(name,str) or not re.fullmatch(r'ui-[0-9]{3}\.png',name) or name in names:
                raise ValueError('Invalid or duplicate texture pack filename')
            names.add(name)
            file=(folder/name).resolve()
            if not file.is_relative_to(folder) or not file.is_file():
                raise ValueError('Texture pack image missing or hash mismatch')
            data=file.read_bytes()
            if hashlib.sha256(data).hexdigest()!=entry.get('sha256'):
                raise ValueError('Texture pack image missing or hash mismatch')
            if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n':
                raise ValueError('Texture pack image is not a PNG')
            width,height=struct.unpack_from('>II',data,16)
            if (width,height)!=(entry.get('width'),entry.get('height')) or not (1<=width<=2048 and 1<=height<=2048):
                raise ValueError('Texture pack image dimensions differ')
        ini=(folder/'textures.ini').resolve()
        if not ini.is_relative_to(folder) or not ini.is_file() or hashlib.sha256(ini.read_bytes()).hexdigest()!=report.get('ini_sha256'):
            raise ValueError('Texture pack INI missing or hash mismatch')
        return {'folder':str(folder),'sample_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                'ini_sha256':report['ini_sha256'],'scope':report['scope'],'textures':entries,'complete_hd_pack':False}
    if report.get('scope') not in ('one-region-vector-typeset-ui-sample','multi-region-vector-typeset-ui-sample'):
        raise ValueError('Unknown texture sample format')
    if report['scope']=='multi-region-vector-typeset-ui-sample' and (type(report.get('region_count')) is not int or not 2<=report['region_count']<=64):
        raise ValueError('Invalid texture sample region count')
    if type(report.get('factor')) is not int or not 2<=report['factor']<=4:
        raise ValueError('Unsupported texture sample factor')
    for name,key in (('textures.ini','ini_sha256'),('ui-sample.png','png_sha256')):
        file=(folder/name).resolve()
        if not file.is_relative_to(folder) or not file.is_file():
            raise ValueError('Texture sample file leaves its folder or is missing')
        if hashlib.sha256(file.read_bytes()).hexdigest()!=report.get(key):
            raise ValueError('Texture sample hash mismatch: '+name)
    data=(folder/'ui-sample.png').read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n' or len(data)<24:
        raise ValueError('Texture sample is not a PNG')
    width,height=struct.unpack_from('>II',data,16)
    if (width,height)!=(report.get('width'),report.get('height')) or not (1<=width<=2048 and 1<=height<=2048):
        raise ValueError('Texture sample dimensions differ')
    return {'folder':str(folder),'sample_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'png_sha256':report['png_sha256'],'ini_sha256':report['ini_sha256'],
            'scope':report['scope'],'complete_hd_pack':False}


def verify_mip_pack(folder,report,manifest,ini_override=None,cache=None):
    namespace=sampler_pack.validate(report.get('sampler_namespace'))
    groups=report.get('textures')
    if not isinstance(groups,list) or not 1<=len(groups)<=65536:
        raise ValueError('Invalid mip pack texture count')
    expected={};names={};mip_chains=0
    for group in groups:
        if not isinstance(group,dict):raise ValueError('Invalid mip texture group')
        key=group.get('key','')
        if not isinstance(key,str) or not re.fullmatch('[0-9a-f]{24}',key):
            raise ValueError('Invalid mip texture identity')
        w,h,f=group.get('source_width'),group.get('source_height'),group.get('factor')
        if any(type(x) is not int for x in (w,h,f)) or not (1<=w<=512 and 1<=h<=512 and 2<=f<=6 and max(w,h)*f<=2048):
            raise ValueError('Invalid mip texture source dimensions or factor')
        levels=group.get('levels')
        if not isinstance(levels,list) or not 1<=len(levels)<=8:
            raise ValueError('Invalid mip chain level count')
        if len(levels)>max(w*f,h*f).bit_length():
            raise ValueError('Mip chain exceeds Vulkan image level count')
        mip_chains+=len(levels)>1
        for level,entry in enumerate(levels):
            if not isinstance(entry,dict):raise ValueError('Invalid mip image entry')
            name=entry.get('file','')
            if not isinstance(name,str) or not re.fullmatch(r'tex-[0-9]{3,5}-[0-7]\.png',name):
                raise ValueError('Invalid mip filename')
            identity=key+'_'+str(level)
            if identity in expected:raise ValueError('Invalid duplicate mip identity')
            expected[identity]=name
            signature=(entry.get('width'),entry.get('height'),entry.get('sha256'))
            if name in names:
                if names[name]!=signature:raise ValueError('Conflicting mip filename alias')
                if signature[:2]!=(max(1,w*f>>level),max(1,h*f>>level)):
                    raise ValueError('Mip dimensions do not form a complete halving chain')
                continue
            names[name]=signature
            wanted=(max(1,w*f>>level),max(1,h*f>>level))
            if signature[:2]!=wanted:raise ValueError('Mip dimensions do not form a complete halving chain')
            if cache is not None:
                cache.png(name,entry.get('sha256'),wanted)
                continue
            path=(folder/name).resolve()
            if not path.is_relative_to(folder) or not path.is_file():
                raise ValueError('Mip PNG missing or hash mismatch')
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest()!=entry.get('sha256'):
                raise ValueError('Mip PNG missing or hash mismatch')
            if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Mip image is not a PNG')
            width,height=struct.unpack_from('>II',data,16)
            if (width,height)!=(max(1,w*f>>level),max(1,h*f>>level)) or (width,height)!=(entry.get('width'),entry.get('height')):
                raise ValueError('Mip dimensions do not form a complete halving chain')
    if len(names)>65536:raise ValueError('Too many mip images')
    ini_path=folder/'textures.ini'
    if ini_override is not None:
        ini_path=Path(ini_override).resolve()
        if ini_path.parent!=Path(folder).resolve():
            raise ValueError('Temporary pack INI must remain inside the pack folder')
    if ini_path.is_file() and ini_path.stat().st_size>(4<<20):raise ValueError('Mip INI exceeds the pinned reader limit')
    if not ini_path.is_file() or hashlib.sha256(ini_path.read_bytes()).hexdigest()!=report.get('ini_sha256'):
        raise ValueError('Mip pack INI missing or hash mismatch')
    ini=configparser.ConfigParser(interpolation=None,strict=True)
    ini.read(ini_path,encoding='utf-8-sig')
    if set(ini.sections())!={'options','games','hashes'} or dict(ini['options'])!={'hash':'quick'} or dict(ini['games'])!={'npjh50503':'textures.ini'} or dict(ini['hashes'])!=expected:
        raise ValueError('Mip INI does not exactly match verified images')
    result={'folder':str(folder),'sample_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'ini_sha256':report['ini_sha256'],'scope':report['scope'],'textures':groups,
            'mip_chains':mip_chains,'images':len(names),'sampler_namespace':namespace,'complete_hd_pack':False}
    if cache is not None:result['verification_cache']=cache.finish()
    return result


def enable(env, folder):
    manifest=Path(folder)/'sample.json'
    namespace=sampler_pack.validate(json.loads(manifest.read_text(encoding='utf-8-sig')).get('sampler_namespace')) if manifest.is_file() else None
    env['LOA_SAMPLER_PACK']='1' if namespace else '0'
    value=env.get('SR_ACE','off')
    if value=='off':
        value=('v1;tier=enhanced;af=0;text=off;readout=off;notice=off;wide=off;'
               'smooth=off;sas=off;tess=off;twin=off;mips=off;ssaa=off')
    env['SR_ACE']=value+';texpack=on'
    env['SR_TEX_REPLACE']=str(Path(folder).resolve())
    env['SR_TEX_REPLACE_BUDGET_MB']='256'
