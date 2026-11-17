"""Read-only audit of dependencies still needed for the ISO-only English/HD setup."""
import argparse,collections,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from rgf_archive import parse_index,resources

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def archive_identities(folder):
    index=(folder/'REGFILE.RZL').read_bytes();archive=folder/'REGFILE.RZP'
    groups=parse_index(index,archive.stat().st_size);identities={};duplicates=collections.Counter()
    with archive.open('rb') as stream:
        for group,identity,raw in resources(stream,groups):
            index=duplicates[group,identity];duplicates[group,identity]+=1
            identities[group,identity,index]=hashlib.sha256(raw).hexdigest()
    return identities

def audit():
    original=archive_identities(ROOT/'private/translation/archives/japanese')
    target=archive_identities(ROOT/'private/translation/text-pass-16-archives')
    if set(original)!=set(target):raise ValueError('Archive occurrence topology changed; do not infer translation correspondence')
    changes=collections.Counter();changed=0;glyphs=[]
    for key,before in original.items():
        if before!=target[key]:
            changed+=1;changes[f'{key[1]>>16:04x}']+=1
            if key[1]==0x50d78:glyphs.append(key[0])
    textures=json.loads((ROOT/'private/translation/english-review/full-textures.json').read_text())['resources']
    pixels=[edit for row in textures for edit in row.get('edits',[])]
    missing=[edit['rgba_path'] for edit in pixels if not Path(edit['rgba_path']).is_file()]
    # A pixel file and its hash are not executable generation instructions.
    pack=json.loads((ROOT/'private/hd-remaster-pack/sample.json').read_text())
    origins=collections.Counter(group.get('origin','unknown') for group in pack['textures'])
    no_refs=sum(not group.get('archive_references') for group in pack['textures'])
    captions=json.loads((ROOT/'private/translation/movie-captions/result.json').read_text())
    report=dict(schema=1,status='INCOMPLETE',scope='read-only ISO-only generation dependency audit',
        archive_occurrences=len(original),changed_occurrences_from_Japanese=changed,changed_kinds=dict(sorted(changes.items())),glyph_table_changed=bool(glyphs),
        translation_recipe=dict(current_base='upstream v1.6, not original Japanese',
            message_plan_sha256=sha(ROOT/'private/translation/english-review/full-messages.json'),
            texture_plan_sha256=sha(ROOT/'private/translation/english-review/full-textures.json'),
            rendered_pixel_inputs=len(pixels),unique_rendered_pixel_inputs=len({p['rgba_path'] for p in pixels}),missing_pixel_inputs=len(missing),
            direct_Japanese_recipe_verified=False),
        HD_recipe=dict(groups=len(pack['textures']),origins=dict(origins),groups_without_direct_archive_references=no_refs,
            generation_from_ISO_only_verified=False),
        captions=dict(bundle_sha256=sha(ROOT/'private/translation/movie-captions/captions.bin'),
            renderer_available=(ROOT/'tools/render-movie-captions.ps1').is_file(),ISO_only_recipe_verified=False),
        blocking_work=[
            'Build all guest code and memory images locally, then validate native boot.',
            'Rebase the complete English recipe onto the original Japanese archive; do not bundle the upstream patched image.',
            'Replace rendered texture/caption pixel dependencies with local rendering instructions and ISO-derived inputs.',
            'Resolve HD groups without direct archive references using verified ISO extraction or a measured local capture route.',
            'Perform a clean install with no copied game binaries/assets before replacing Setup.exe.'],
        ready_to_publish=False)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'private/local-build/dependency-audit.json')
    args=parser.parse_args();destination=args.output.resolve()
    if not destination.is_relative_to(ROOT/'private'):raise ValueError('Keep dependency audit private')
    report=audit();destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
