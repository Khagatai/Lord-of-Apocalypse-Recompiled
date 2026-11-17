"""Launch an experimental native preview with verified inputs and private logs."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title
import save_storage
import graphics_settings
import settings_bridge
import texture_pack
import mip_preview
import sampler_pack
import network_settings
import test_support
import ui_runtime

def verify_native_location(root=ROOT,image=None):
    if sys.platform=='win32' and not str(root).isascii():
        raise ValueError('This native runtime requires an installation path using ASCII characters. '
                         'Move the entire extracted folder to C:\\Games\\LordOfApocalypse-Recomp. '
                         'Your original ISO may remain at its selected location; setup supports Unicode filenames.')
    if sys.platform=='win32' and image is not None and not str(image).isascii():
        raise ValueError('The native runtime requires an ASCII-only game-image path. '
                         'English images prepared by setup work in an ASCII installation folder. '
                         'For direct Japanese play, move your original ISO to an ASCII path and select it again in the launcher.')

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--language", choices=("japanese", "english-v16"), default="japanese")
    parser.add_argument("--candidate-report", type=Path, help="Test a verified text candidate with separate english-text-test saves")
    parser.add_argument("--check", action="store_true", help="Verify preview inputs without opening a window")
    parser.add_argument('--check-cached',action='store_true',help='Use normal launch verification caching without opening a window; --check always hashes all assets')
    parser.add_argument("--profile", choices=("diagnostic", "release"), default="release")
    parser.add_argument("--renderer", choices=("vulkan", "gdi"), default="vulkan")
    parser.add_argument('--variant', choices=(*graphics_settings.OPTIONS['variant'], 'saved'))
    parser.add_argument('--net-profile',type=Path,help='Explicit private experimental co-op profile; defaults to saved network settings')
    parser.add_argument('--texture-pack',type=Path,help='Explicit verified private HD UI sample; does not persist an enhancement preference')
    parser.add_argument('--graphics-preset',choices=('original','balanced','quality'),help='Per-run profile; saved preferences remain unchanged until a menu choice is saved')
    parser.add_argument('--mip-preview',type=Path,help='Registered private mip-renderer build; WIP English only, isolated saves/preferences')
    args = parser.parse_args(argv)
    if args.check and args.check_cached:parser.error('Choose full or cached preflight')
    started=time.perf_counter()
    def progress(message):
        if not args.check:print(message,flush=True,file=sys.stderr)
    progress('Starting Lord of Apocalypse: checking game image and build...')
    graphics = graphics_settings.load()
    network_profile=network_settings.profile_path(args.net_profile or network_settings.SETTINGS)
    network=network_settings.load(network_profile)
    preview_settings=None
    if args.mip_preview:
        preview_settings=mip_preview.private_path(args.mip_preview)/'preview-graphics.json'
        if preview_settings.exists():graphics=graphics_settings.load(preview_settings)
    if args.graphics_preset:
        graphics = graphics_settings.apply_preset(graphics,args.graphics_preset)
    if args.variant == 'saved':
        args.variant = graphics['variant']
    if args.variant:
        variant_parser = argparse.ArgumentParser()
        variant_parser.add_argument('--language')
        variant_parser.add_argument('--image', type=Path)
        variant_parser.add_argument('--candidate-report', type=Path)
        selected = variant_parser.parse_args(graphics_settings.variant_arguments(args.variant))
        args.language, args.image, args.candidate_report = selected.language, selected.image, selected.candidate_report
    if args.language=='english-v16' and not args.candidate_report:
        parser.error('The standalone v1.6 version is retired. Use --variant english-text-test for WIP English, or --variant japanese.')
    args.image = args.image or title.disc_image(args.language)
    revision = title.verify_launch_inputs(args.profile)
    menu_runtime=ui_runtime.verify(ROOT) if args.renderer=='vulkan' else None
    candidate_report_hash = None
    save_namespace = args.language
    if args.candidate_report:
        if args.language != "english-v16":
            parser.error("Text candidates require --language english-v16")
        from translation_candidate import verify
        digest, candidate_report_hash = verify(args.image, args.candidate_report)
        save_namespace = "english-text-test"
    else:
        digest = title.verify_disc_image(args.image, args.language)
    graphics['variant'] = save_namespace
    if args.texture_pack:
        # The explicit sample shortcut must show its actual state in F1. This
        # changes only the per-run profile until the user saves a menu choice.
        graphics['hd_ui'] = True
    pack=None
    graphics_env=graphics_settings.environment(graphics,args.renderer)
    import movie_captions
    graphics_env.update(movie_captions.environment(save_namespace))
    graphics_env.update(network_settings.environment(network,network_profile))
    selected_pack=texture_pack.selected_folder(graphics,args.renderer,save_namespace,args.texture_pack)
    if selected_pack:
        progress('Checking HD textures (new or changed files take longer)...')
        pack=texture_pack.verify_sample(selected_pack,cache_path=None if args.check else ROOT/'private/settings/hd-verification-cache.json')
        texture_pack.enable(graphics_env,selected_pack)
    build = title.build_directory(args.profile)
    executable = build / "lordofapocalypse.exe"
    mip_experiment=None
    memstick=save_storage.memstick_path(ROOT,save_namespace)
    if args.mip_preview:
        if args.renderer!='vulkan' or args.profile!='release' or save_namespace!='english-text-test':
            parser.error('The mip preview requires release/Vulkan/WIP English')
        mip_experiment=mip_preview.verify(args.mip_preview,revision)
        executable=Path(mip_experiment['executable'])
        memstick=ROOT/'private/memstick/hd-remaster-preview'
        graphics_env['LOA_MIP_TEXTURES']='1'
        graphics_env['LOA_MIP_CAPTURE']='0'
    image = build / "lordofapocalypse_image.bin"
    reference = ROOT / "private/oracle-prefix/entry-prefix.trace"
    input_profile = ROOT / "config/controller-camera.json"
    for path in (executable, image, reference, input_profile, title.SDK / "bin/SDL3.dll"):
        if not path.is_file():
            raise FileNotFoundError(f"Preview dependency missing: {path}")
    data = executable.read_bytes()
    if pack and pack.get('sampler_namespace'):
        metadata_path=executable.parent/('build.json' if mip_experiment else 'host-ui-build.json')
        sampler_pack.require_runtime(pack['sampler_namespace'],json.loads(metadata_path.read_text()),hashlib.sha256(data).hexdigest())
    pe = int.from_bytes(data[0x3c:0x40], "little")
    if data[:2] != b"MZ" or data[pe:pe+4] != b"PE\0\0" or int.from_bytes(data[pe+4:pe+6], "little") != 0x8664:
        raise ValueError("Expected the Windows AMD64 native executable")
    record = {"scope": "experimental-interactive-preview", "boot_validated": False,
              "framework_commit": revision, "iso_sha256": digest,
              "executable_sha256": hashlib.sha256(data).hexdigest(),
              "presenter": args.renderer, "gpu_ge": args.renderer == "vulkan", "automatic_input": False,
              "build_profile": args.profile,
              "language": args.language,
              "translation_candidate_report_sha256": candidate_report_hash,
              "translation_status": "draft-requires-in-game-review" if args.candidate_report else "existing-patch" if args.language == "english-v16" else "original",
              "memstick": str(memstick),
              'mip_experiment':mip_experiment,
              "input_profile": str(input_profile),
              "input_profile_sha256": hashlib.sha256(input_profile.read_bytes()).hexdigest(),
              'graphics_settings': graphics,
              'graphics_environment': graphics_env,
              'texture_pack':{key:value for key,value in pack.items() if key!='textures'} if pack else None,
              "warning": "Gameplay, input, audio and save/load are not validated"}
    record['startup_checks_seconds']=round(time.perf_counter()-started,3)
    record['menu_runtime']=menu_runtime
    if args.check or args.check_cached:
        print(json.dumps({"preflight": "PASS", "window_opened": False, **record}, indent=2))
        return 0
    verify_native_location(image=args.image)
    parent = ROOT / "private"
    progress(f'Checks complete in {record["startup_checks_seconds"]:.1f}s. Opening game...')
    output = Path(tempfile.mkdtemp(prefix="preview-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-", dir=parent))
    if mip_experiment:
        mip_preview.seed_saves(save_storage.memstick_path(ROOT,save_namespace),memstick)
    env = title.environment()
    # A person controls this window. Do not inherit headless automation or capture gates.
    for key in ("SR_HEADLESS", "SR_HEADLESS_ACCEPT_PRESENTED_FRAMES", "SR_PADSCRIPT", "SR_PAD",
                "SR_ROUTE", "SR_NOINPUT", "SR_FBDUMP", "SR_FBSNAP", "SR_FBSNAP_WINDOWS",
                "SR_FIRST_FRAME_DUMP", "SR_QUIET", "SR_VIDEOREC_DIR", "SR_DETERMINISTIC_CLOCK",
                "SR_REPLAY", "SR_RECORD", "SR_ACE", "SR_WINDOW_HIDDEN", "SR_EXIT_AT_VBLANK", "SR_PAUSE_SCRIPT"):
        env.pop(key, None)
    env.update({"PSP_ISO": str(args.image.resolve()), "SR_MEMSTICK": str(memstick),
                "NK_INPUT_PROFILE": str(input_profile),
                "SR_MODULE_DIR": str(ROOT / "private/modules"), "SR_REAL_MODULE_START": "1",
                "SR_BOOT_PATH": title.CONFIG["module"]["start_thread"]["argument"],
                "SR_VIDEO": args.renderer, "SR_GPU_GE": "1" if args.renderer == "vulkan" else "0", "SR_PADWIDTH": "0",
                "SR_PERF": "1", "SR_PERF_JSON": str(output / "perf.json")})
    env.update(graphics_env)
    if mip_experiment:
        import runtime_assets
        runtime_assets.configure_fonts(env,build)
    # The language shown by F1 must match this run, including legacy direct shortcuts.
    bridge = settings_bridge.Bridge(output,preview_settings) if mip_experiment else settings_bridge.Bridge(output)
    env.update(bridge.environment(graphics))
    support = test_support.Support(ROOT,output,memstick,graphics)
    # Aggregate measurements only; no PCM recording or verbose MPEG decoder dump.
    env.update(SR_AUDIOSTAT='1',SR_MPEGAV='1',LOA_MOVIE_TIMING='1',LOA_AUDIO_DIAGNOSTICS='1')
    command = [str(executable), "--image", str(image),
               f"{title.CONFIG['module']['base']:08x}", f"{title.CONFIG['module']['entry']:08x}",
               str(reference), "none", "--gui"]
    record["command"] = command
    record["memstick"] = str(memstick)
    record["state"] = "PREPARING"
    result = output / "result.json"
    result.write_text(json.dumps(record, indent=2) + "\n")
    print("Experimental native preview. Gameplay is not validated.", flush=True)
    print(f"Build: {args.profile}; presenter: {args.renderer}; GPU GE: {args.renderer == 'vulkan'}", flush=True)
    print("Arrows: D-pad; Z: Circle; X: Cross; Enter: Start; F1/Escape: pause settings.", flush=True)
    print(f"Private log: {output / 'native.log'}", flush=True)
    print(f"Persistent saves: {memstick}", flush=True)
    if mip_experiment:
        print('Experimental mip renderer: separate preview saves and preferences; normal progress is unchanged.',flush=True)
    import contextlib,online_session
    online=online_session.Session(output,network) if network['mode']=='off' else contextlib.nullcontext({})
    with online as online_env, network_settings.host_session(network,output), save_storage.save_session(memstick), (output / "native.log").open("wb") as log:
        record['save_backup'] = save_storage.snapshot_saves(ROOT,save_namespace,memstick)
        env.update(online_env)
        record["state"] = "RUNNING"
        result.write_text(json.dumps(record, indent=2) + "\n")
        process = subprocess.Popen(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT)
        if os.environ.get('LOA_GUI_LAUNCHER')=='1':
            print('LOA_LAUNCHER_GAME_STARTED',flush=True)
        if args.renderer == 'vulkan' and not graphics['fullscreen']:
            try:
                import window_settings
                record['window_configuration'] = window_settings.apply(process.pid, graphics['window_size'])
            except OSError as error:
                record['window_configuration'] = {'applied': False, 'error': str(error)}
            result.write_text(json.dumps(record, indent=2)+'\n')
        terminated = False
        try:
            while process.poll() is None:
                bridge.poll()
                support.poll()
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
            code = process.returncode
            bridge.poll()
            support.poll()
        except KeyboardInterrupt:
            terminated = True
            process.terminate()
            code = process.wait(timeout=10)
    record.update({"state": "EXITED", "returncode": code, "harness_terminated_child": terminated})
    try:
        support.finish()
    except (OSError,ValueError,RuntimeError) as error:
        record['diagnostic_export_error']=str(error)
        print('Could not finalize diagnostic report: '+str(error),file=sys.stderr)
    result.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Native preview exited with code {code}. Log kept in {output}", flush=True)
    next_variant = bridge.restart_after_exit(code) if not terminated else None
    if next_variant:
        record['restart_variant'] = next_variant
        result.write_text(json.dumps(record, indent=2)+'\n')
        next_arguments=['--variant', next_variant, '--profile', args.profile, '--renderer', args.renderer]
        if args.net_profile:next_arguments.extend(['--net-profile',str(network_profile)])
        if args.mip_preview and next_variant=='english-text-test':
            next_arguments.extend(['--mip-preview',str(args.mip_preview.resolve())])
        restart_graphics=graphics_settings.load(preview_settings) if mip_experiment else graphics_settings.load()
        if args.texture_pack and next_variant=='english-text-test' and restart_graphics['hd_ui']:
            next_arguments.extend(['--texture-pack',str(args.texture_pack.resolve())])
        return next_arguments
    return int(code != 0)

if __name__ == "__main__":
    arguments = None
    while True:
        outcome = main(arguments)
        if isinstance(outcome, list):
            arguments = outcome
        else:
            raise SystemExit(outcome)
