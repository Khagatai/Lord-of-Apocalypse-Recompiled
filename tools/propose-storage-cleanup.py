"""Prepare a review-only cleanup proposal. No deletion, archiving or commits."""
import json,os,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'private'
def record(path):return dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,mtime_ns=path.stat().st_mtime_ns)
def main():
    deletions=[]
    for path in PRIVATE.glob('*/mip-gpu-check.exe'):deletions.append(dict(record(path),reason='Rebuildable historical renderer QA executable; keep reports and captures.'))
    prototype=PRIVATE/'mip-prototype-build-04/mip-prototype.exe'
    if prototype.is_file():deletions.append(dict(record(prototype),reason='Old experimental preview executable; normal game uses native-release.'))
    recovery=PRIVATE/'release-backups/15ed54979675ee1ead541d7c43b6863ed48a171f5db0448aa85c07fd7d07463f.exe'
    if recovery.is_file():
        for path in recovery.parent.glob('*.exe'):
            if path!=recovery:deletions.append(dict(record(path),reason='Extra historical recovery executable; retain the known pre-networking recovery build.'))
    archive=[]
    prefixes=('hd-','mip-','sampler-','neural-','campaign-','character-','environment-','title-ui-','menu-art-','background-','portrait-','quality-','text-sharpening-','texture-settings-','ui-original-','ui-player-')
    for folder in PRIVATE.iterdir():
        if not folder.is_dir() or folder.is_symlink() or not folder.name.startswith(prefixes):continue
        for current,dirs,files in os.walk(folder,followlinks=False):
            dirs[:]=[d for d in dirs if not (Path(current)/d).is_symlink()]
            for name in files:
                path=Path(current)/name
                if path.suffix.lower()=='.ppm' and not path.is_symlink():archive.append(record(path))
    sample=[]
    # Read a varied bounded sample into memory; compression output is discarded.
    seen=set()
    for row in sorted(archive,key=lambda value:-value['bytes']):
        group=Path(row['path']).parts[1]
        if group in seen:continue
        seen.add(group);data=(ROOT/row['path']).read_bytes();compressed=zlib.compress(data,6)
        sample.append(dict(path=row['path'],bytes=len(data),compressed_sample_bytes=len(compressed)))
        if len(sample)==16:break
    raw=sum(r['bytes'] for r in archive);sample_raw=sum(r['bytes'] for r in sample);sample_compressed=sum(r['compressed_sample_bytes'] for r in sample)
    fraction=sample_compressed/sample_raw if sample_raw else 1
    result=dict(scope='proposal-only-awaiting-user-review',deleted=False,archived=False,git_commit_created=False,
        delete_bytes=sum(r['bytes'] for r in deletions),delete_candidates=deletions,
        lossless_archive_raw_bytes=raw,lossless_archive_candidates=archive,compression_samples=sample,
        estimated_archive_savings_bytes=round(raw*(1-fraction)),
        estimate_limit='Estimate from 16 raw-frame samples, not a measured archive. Frames remain untouched. Restoring raw paths would be required for historical raw-frame checks.',
        protected=['Original Japanese ISO and original patch inputs','Current WIP image/archive pair and stable English baseline','Active HD pack and source texture catalogs','All real saves, save backups and settings','Editable translation data and local translation engines/models','Current native executable, runtime DLLs, fonts and required module/image/trace inputs','Steam adapter, official SDK and current networking dependencies','One known pre-networking recovery executable','QA reports, logs, PNG captures, current oracle evidence and raw source RGBA captures'])
    output=PRIVATE/'storage-cleanup-proposal.json';output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(delete_candidates=len(deletions),delete_gib=round(result['delete_bytes']/2**30,3),
                         archive_files=len(archive),archive_raw_gib=round(raw/2**30,3),
                         archive_savings_estimate_gib=round(result['estimated_archive_savings_bytes']/2**30,3),
                         compression_sample_fraction=round(fraction,3),proposal=str(output),nothing_deleted=True),indent=2))
if __name__=='__main__':main()
