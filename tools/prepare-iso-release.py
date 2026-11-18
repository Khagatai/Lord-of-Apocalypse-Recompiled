"""Prepare the ISO-only player payload from public tools, sources and text recipes.

No game executable, module, ISO, texture, caption bitmap or binary delta is
accepted by this inventory. This creates a local candidate; publish only after
the first-run build and installation checks have passed.
"""
import argparse,hashlib,importlib.util,json,os,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import source_identity,title,neural_texture
from player_update import version_key


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def inventory(work, launcher=None):
    source_identity.verify(ROOT,'framework');source_identity.verify(ROOT,'decryptor')
    items={};work.mkdir(parents=True,exist_ok=True)
    def add(path,name=None):
        path=Path(path);name=name or path.relative_to(ROOT).as_posix()
        if path.is_symlink() or not path.is_file() or name in items:raise ValueError('Duplicate/missing release input: '+name)
        if any(p in ('.git','__pycache__','.codex','.agents') for p in Path(name).parts) or Path(name).name.upper() in ('AGENTS.MD','CLAUDE.MD','GEMINI.MD'):
            raise ValueError('Development metadata cannot enter the player payload: '+name)
        if name.startswith(('private/modules/','private/native-release/','private/hd-remaster-pack/','private/memstick/','private/settings/','private/disc/','private/oracle-prefix/')):
            raise ValueError('Game-derived or personal payload path prohibited: '+name)
        items[name]=path
    def generated(name,value):
        path=work/(hashlib.sha256(name.encode()).hexdigest()+'.json');path.write_text(json.dumps(value,indent=2)+'\n');add(path,name)
    for name in ('LICENSE','CREDITS.md'):add(ROOT/name)
    add(launcher or work/'LordOfApocalypse.exe','LordOfApocalypse.exe')
    add(ROOT/'config/PLAYER_README.txt','READ-ME-FIRST.txt')
    for folder in ('tools','config'):
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in ('.py','.c','.cpp','.cs','.h','.mk','.ps1','.json','.toml','.manifest','.txt'):
                if path.name in ('local-build-inputs.json','local-build-player-framework.json','release-download.json','PLAYER_README.txt'):continue
                add(path)
    pins=json.loads((ROOT/'config/local-build-inputs.json').read_text())
    framework=json.loads((ROOT/'config/local-build-framework.json').read_text());selected={}
    for name,digest in framework['files'].items():
        if (name.startswith(('docs/','tests/','.github/')) and name!='docs/cleanroom/PGF_CONVERTER_SPEC.md') or Path(name).name.upper() in ('AGENTS.MD','CLAUDE.MD','GEMINI.MD'):continue
        selected[name]=digest;add(title.FRAMEWORK/name,'external/nakagawa-recomp/'+name)
    framework['files']=selected
    raw=(json.dumps(framework,indent=2)+'\n').encode();path=work/'player-framework.json';path.write_bytes(raw)
    # This is an exact subset of the pinned upstream source manifest; it removes
    # documentation and agent instructions, never substitutes framework code.
    add(path,'config/local-build-player-framework.json')
    pins['framework']=dict(pins['framework'],manifest='config/local-build-player-framework.json',sha256=hashlib.sha256(raw).hexdigest())
    generated('config/local-build-inputs.json',pins)
    decrypt=json.loads((ROOT/'config/local-build-decryptor.json').read_text())
    for name in decrypt['files']:add(ROOT/'private/tools/pspdecrypt'/name)
    sdk=json.loads((work/'SDK-provenance-audit.json').read_text())
    if sdk.get('status')!='PASS' or not sdk.get('files'):raise ValueError('Portable compiler provenance audit has not passed')
    for name,digest in sorted(sdk['files'].items()):
        path=ROOT/'private/toolchain/prerequisites/msys64'/name
        if not name.startswith('ucrt64/') or '..' in Path(name).parts or sha(path)!=digest:
            raise ValueError('Portable compiler differs from audited upstream archive: '+name)
        add(path)
    for path in sorted((ROOT/'private/toolchain/prerequisites/notices').rglob('*')):
        if path.is_file():add(path,'licenses/toolchain/'+path.relative_to(ROOT/'private/toolchain/prerequisites/notices').as_posix())
    add(ROOT/'private/toolchain/prerequisites/installed.json','licenses/toolchain/installed.json')
    add(work/'toolchain-source-manifest.json','licenses/toolchain/SOURCE-MANIFEST.json')
    for path in sorted((work/'upscaler-licenses').iterdir()):
        if path.is_file():add(path,'licenses/upscaler/'+path.name)
    for path in sorted((ROOT/'private/tools/python314').iterdir()):
        if path.is_file() and path.suffix in ('.exe','.dll','.pyd','.zip','._pth','.txt','.cat'):add(path)
    # The optional texture tool is obtained directly from its publisher on first
    # build, with pinned archive/member hashes. Do not redistribute its vendor
    # DLLs or model/demo bundle in this project's public payload.
    # Game-independent connectivity adapters, never the Steam SDK itself.
    for name in ('loa_steam_bridge.dll','steam_api64.dll','bridge.json'):add(ROOT/'private/steam-test'/name)
    for name in ('private/online-deps/build/datachannel/libdatachannel.dll','private/online-deps/build.json'):add(ROOT/name)
    for source in ('private/online-deps','private/steam-test'):
        for path in (ROOT/source).rglob('*'):
            if path.is_file() and path.name.upper().startswith(('LICENSE','COPYING','NOTICE')) and path not in items.values():add(path)
    recipes={}
    for kind,source in dict(messages='japanese-messages.json',textures='portable-text-recipes.json',captions='local-render-caption-recipe.json',HD='portable-hd-recipes.json').items():
        path=ROOT/'private/local-build'/source;name='private/distribution/recipes/'+kind+'.json';add(path,name)
        recipes[kind]=dict(path=name,sha256=sha(path))
    original=dict(size=title.CONFIG['disc']['iso_size'],sha256=title.CONFIG['disc']['iso_sha256'])
    native_tools = set('title.py import_trace_codegen.py frame_rate_codegen.py mip_runtime_patch.py media_runtime_patch.py '
                       'iso_local_setup.py survey-disc.py build-prx-helper.py prx-decrypt.cpp'.split())
    native_tools.update('in-game-settings.c title_settings_menu.h gameplay_fps.c coop_hle.c coop_service_wait.h '
                        'coop_transport.c coop_transport.h online_runtime.c online_runtime.h movie_subtitles.c '
                        'movie_caption_format.h audio_diagnostics.h'.split())
    native_configs = {'config/lordofapocalypse.toml','config/lordofapocalypse.json','config/startup-registers.json',
                      'config/local-build-inputs.json','config/local-build-player-framework.json'}
    native_prefixes = ('external/nakagawa-recomp/', 'private/toolchain/prerequisites/msys64/ucrt64/',
                       'private/tools/pspdecrypt/', 'private/tools/python314/')
    def identity(paths):
        tree = {name: sha(items[name]) for name in sorted(paths)}
        return hashlib.sha256(json.dumps(tree, sort_keys=True).encode()).hexdigest()
    native = {name for name in items if name in native_configs or name.startswith(native_prefixes)
              or (name.startswith('tools/') and (Path(name).name in native_tools or name.endswith('.mk')))}
    def content_identity(recipe_keys, source_names):
        return identity({recipes[k]['path'] for k in recipe_keys} | {'tools/'+name for name in source_names.split()})
    fingerprints = dict(native=identity(native),
        text=content_identity(('textures',), 'build-local-text-images.py render-text-worker.ps1 text_render_worker.py '
                              'render-local-credits.ps1 render-caption-atlas.ps1 texture_text.py inventory-textures.py xet_codec.py'),
        image=content_identity(('messages','textures'), 'build-iso-english.py iso_archive.py message_recipe.py rgf_archive.py'),
        captions=content_identity(('captions',), 'build-local-movie-captions.py build-movie-helper.py movie-caption-survey.c '
                                  'validate-movie-captions.py render-caption-atlas.ps1 render-text-worker.ps1 text_render_worker.py'),
        HD=identity({recipes['HD']['path'],'config/remaster-upscaler.json','config/hd-compatible-pipelines.json',
                     'external/nakagawa-recomp/third_party/xbrz/xbrz.c','external/nakagawa-recomp/src/rt/gpu_sdl3vk/tex_scale.c'} |
                    {'tools/'+name for name in ('build-local-hd-pack.py rebase-local-hd-recipes.py catalog-remaster-textures.py '
                                                'hd_native.py hd-native.c hd_work.py neural_texture.py model-detail.h inventory-textures.py').split()}))
    build=dict(schema=1,pipeline_revision=3,original=original,recipes=recipes,stage_inputs=fingerprints,
               default_language='english-text-test',Japanese_audio=True)
    raw=(json.dumps(build,indent=2)+'\n').encode();path=work/'player-build.json';path.write_bytes(raw);add(path,'config/player-build.json')
    generated('private/distribution/release.json',dict(schema=2,kind='ISO-local-native-build',original=original,
        build_plan=dict(path='config/player-build.json',sha256=hashlib.sha256(raw).hexdigest())))
    return items


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--version',default='0.9.0-beta.2',help='Version without the leading v used in GitHub tags')
    p.add_argument('--launcher',type=Path,help='Use a launcher built separately for this version')
    p.add_argument('--report',type=Path,help='Write the build report here instead of the default staging path');a=p.parse_args()
    version_key(a.version)
    if a.version.startswith('v'):p.error('Use a version without a leading v')
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=True);work=ROOT/'private/local-build/release-staging'
    items=inventory(work,a.launcher);path=output/f'Lord-of-Apocalypse-Recompiled-v{a.version}-ISO-Builder-part01-of01.zip'
    if path.exists():raise FileExistsError('Existing release candidate preserved')
    temporary=path.with_suffix('.zip.part');records=[]
    if temporary.exists():raise FileExistsError('Interrupted ZIP requires inspection')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
        for name,source in sorted(items.items()):
            archive.write(source,'LordOfApocalypse-Recomp/'+name)
            records.append(dict(path=name,size=source.stat().st_size,sha256=sha(source)))
        manifest=dict(schema=2,version=a.version,files=records,game_payloads_included=False,builds_native_game_locally=True)
        archive.writestr('LordOfApocalypse-Recomp/PACKAGE-MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    if temporary.stat().st_size>=2*1024**3:raise ValueError('Player payload exceeds GitHub per-asset limit')
    temporary.replace(path)
    with zipfile.ZipFile(path) as archive:
        bad=archive.testzip()
        if bad:raise ValueError('Release CRC failed: '+bad)
        for row in records:
            with archive.open('LordOfApocalypse-Recomp/'+row['path']) as stream:observed=hashlib.file_digest(stream,'sha256').hexdigest()
            if observed!=row['sha256']:raise ValueError('Release entry hash failed: '+row['path'])
    report=dict(status='PAYLOAD_VERIFIED',version=a.version,assets=[dict(path=str(path),size=path.stat().st_size,sha256=sha(path))],
        package_files=len(records),iso_only_publication_checks_complete=False,game_payloads_included=False,
        builds_native_game_locally=True,clean_install_verified=False)
    (a.report or work/'iso-release-assets.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'Payload-SHA256SUMS.txt').write_text(sha(path)+'  '+path.name+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
