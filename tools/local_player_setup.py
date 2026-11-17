"""First-run, ISO-only native compilation and English/HD generation.

All game-derived output is created privately on the player's PC. A failed or
partial stage is never reported ready, and successful owned stages can resume.
"""
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,source_identity,iso_local_setup,translation_candidate
import setup_progress
import setup_resources
from graphics_settings import preference_lock
TIMINGS=None


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def local(name):
    path=(ROOT/name).resolve()
    if not path.is_relative_to(ROOT/'private'):raise ValueError('Player build path escapes private storage')
    return path


def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');temporary.replace(path)


def plan():
    record=json.loads(local('private/distribution/release.json').read_text())
    if record.get('schema')!=2 or record.get('kind')!='ISO-local-native-build':raise ValueError('Unsupported player build manifest')
    path=(ROOT/record['build_plan']['path']).resolve()
    if not path.is_relative_to(ROOT/'config') or sha(path)!=record['build_plan']['sha256']:raise ValueError('Player build plan identity differs')
    result=json.loads(path.read_text())
    if result.get('schema')!=1 or result.get('original')!=record['original']:raise ValueError('Player build source identity differs')
    for row in result['recipes'].values():
        if sha(local(row['path']))!=row['sha256']:raise ValueError('Player generation recipe changed: '+row['path'])
    return result


def run(script,*args):
    print('Preparing '+script.removesuffix('.py').replace('-',' ')+'...',flush=True)
    started=time.monotonic();code=-1
    try:
        env = title.environment()
        env[setup_progress.PROFILE_ENV] = setup_progress.profile or ''
        process=subprocess.Popen([sys.executable,'-u',str(ROOT/'tools'/script),*map(str,args)],env=env,cwd=ROOT,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1)
        try:
            for line in process.stdout:
                print(line,end='',flush=True)
                if script=='build-local-hd-pack.py':
                    count=re.fullmatch(r'Preparing HD textures: (\d+) / (\d+) jobs complete\s*',line)
                    if count:
                        setup_progress.emit('hd',int(count[1]),int(count[2]))
                        if int(count[1])==int(count[2]):setup_progress.emit('verify')
            code=process.wait()
        finally:
            process.stdout.close()
            if process.poll() is None:process.wait()
        if code:raise subprocess.CalledProcessError(code,script)
    except subprocess.CalledProcessError as error:
        extra=' HD inference details are in private/local-build/HD-work/scratch/inference-*.log.' if script=='build-local-hd-pack.py' else ''
        raise RuntimeError(f'Local setup stage {script} failed (exit {error.returncode}). Completed stages are kept for retry; see the launcher log.'+extra) from error
    finally:
        if TIMINGS:TIMINGS.record(script+(' '+str(args[0]) if script=='title.py' and args else ''),time.monotonic()-started,code)


HD_OUTPUT = 'private/hd-remaster-pack/sample.json'


def base_outputs():
    return (title.CONFIG['module']['file'], title.CONFIG['dynamic_modules']['libfont']['file'],
            'private/native-release/lordofapocalypse/lordofapocalypse.exe',
            'private/native-release/lordofapocalypse/lordofapocalypse_image.bin',
            'private/translation/text-pass-16-image/LordOfApocalypse-English-WIP.iso',
            'private/translation/movie-captions/captions.bin')


def ready(*, with_hd=False):
    marker=local('private/local-build/ready.json')
    if not marker.is_file():return False
    record=json.loads(marker.read_text());manifest=local('private/distribution/release.json')
    if record.get('state')!='READY' or not manifest.is_file() or record.get('release_manifest_sha256')!=sha(manifest):return False
    required = set(base_outputs())
    outputs = {row['path']: row for row in record.get('outputs', [])}
    if set(outputs) not in (required, required | {HD_OUTPUT}):return False
    if with_hd:
        required.add(HD_OUTPUT)
        if HD_OUTPUT not in outputs or not local(HD_OUTPUT).is_file():return False
        if sha(local(HD_OUTPUT)) != outputs[HD_OUTPUT]['sha256']:return False
    return all(local(name).is_file() for name in required)


