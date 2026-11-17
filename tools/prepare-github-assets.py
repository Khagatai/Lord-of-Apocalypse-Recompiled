"""Prepare local tester candidate downloads directly, without an oversized ZIP copy.

Contains game-derived runtime/textures: this tool does not authorize publication.
"""
import argparse,hashlib,importlib.util,json,os,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('package_test_build',ROOT/'tools/package-test-build.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
VERSION='0.9.0-beta.1'

def prepare(output,replace=False):
    output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    if list(output.iterdir()):
        if not replace:raise FileExistsError('Use an empty payload folder, or explicitly replace the verified local candidate')
        previous=json.loads((package.WORK/'github-assets-result.json').read_text())
        allowed={'SHA256SUMS.txt','PUBLICATION-STATUS.txt'}
        for row in previous['assets']:
            path=Path(row['path'])
            if path.parent!=output or path.is_symlink() or package.sha(path)!=row['sha256']:raise ValueError('Previous candidate changed; refusing replacement')
            allowed.add(path.name)
        if {p.name for p in output.iterdir()}!=allowed:raise ValueError('Unexpected files in candidate folder')
    started=time.monotonic();items=package.inventory()
    proof=json.loads((package.WORK/'patch-verification.json').read_text())
    image=ROOT/'private/translation/text-pass-16-image/LordOfApocalypse-English-WIP.iso'
    delta=package.WORK/'patches/english-wip.vcdiff'
    source_sha='3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93'
    target=dict(size=image.stat().st_size,sha256=package.sha(image))
    delta_sha=package.verify_patch_proof(proof,'english-wip',source_sha,target,delta)
    patch_name='private/distribution/patches/english-wip.vcdiff';items[patch_name]=delta
    manifest=dict(schema=1,original=dict(size=1068498944,sha256=source_sha),
        images=[dict(label='WIP English (work in progress)',path=image.relative_to(ROOT).as_posix(),
                     **target,patch=patch_name,patch_sha256=delta_sha)],
        patcher=dict(path='private/tools/xdelta/xdelta3.exe',sha256=package.sha(ROOT/'private/tools/xdelta/xdelta3.exe')))
    generated=package.WORK/'release.json';generated.write_text(json.dumps(manifest,indent=2)+'\n')
    items['private/distribution/release.json']=generated
    extras={'READ-ME-FIRST.txt':(ROOT/'config/PLAYER_README.txt').read_text(encoding='utf-8'),
        'private/tools/xdelta/SOURCE.txt':'xdelta 3.0.11, GPL-2.0-or-later. Source: https://github.com/jmacd/xdelta/tree/v3.0.11\n'}
    ordered=sorted(items,key=lambda n:(n.startswith('private/hd-remaster-pack/') and n.endswith('.png'),n))
    groups=[[]];size=0;limit=1800*1024*1024
    for name in ordered:
        length=items[name].stat().st_size
        if length>=limit:raise ValueError('Single file exceeds release part budget: '+name)
        if groups[-1] and size+length>limit:groups.append([]);size=0
        groups[-1].append(name);size+=length
    records=[];assets=[];expanded=0
    for number,group in enumerate(groups,1):
        path=output/f'Lord-of-Apocalypse-Recompiled-v{VERSION}-Windows-x64-part{number:02}-of{len(groups):02}.zip'
        temporary=path.with_suffix('.zip.part')
        if temporary.exists():raise FileExistsError('Interrupted part requires inspection: '+str(temporary))
        with zipfile.ZipFile(temporary,'w',allowZip64=True) as archive:
            for name in group:
                source=items[name]
                if not package.allowed(name):raise ValueError('Protected package path: '+name)
                info=zipfile.ZipInfo(package.TOP+name,date_time=(2026,11,17,0,0,0));info.external_attr=0o100644<<16
                info.compress_type=zipfile.ZIP_STORED if source.suffix.lower() in ('.png','.zip','.vcdiff') else zipfile.ZIP_DEFLATED
                digest=hashlib.sha256();length=0
                with source.open('rb') as src,archive.open(info,'w',force_zip64=True) as dst:
                    for block in iter(lambda:src.read(1024*1024),b''):dst.write(block);digest.update(block);length+=len(block)
                records.append(dict(path=name,size=length,sha256=digest.hexdigest()));expanded+=length
            if number==len(groups):
                for name,text in extras.items():
                    raw=text.encode('utf-8');archive.writestr(package.TOP+name,raw,compress_type=zipfile.ZIP_DEFLATED)
                    records.append(dict(path=name,size=len(raw),sha256=hashlib.sha256(raw).hexdigest()));expanded+=len(raw)
                data=json.dumps(dict(schema=1,version=VERSION,framework_commit='8704fba98007fff6d6f930365f2b2142af1bfbba',
                    files=records,gameplay_acceptance=False,public_distribution_review_complete=False),indent=2).encode()
                archive.writestr(package.TOP+'PACKAGE-MANIFEST.json',data,compress_type=zipfile.ZIP_DEFLATED);expanded+=len(data)
        if temporary.stat().st_size>=2*1024**3:raise ValueError('Release asset exceeds 2 GiB')
        os.replace(temporary,path)
        assets.append(dict(path=str(path),size=path.stat().st_size,sha256=package.sha(path)))
        print(json.dumps(dict(part=number,total=len(groups),bytes=path.stat().st_size)),flush=True)
    expected={r['path']:r for r in records};seen=set();verified=0
    for asset in assets:
        with zipfile.ZipFile(asset['path']) as archive:
            for info in archive.infolist():
                if not info.filename.startswith(package.TOP):raise ValueError('Unexpected ZIP root')
                name=info.filename[len(package.TOP):]
                if name in seen:raise ValueError('Duplicate ZIP member: '+name)
                seen.add(name)
                if name in expected:
                    with archive.open(info) as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                    if info.file_size!=expected[name]['size'] or digest!=expected[name]['sha256']:raise ValueError('Package integrity failed: '+name)
                    verified+=1
                else:archive.read(info) # also verifies the generated manifest CRC
    if verified!=len(records):raise ValueError('Missing package files')
    report=dict(status='PASS',version=VERSION,assets=assets,expanded_size=expanded,
        independent_zips=True,all_under_2_GiB=True,crc_verified=True,manifest_files_verified=verified,
        ISOs=0,saves=0,saved_preferences=0,public_distribution_review_complete=False,
        publication_status='LOCAL TEST CANDIDATE ONLY: game-derived content/licence review unresolved',
        seconds=round(time.monotonic()-started,1))
    (package.WORK/'github-assets-result.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'SHA256SUMS.txt').write_text(''.join(a['sha256']+'  '+Path(a['path']).name+'\n' for a in assets))
    (output/'PUBLICATION-STATUS.txt').write_text(report['publication_status']+'\nThese files are not cleared for public upload under the project\'s original content restrictions.\nNo ISO, save or personal settings are included. The package DOES include game-derived runtime and texture data.\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--local-tester-candidate',action='store_true',required=True)
    parser.add_argument('--replace-local-candidate',action='store_true')
    args=parser.parse_args();print(json.dumps(prepare(args.output,args.replace_local_candidate),indent=2),flush=True)
