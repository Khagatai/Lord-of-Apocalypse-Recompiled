"""First-run, ISO-only native compilation and English/HD generation.

All game-derived output is created privately on the player's PC. A failed or
partial stage is never reported ready, and successful owned stages can resume.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,source_identity,translation_candidate
import setup_progress
import setup_resources
from graphics_settings import preference_lock,read_preferences
TIMINGS=None
BUILD_OPTIONS=setup_resources.DEFAULTS


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def local(name):
    path=ROOT/name
    if not path.is_relative_to(ROOT/'private') or path.resolve()!=path:
        raise ValueError('Player build path escapes private storage')
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
        cap = BUILD_OPTIONS['memory_gib']
        with setup_resources.run_stage(ROOT/'tools'/script,args,cap*setup_resources.GIB,env=env,cwd=ROOT,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1) as (process,job):
            last_sample=started
            with process.stdout:
                for line in process.stdout:
                    print(line,end='',flush=True)
                    if script=='build-local-hd-pack.py':
                        count=re.fullmatch(r'Preparing HD textures: (\d+) / (\d+) jobs complete\s*',line)
                        if count:
                            setup_progress.emit('hd',int(count[1]),int(count[2]))
                            if int(count[1])==int(count[2]):setup_progress.emit('verify')
                    if job and time.monotonic()-last_sample>=2:
                        peak=job.peak()
                        if peak:print(f'LOA_SETUP_MEMORY {peak//setup_resources.MIB} {cap*1024}',flush=True)
                        last_sample=time.monotonic()
            code=process.wait()
            peak=job.peak() if job else None
            if peak:
                print(f'LOA_SETUP_MEMORY {peak//setup_resources.MIB} {cap*1024}',flush=True)
                if cap and peak>cap*setup_resources.GIB:
                    print(f'{script}: Windows reported an allocation request above the {cap} GiB cap.',flush=True)
                else:
                    print(f'{script} peak committed memory: {peak/setup_resources.MIB:.0f} MiB',flush=True)
        if code:raise subprocess.CalledProcessError(code,script)
    except subprocess.CalledProcessError as error:
        extra=' HD inference details are in private/local-build/HD-work/scratch/inference-*.log.' if script=='build-local-hd-pack.py' else ''
        if BUILD_OPTIONS['memory_gib']:
            extra+=' A build memory cap was active. If the log shows an allocation failure, raise the cap or lower setup concurrency before retrying.'
        raise RuntimeError(f'Local setup stage {script} failed (exit {error.returncode}). Completed stages are kept for retry; see the launcher log.'+extra) from error
    finally:
        if TIMINGS:TIMINGS.record(script+(' '+str(args[0]) if script=='setup_resources.py' and args else ''),time.monotonic()-started,code)


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


def cache_owner(folder, tool):
    if not folder.exists():return {}
    if folder.is_symlink() or folder.is_junction():raise ValueError('Linked setup output: '+str(folder))
    owner = json.loads((folder/'owner.json').read_text())
    if owner.get('tool') != tool:raise ValueError('Existing setup folder is not owned by this builder: '+str(folder))
    return owner


def reset_cache(folder, tool):
    """Remove only owned, obsolete generated output from the named setup stage."""
    folder = Path(folder)
    if not folder.resolve().is_relative_to(ROOT/'private') or folder.resolve()!=folder:
        raise ValueError('Setup cache escapes its expected directory')
    retired = folder.with_name(folder.name+'-obsolete')
    if retired.exists():
        cache_owner(retired, tool)
        shutil.rmtree(retired)
    if cache_owner(folder, tool):
        folder.replace(retired)
        shutil.rmtree(retired)


def setup_cache(work, stage, fingerprint, folder, tool, expected_owner, *, compatible=False):
    stamp = work/f'{stage}-inputs.json'
    if fingerprint is None:return
    previous = json.loads(stamp.read_text()).get('sha256') if stamp.is_file() else None
    owner = cache_owner(folder, tool)
    if ((previous is not None and previous != fingerprint and not compatible)
            or any(owner.get(key) != val for key,val in expected_owner.items() if owner)):
        reset_cache(folder, tool)
    if previous != fingerprint:
        atomic_json(stamp, dict(sha256=fingerprint))


def native_cache_matches(build_manifest, stamp, identity):
    if not build_manifest.is_file():return False
    if identity is None:return True  # Legacy ISO release, before fingerprints.
    previous = json.loads(stamp.read_text()) if stamp.is_file() else {}
    return previous == dict(input_sha256=identity, build_manifest_sha256=sha(build_manifest))


def prepare(image, jobs=None, *, with_hd=False, memory_gib=None, hd_profile=None):
    global BUILD_OPTIONS
    previous_profile = setup_progress.profile
    previous_options = BUILD_OPTIONS
    options = read_preferences(ROOT/'private/settings/graphics.json')[1]
    for key,value in (('compiler_jobs',jobs),('memory_gib',memory_gib),('hd_profile',hd_profile)):
        if value is not None:options[key]=value
    BUILD_OPTIONS=setup_resources.validate(options)
    setup_progress.profile = None if with_hd else 'base'
    try:
        return prepare_locked(image, with_hd)
    finally:
        setup_progress.profile = previous_profile
        BUILD_OPTIONS = previous_options


def prepare_locked(image, with_hd):
    global TIMINGS
    setup_progress.emit('checking');checked=time.monotonic()
    image=Path(image).resolve(strict=True);recipe=plan()
    expected=recipe['original']
    # Validate the complete dump before creating any game output or build lock.
    if image.stat().st_size!=expected['size'] or sha(image)!=expected['sha256']:
        raise ValueError('Requires your unmodified Japanese NPJH50503 disc 1.01 ISO; SHA256 '+expected['sha256'])
    jobs = setup_resources.compiler_workers(requested=BUILD_OPTIONS['compiler_jobs'],memory_gib=BUILD_OPTIONS['memory_gib'])
    source_identity.verify(ROOT,'framework');source_identity.verify(ROOT,'decryptor')
    records=recipe['recipes'];fingerprints=recipe.get('stage_inputs', {})
    work=local('private/local-build');work.mkdir(parents=True,exist_ok=True)
    with preference_lock(work/'player-setup.lock'):
        # Remember the verified ISO even if first setup is interrupted.
        atomic_json(local('private/distribution/local-image.json'),dict(schema=1,path=str(image)))
        if ready(with_hd=with_hd):
            setup_progress.emit('ready',1,1)
            return dict(status='PASS',already_prepared=True,original_unchanged=True)
        TIMINGS=setup_progress.Timings(work/'setup-timings.json',started=checked)
        TIMINGS.record('verify-inputs',time.monotonic()-checked,0)
        cap = BUILD_OPTIONS['memory_gib']
        print(f'Build memory cap: {str(cap)+" GiB" if cap else "Auto (no hard cap)"}.',flush=True)
        if not ready():
            prepare_base(image, jobs, expected, records, work, fingerprints)
            write_ready(work, image, expected, base_outputs(), show_progress=not with_hd)
        if with_hd:
            prepare_hd(records, work, fingerprints)
            write_ready(work, image, expected, (*base_outputs(), HD_OUTPUT))
        atomic_json(work/'setup-progress.json',dict(state='READY',ready_to_play=True))
        setup_progress.emit('ready',1,1)
        return dict(status='PASS',original_unchanged=True,native_available=True,
                    English_available=True,HD_requested=with_hd)


def prepare_base(image, jobs, expected, records, work, fingerprints):
    atomic_json(work/'setup-progress.json',dict(state='BUILDING',ready_to_play=False))
    print('Preparing native Windows executable from your ISO. First setup can take a substantial time; completed stages resume.',flush=True)
    requested = BUILD_OPTIONS['compiler_jobs'] or 'Auto'
    print(f'Using {jobs} compiler jobs (requested {requested}, bounded by CPU and available RAM).',flush=True)
    bridge=local('private/tools/decrypt-build/prx-decrypt.dll')
    setup_progress.emit('inputs')
    if not bridge.is_file():run('build-prx-helper.py')
    run('iso_local_setup.py','--image',image)
    input_report=json.loads((work/'inputs.json').read_text())
    native=title.build_directory('release')
    native_manifest=native/'host-ui-build.json'
    stamp=work/'native-inputs.json'
    identity=fingerprints.get('native')
    if native_cache_matches(native_manifest,stamp,identity):title.verify_launch_inputs('release')
    else:
        force = ['--force'] if native_manifest.is_file() else []
        for stage in ('generate','build'):
            setup_progress.emit('generate' if stage=='generate' else 'compile')
            run('setup_resources.py',stage,'--jobs',jobs,*force)
        title.verify_launch_inputs('release')
        if identity is not None:atomic_json(stamp,dict(input_sha256=identity,build_manifest_sha256=sha(native_manifest)))
    input_report.update(state='NATIVE_COMPILED',native_compilation_complete=True)
    atomic_json(work/'inputs.json',input_report)
    atomic_json(work/'setup-progress.json',dict(state='PREPARING_ENGLISH',ready_to_play=False))
    rendered=work/'English-rendered'
    setup_cache(work,'text',fingerprints.get('text'),rendered,'build-local-text-images-portable-v1',
                {'recipes_sha256':records['textures']['sha256']})
    setup_progress.emit('text')
    run('build-local-text-images.py','--image',image,'--recipes',local(records['textures']['path']),
        '--output',rendered,'--allow-local-rasterization',*(['--resume'] if rendered.exists() else []))
    if json.loads((rendered/'result.json').read_text()).get('ISO_only_texture_generation_complete') is not True:
        raise RuntimeError('English UI reconstruction is incomplete; no playable installation admitted')
    english=local('private/translation/text-pass-16-image');report=english/'result.json';english_image=english/'LordOfApocalypse-English-WIP.iso'
    image_inputs=fingerprints.get('image')
    if image_inputs is not None:
        image_inputs=hashlib.sha256((image_inputs+fingerprints['text']).encode()).hexdigest()
    setup_cache(work,'image',image_inputs,english,'build-iso-english-v1',
                {'message_recipe_sha256':records['messages']['sha256'],'render_recipe_sha256':sha(rendered/'result.json')})
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
    setup_cache(work,'captions',fingerprints.get('captions'),captions,'local-movie-caption-build-v1',
                {'recipe_sha256':records['captions']['sha256']})
    setup_progress.emit('captions')
    if not local('private/local-build/movie-helper/movie-survey.exe').is_file():run('build-movie-helper.py')
    run('build-local-movie-captions.py','--image',image,'--recipe',local(records['captions']['path']),
        '--output',captions,'--allow-local-rasterization',*(['--resume'] if captions.exists() else []))
    run('validate-movie-captions.py',captions/'captions.bin','--output',work/'caption-writer-check')
    caption_report=json.loads((captions/'result.json').read_text());caption_report['approved_for_launch']=True
    atomic_json(captions/'result.json',caption_report)


def prepare_hd(records, work, fingerprints):
    rendered = work/'English-rendered'
    english = local('private/translation/text-pass-16-image')
    archive_sha = sha(english/'REGFILE.RZP')
    index_sha = sha(english/'REGFILE.RZL')
    hd_input = fingerprints.get('HD')
    if hd_input is not None:
        hd_input = hashlib.sha256((hd_input+archive_sha+index_sha).encode()).hexdigest()
    atomic_json(work/'setup-progress.json',dict(state='PREPARING_HD',ready_to_play=True))
    setup_progress.emit('tools')
    run('upscaler_dependency.py')
    hd_recipe=local(records['HD']['path'])
    original_hd=json.loads(hd_recipe.read_text())
    if (json.loads((rendered/'result.json').read_text()).get('platform_rasterization_variants')
            or (original_hd['archive_sha256'],original_hd['index_sha256'])!=(archive_sha,index_sha)):
        setup_progress.emit('catalog')
        # A catalog describes one exact archive pair. Keep it through resume.
        catalog=work/'current-HD-catalog'
        catalog_report=catalog/'result.json'
        if catalog_report.is_file():
            existing=json.loads(catalog_report.read_text())
            if (existing.get('archive_sha256'),existing.get('index_sha256'))!=(archive_sha,index_sha):
                if (catalog.resolve()!=catalog or
                        existing.get('scope')!='archive-identity-candidates-not-full-game-validation'):
                    raise ValueError('Existing HD catalog is not owned by setup')
                shutil.rmtree(catalog)
        if not (catalog/'result.json').is_file():run('catalog-remaster-textures.py','--archives',english,'--output',catalog,'--decode')
        rebased=work/'local-HD-recipes-v2.json'
        run('rebase-local-hd-recipes.py','--recipes',hd_recipe,'--catalog',catalog,'--rendered',rendered/'result.json','--output',rebased)
        hd_recipe=rebased
    recipe=json.loads(hd_recipe.read_text())
    if (recipe.get('archive_sha256'),recipe.get('index_sha256'))!=(archive_sha,index_sha):
        raise ValueError('HD recipe does not describe the current archives; existing texture files preserved')
    # The builder reconciles individual content-addressed jobs under its lock.
    # Never delete a complete HD pack because an archive or release hash changed.
    profile=BUILD_OPTIONS['hd_profile']
    batch,batch_mib,cache_mib,threads=setup_resources.HD_PROFILES[profile]
    print(f'HD processing: {profile}, up to {batch} jobs per batch, GPU workers {threads}.',flush=True)
    setup_progress.emit('hd')
    run('build-local-hd-pack.py','--archives',english,'--recipes',hd_recipe,'--batch-size',batch,
        '--batch-mib',batch_mib,'--cache-mib',cache_mib,'--threads',threads)
    hd_report=json.loads((work/'HD-work/result.json').read_text())
    if hd_report.get('state')!='HD_GENERATED':raise RuntimeError('HD generation has not completed')
    if hd_input is not None:
        for name in ('HD-jobs','HD-pack'):atomic_json(work/(name+'-inputs.json'),dict(sha256=hd_input))


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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',type=Path,required=True)
    p.add_argument('--jobs',type=int,choices=setup_resources.OPTIONS['compiler_jobs'],help='Maximum compiler jobs (0 for Auto)')
    p.add_argument('--memory-gib',type=int,choices=setup_resources.OPTIONS['memory_gib'],help='Windows build memory cap (0 for Auto)')
    p.add_argument('--hd-profile',choices=setup_resources.OPTIONS['hd_profile'])
    p.add_argument('--with-hd', action='store_true', help='Also build the optional local HD texture pack')
    a=p.parse_args()
    print(json.dumps(prepare(a.image,a.jobs,with_hd=a.with_hd,memory_gib=a.memory_gib,hd_profile=a.hd_profile),indent=2),flush=True)


if __name__=='__main__':main()