def prepare(image, jobs=None, *, with_hd=False):
    previous_profile = setup_progress.profile
    setup_progress.profile = None if with_hd else 'base'
    try:
        return prepare_locked(image, jobs, with_hd)
    finally:
        setup_progress.profile = previous_profile


def prepare_locked(image, jobs, with_hd):
    global TIMINGS
    setup_progress.emit('checking');checked=time.monotonic()
    image=Path(image).resolve(strict=True);recipe=plan()
    expected=recipe['original']
    # Validate the complete dump before creating any game output or build lock.
    if image.stat().st_size!=expected['size'] or sha(image)!=expected['sha256']:
        raise ValueError('Requires your unmodified Japanese NPJH50503 disc 1.01 ISO; SHA256 '+expected['sha256'])
    if jobs is None:jobs=setup_resources.compiler_workers()
    if not 1<=jobs<=8:raise ValueError('Use 1-8 compiler workers')
    source_identity.verify(ROOT,'framework');source_identity.verify(ROOT,'decryptor')
    records=recipe['recipes'];work=local('private/local-build');work.mkdir(parents=True,exist_ok=True)
    with preference_lock(work/'player-setup.lock'):
        # Remember the verified ISO even if first setup is interrupted.
        atomic_json(local('private/distribution/local-image.json'),dict(schema=1,path=str(image)))
        if ready(with_hd=with_hd):
            setup_progress.emit('ready',1,1)
            return dict(status='PASS',already_prepared=True,original_unchanged=True)
        TIMINGS=setup_progress.Timings(work/'setup-timings.json',started=checked)
        TIMINGS.record('verify-inputs',time.monotonic()-checked,0)
        if not ready():
            prepare_base(image, jobs, expected, records, work)
            write_ready(work, image, expected, base_outputs(), show_progress=not with_hd)
        if with_hd:
            prepare_hd(records, work)
            write_ready(work, image, expected, (*base_outputs(), HD_OUTPUT))
        atomic_json(work/'setup-progress.json',dict(state='READY',ready_to_play=True))
        setup_progress.emit('ready',1,1)
        return dict(status='PASS',original_unchanged=True,native_available=True,
                    English_available=True,HD_requested=with_hd)


def prepare_base(image, jobs, expected, records, work):
    atomic_json(work/'setup-progress.json',dict(state='BUILDING',ready_to_play=False))
    print('Preparing native Windows executable from your ISO. First setup can take a substantial time; completed stages resume.',flush=True)
    print(f'Using {jobs} compiler workers (CPU and available-memory bounded).',flush=True)
    bridge=local('private/tools/decrypt-build/prx-decrypt.dll')
    setup_progress.emit('inputs')
    input_started=time.monotonic()
    if not bridge.is_file():run('build-prx-helper.py')
    input_report=iso_local_setup.prepare_inputs(image)
    TIMINGS.record('prepare-inputs',time.monotonic()-input_started,0)
    native=title.build_directory('release')
    if (native/'host-ui-build.json').is_file():title.verify_launch_inputs('release')
    else:
        for stage in ('generate','build'):
            setup_progress.emit('generate' if stage=='generate' else 'compile')
            run('title.py',stage,'--profile','release','--jobs',jobs)
        title.verify_launch_inputs('release')
    input_report.update(state='NATIVE_COMPILED',native_compilation_complete=True)
    atomic_json(work/'inputs.json',input_report)
    atomic_json(work/'setup-progress.json',dict(state='PREPARING_ENGLISH',ready_to_play=False))
    rendered=work/'English-rendered'
    setup_progress.emit('text')
    run('build-local-text-images.py','--image',image,'--recipes',local(records['textures']['path']),
        '--output',rendered,'--allow-local-rasterization',*(['--resume'] if rendered.exists() else []))
    if json.loads((rendered/'result.json').read_text()).get('ISO_only_texture_generation_complete') is not True:
        raise RuntimeError('English UI reconstruction is incomplete; no playable installation admitted')
    english=local('private/translation/text-pass-16-image');report=english/'result.json';english_image=english/'LordOfApocalypse-English-WIP.iso'
    setup_progress.emit('archives')
    if not report.is_file():
        if english.exists():
            owner=json.loads((english/'owner.json').read_text())
            expected_owner=dict(tool='build-iso-english-v1',source_ISO_sha256=expected['sha256'],
                message_recipe_sha256=records['messages']['sha256'],render_recipe_sha256=sha(rendered/'result.json'),image_name=english_image.name)
            if owner!=expected_owner or any(p.name not in ('owner.json','REGFILE.RZL','REGFILE.RZP',english_image.name) or p.is_symlink() or not p.is_file() for p in english.iterdir()):
                raise RuntimeError('Interrupted English output is not owned by this build; existing files preserved')
            # Explicit owned stage files only, never a recursive deletion.
            for path in english.iterdir():path.unlink()
            english.rmdir()
        run('build-iso-english.py','--image',image,'--messages',local(records['messages']['path']),
            '--textures',rendered/'result.json','--output',english,'--image-name',english_image.name)
    translation_candidate.verify(english_image,report)
    atomic_json(work/'setup-progress.json',dict(state='PREPARING_CAPTIONS',ready_to_play=False))
    captions=local('private/translation/movie-captions')
    setup_progress.emit('captions')
    if not local('private/local-build/movie-helper/movie-survey.exe').is_file():run('build-movie-helper.py')
    run('build-local-movie-captions.py','--image',image,'--recipe',local(records['captions']['path']),
        '--output',captions,'--allow-local-rasterization',*(['--resume'] if captions.exists() else []))
    run('validate-movie-captions.py',captions/'captions.bin','--output',work/'caption-writer-check')
    caption_report=json.loads((captions/'result.json').read_text());caption_report['approved_for_launch']=True
    atomic_json(captions/'result.json',caption_report)


