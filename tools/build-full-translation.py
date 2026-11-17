"""Build MES edits and caption/texture edits together using one staging archive pair."""
import argparse,hashlib,importlib.util,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mes_codec import GlyphTable
from rgf_archive import parse_index,resources
from rgf_edits import append_edits
from texture_text import digest,reconstruct,verify
spec=importlib.util.spec_from_file_location('batch_builder',ROOT/'tools/build-translation-batch.py');batch=importlib.util.module_from_spec(spec);spec.loader.exec_module(batch)
def file_hash(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('messages',type=Path);parser.add_argument('--textures',type=Path,required=True)
    parser.add_argument('--archives',type=Path,default=ROOT/'private/translation/archives/english-v16')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pass-number',type=int,default=19)
    args=parser.parse_args();out=args.output.resolve()
    from translation_baseline import ensure_archives
    args.archives=ensure_archives(args.archives)
    if args.pass_number<1:parser.error('Translation pass must be positive')
    if not out.is_relative_to(ROOT/'private') or out.exists():parser.error('Use a fresh private staging directory')
    for path in (args.messages,args.textures,args.archives):
        if not path.resolve().is_relative_to(ROOT/'private'):raise ValueError('Game-derived inputs must remain private')
    raw_messages=args.messages.read_bytes();raw_textures=args.textures.read_bytes()
    messages=json.loads(raw_messages)['bundles'];texture_list=json.loads(raw_textures)['resources']
    textures={int(row['resource_id'],16):row for row in texture_list}
    if len(textures)!=len(texture_list):raise ValueError('Duplicate texture/layout identities')
    wanted={(int(row['resource_id'],16),row['source_bundle_sha256']) for row in messages}
    original={name:file_hash(args.archives/name) for name in ('REGFILE.RZL','REGFILE.RZP')}
    index=(args.archives/'REGFILE.RZL').read_bytes();groups=parse_index(index,(args.archives/'REGFILE.RZP').stat().st_size)
    payloads={};glyphs=set();pixel_edits={};checked=[]
    with (args.archives/'REGFILE.RZP').open('rb') as source:
        for _,identity,raw in resources(source,groups):
            if identity==0x50d78:glyphs.add(raw)
            key=identity,digest(raw)
            if key in wanted:payloads[key]=raw
            if identity in textures and digest(raw)==textures[identity]['source_sha256'] and key not in pixel_edits:
                row=textures[identity];target=reconstruct(raw,row,ROOT/'private')
                if target==raw:raise ValueError('Texture/layout edit makes no change')
                verified=dict(row,target_sha256=digest(target));verify(raw,target,verified,ROOT/'private')
                checked.append(verified);pixel_edits[key]=target
    if len(glyphs)!=1 or len(checked)!=len(textures):raise ValueError('Required glyph/texture source variant missing')
    glyph_raw=glyphs.pop();replacements,affected=batch.prepare_replacements(messages,payloads,GlyphTable.parse(glyph_raw))
    if set(replacements)&set(pixel_edits):raise ValueError('Message and texture replacement collision')
    replacements.update(pixel_edits);out.mkdir(parents=True)
    shutil.copyfile(args.archives/'REGFILE.RZP',out/'REGFILE.RZP')
    with (args.archives/'REGFILE.RZP').open('rb') as source,(out/'REGFILE.RZP').open('r+b') as target:
        rebuilt,checks=append_edits(index,source,target,replacements)
    (out/'REGFILE.RZL').write_bytes(rebuilt)
    if any(file_hash(args.archives/name)!=expected for name,expected in original.items()):raise ValueError('Source archive changed')
    text_report=dict(scope='verified-local-texture-text-regions',resources=checked)
    path=out/'texture-text-report.json';path.write_text(json.dumps(text_report,indent=2)+'\n')
    result=dict(status='candidate-not-installed-requires-in-game-review',translation_complete=False,translation_pass=args.pass_number,
        scope='text-and-caption-layout-only',manifest_sha256=digest(raw_messages),texture_manifest_sha256=digest(raw_textures),
        glyph_table_sha256=digest(glyph_raw),resource_id=None,resource_ids=sorted({r['resource_id'] for r in messages}|{r['resource_id'] for r in checked}),
        edited_bundle_variants=len(messages),edited_messages=sum(len(r['entries']) for r in messages),affected_message_entries=affected,
        source_archives_sha256=original,source_unchanged=True,candidate_archives_sha256={name:file_hash(out/name) for name in original},
        texture_text_resource_variants=len(checked),caption_layout_resource_variants=sum(r.get('caption_layout') is True for r in checked),
        translated_texture_images=sum(len(r.get('edits',[])) for r in checked),texture_text_report_sha256=file_hash(path),**checks)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('translation_pass','edited_messages','translated_texture_images','all_resource_payloads_verified','candidate_archives_sha256')},indent=2))
if __name__=='__main__':main()
