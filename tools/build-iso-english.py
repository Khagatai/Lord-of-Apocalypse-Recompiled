"""Build an English candidate directly from the original ISO and local text/render recipes.

No upstream patched ISO, prepared archive or binary delta is used. Output stays
private and is not promoted to the working game. Movie-caption/HD generation
are separate installer stages.
"""
import argparse,collections,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from iso_archive import original_archive
from rgf_archive import parse_index,resources
from rgf_edits import append_edits
from iso_edits import append_files,extent_hash,survey
from mes_codec import GlyphTable
from message_recipe import reconstruct_bundle
from texture_text import reconstruct

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--messages',type=Path,default=ROOT/'private/local-build/japanese-messages.json')
    parser.add_argument('--textures',type=Path,default=ROOT/'private/local-build/text-rendering/result.json')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--image-name',default='LordOfApocalypse-English-ISO-built.iso');args=parser.parse_args()
    if Path(args.image_name).name!=args.image_name or not args.image_name.endswith('.iso'):raise ValueError('Invalid generated image name')
    output=args.output.resolve();image=args.image.resolve(strict=True)
    if not output.is_relative_to(ROOT/'private') or output.exists():raise ValueError('Use a fresh private candidate directory')
    messages=json.loads(args.messages.read_text(encoding='utf-8'));textures=json.loads(args.textures.read_text())
    if messages.get('all_changed_MES_reconstructed') is not True or textures.get('ISO_only_texture_generation_complete') is not True:raise ValueError('Text/local-render recipe verification is incomplete')
    plans={}
    for kind,rows in [('message',messages['bundles']),('texture',textures['resources'])]:
        for row in rows:
            key=row['group_index'],int(row['resource_id'],16),row['occurrence']
            if key in plans:raise ValueError('Duplicate source occurrence recipe')
            plans[key]=kind,row
    source={};glyphs=set();counts=collections.Counter();original_hashes={}
    with original_archive(image) as (index,archive):
        for group,identity,raw in resources(archive,parse_index(index,archive.size)):
            occurrence=counts[group,identity];counts[group,identity]+=1;key=group,identity,occurrence
            original_hashes[key]=hashlib.sha256(raw).hexdigest()
            if key in plans:source[key]=raw
            if identity==0x50d78:glyphs.add(raw)
    if set(source)!=set(plans) or len(glyphs)!=1:raise ValueError('Required original resources missing')
    glyph=glyphs.pop()
    if hashlib.sha256(glyph).hexdigest()!=messages['glyph_table_sha256']:raise ValueError('Original glyph table differs')
    table=GlyphTable.parse(glyph);replacements={};expected=dict(original_hashes)
    for key,(kind,plan) in plans.items():
        raw=source[key]
        rebuilt=reconstruct_bundle(raw,plan,table) if kind=='message' else reconstruct(raw,plan,ROOT/'private')
        digest=hashlib.sha256(rebuilt).hexdigest()
        if digest!=plan['target_sha256']:raise ValueError('Local resource reconstruction differs')
        identity=key[0],key[2],key[1],original_hashes[key]
        replacements[identity]=rebuilt;expected[key]=digest
    output.mkdir(parents=True)
    (output/'owner.json').write_text(json.dumps(dict(tool='build-iso-english-v1',source_ISO_sha256=sha(image),
        message_recipe_sha256=sha(args.messages),render_recipe_sha256=sha(args.textures),image_name=args.image_name),indent=2)+'\n')
    with original_archive(image) as (index,archive):
        with (output/'REGFILE.RZP').open('w+b') as target:
            shutil.copyfileobj(archive,target,1024*1024);target.flush()
            rebuilt,checks=append_edits(index,archive,target,replacements)
        (output/'REGFILE.RZL').write_bytes(rebuilt)
    counts=collections.Counter();verified=0
    with (output/'REGFILE.RZP').open('rb') as stream:
        for group,identity,raw in resources(stream,parse_index(rebuilt,(output/'REGFILE.RZP').stat().st_size)):
            occurrence=counts[group,identity];counts[group,identity]+=1
            if hashlib.sha256(raw).hexdigest()!=expected[group,identity,occurrence]:raise ValueError('Built archive resource differs')
            verified+=1
    if verified!=len(expected):raise ValueError('Archive resource count changed')
    candidate=output/args.image_name
    shutil.copyfile(image,candidate)
    with image.open('rb') as source_stream,candidate.open('r+b') as target,(output/'REGFILE.RZL').open('rb') as rzl,(output/'REGFILE.RZP').open('rb') as rzp:
        append_files(source_stream,target,{'PSP_GAME/USRDIR/UPDATA/REGFILE.RZL':rzl,'PSP_GAME/USRDIR/UPDATA/REGFILE.RZP':rzp})
    unchanged=0
    with image.open('rb') as original,candidate.open('rb') as target:
        before=survey.ISO(original).files();after=survey.ISO(target).files()
        if set(before)!=set(after):raise ValueError('ISO directory membership changed')
        for name,row in before.items():
            if name in ('PSP_GAME/USRDIR/UPDATA/REGFILE.RZL','PSP_GAME/USRDIR/UPDATA/REGFILE.RZP'):continue
            new=after[name]
            if row['size']!=new['size'] or extent_hash(original,row['lba']*2048,row['size'])!=extent_hash(target,new['lba']*2048,new['size']):raise ValueError('Non-text ISO payload changed: '+name)
            unchanged+=1
    report=dict(status='PASS',scope='English ISO built directly from original Japanese ISO',candidate=str(candidate),candidate_sha256=sha(candidate),candidate_size=candidate.stat().st_size,
        all_resource_payloads_verified=True,resource_occurrences_verified=verified,changed_resource_occurrences=len(plans),unchanged_non_text_ISO_files=unchanged,
        source_ISO_sha256=sha(image),upstream_patched_ISO_used=False,binary_delta_used=False,prepared_game_assets_copied_in=False,
        audio_and_game_code_unchanged=True,active_game_changed=False,movie_caption_bundle_generated=False,HD_pack_generated=False,complete_player_installer=False,
        message_recipe_sha256=sha(args.messages),render_recipe_sha256=sha(args.textures))
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