def prepare_hd(records, work):
    rendered = work/'English-rendered'
    english = local('private/translation/text-pass-16-image')
    atomic_json(work/'setup-progress.json',dict(state='PREPARING_HD',ready_to_play=True))
    import upscaler_dependency
    setup_progress.emit('tools')
    tools_started=time.monotonic()
    upscaler_dependency.ensure()
    TIMINGS.record('prepare-texture-tools',time.monotonic()-tools_started,0)
    hd_recipe=local(records['HD']['path'])
    if json.loads((rendered/'result.json').read_text()).get('platform_rasterization_variants'):
        setup_progress.emit('catalog')
        catalog=work/'current-HD-catalog'
        if not (catalog/'result.json').is_file():run('catalog-remaster-textures.py','--archives',english,'--output',catalog,'--decode')
        rebased=work/'local-HD-recipes-v2.json'
        run('rebase-local-hd-recipes.py','--recipes',hd_recipe,'--catalog',catalog,'--rendered',rendered/'result.json','--output',rebased)
        hd_recipe=rebased
    import hd_recipe_migration
    migration=hd_recipe_migration.migrate(ROOT,hd_recipe)
    if migration:print(json.dumps(migration,indent=2),flush=True)
    setup_progress.emit('hd')
    run('build-local-hd-pack.py','--archives',english,'--recipes',hd_recipe)
    hd_report=json.loads((work/'HD-work/result.json').read_text())
    if hd_report.get('state')!='HD_GENERATED':raise RuntimeError('HD generation has not completed')


def write_ready(work, image, expected, outputs, *, show_progress=True):
    validation_started = time.monotonic()
    if show_progress:setup_progress.emit('verify')
    if sha(image) != expected['sha256']:raise ValueError('Original ISO changed during setup')
    result = dict(state='READY', release_manifest_sha256=sha(local('private/distribution/release.json')),
                  outputs=[dict(path=name, sha256=sha(local(name))) for name in outputs],
                  game_data_bundled=False, original_unchanged=True, full_campaign_validation=False)
    atomic_json(work/'ready.json', result)
    TIMINGS.record('final-validation',time.monotonic()-validation_started,0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',type=Path,required=True);p.add_argument('--jobs',type=int,choices=range(1,9),help='Override automatic CPU/RAM bounded compiler workers')
    p.add_argument('--with-hd', action='store_true', help='Also build the optional local HD texture pack')
    a=p.parse_args()
    print(json.dumps(prepare(a.image,a.jobs,with_hd=a.with_hd),indent=2),flush=True)


if __name__=='__main__':main()
