"""Identity-pinned Nakagawa generation/build entry points for the local title."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
CONFIG = tomllib.loads((ROOT / "config/lordofapocalypse.toml").read_text())
FRAMEWORK = ROOT / CONFIG["runtime"]["path"]
BUILD = ROOT / "private/native-build/lordofapocalypse"
SDK = ROOT / "private/toolchain/prerequisites/msys64/ucrt64"
PYTHON = ROOT / "private/tools/python314/python.exe"

def verify_inputs():
    if not shutil.which('git'):
        raise FileNotFoundError('Git is required for development/build checks. Use LordOfApocalypse.exe to play an existing release build.')
    revision = subprocess.check_output(["git", "-c", f"safe.directory={FRAMEWORK.as_posix()}",
                                       "-C", str(FRAMEWORK), "rev-parse", "HEAD"], text=True).strip()
    if revision != CONFIG["runtime"]["commit"]:
        raise ValueError("Active framework pin mismatch")
    verify_title_inputs()
    return revision


def verify_title_inputs():
    """Check measured title inputs independently of developer Git metadata."""
    adapter = ROOT / CONFIG["runtime"]["codegen_adapter"]
    if hashlib.sha256(adapter.read_bytes()).hexdigest() != CONFIG["runtime"]["codegen_adapter_sha256"]:
        raise ValueError("Codegen adapter identity mismatch")
    if hashlib.sha256((ROOT/'tools/frame_rate_codegen.py').read_bytes()).hexdigest()!=CONFIG['runtime']['timing_codegen_sha256']:
        raise ValueError('Timing codegen identity mismatch')
    for module in (CONFIG["module"], CONFIG["dynamic_modules"]["libfont"]):
        path = ROOT / module["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != module["sha256"]:
            raise ValueError(f"Module hash mismatch: {path.name}")
    manifest = json.loads((ROOT / "config/lordofapocalypse.json").read_text())
    for name in ("base", "entry"):
        if manifest["executable"][name] != CONFIG["module"][name]:
            raise ValueError(f"Measured {name} differs between configs")


def verify_launch_inputs(profile='release'):
    """Verify an existing release using its build manifest, without invoking Git.

    This checks local artifact integrity, not the authenticity of a download.
    Generation and builds continue to require the exact framework checkout.
    """
    if profile != 'release':
        return verify_inputs()
    verify_title_inputs()
    folder=build_directory(profile)
    record=folder/'host-ui-build.json'
    if not record.is_file():
        raise FileNotFoundError('Release build manifest missing: copy host-ui-build.json together with the matching executable and image.')
    metadata=json.loads(record.read_text())
    revision=metadata.get('framework_commit')
    if revision != CONFIG['runtime']['commit']:
        raise ValueError('Release build framework pin mismatch')
    for name,key in (('lordofapocalypse.exe','executable_sha256'),
                     ('lordofapocalypse_image.bin','flat_image_sha256')):
        path=folder/name
        if not path.is_file():
            raise FileNotFoundError(f'Release runtime file missing: {path}')
        with path.open('rb') as stream:
            observed=hashlib.file_digest(stream,'sha256').hexdigest()
        if observed != metadata.get(key):
            raise ValueError(f'Release build hash mismatch: {name}. Copy the executable, image and host-ui-build.json from the same build.')
    return revision

def environment():
    result = dict(os.environ)
    result["PATH"] = os.pathsep.join([str(SDK / "bin"), str(PYTHON.parent), result["PATH"]])
    result["VULKAN_SDK"] = str(SDK)
    result["SDL3_DIR"] = str(SDK)
    # The runtime otherwise resolves these relative to the caller's directory.
    # Keep data validation active while allowing private capture working folders.
    result["PSP_VFPU_TABLES"] = str(FRAMEWORK / "assets/vfpu")
    # Keep every temporary compiler/analysis artifact in the private workspace.
    temporary = ROOT / "private/tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    result["TMP"] = result["TEMP"] = str(temporary)
    return result

def disc_image(language="japanese"):
    if language == 'japanese':
        local = ROOT/'private/distribution/local-image.json'
        if local.is_file():
            record=json.loads(local.read_text(encoding='utf-8'))
            if set(record)!={'schema','path'} or record['schema']!=1 or not isinstance(record['path'],str):
                raise ValueError('Invalid local tester image configuration')
            path=Path(record['path'])
            if not path.is_absolute():raise ValueError('Tester game image path must be absolute')
            return path
    if language=='english-v16':
        from translation_baseline import prepare_image
        return prepare_image()
    return ROOT.parent / "Lord of Apocalypse (Japan).iso"

def verify_disc_image(path, language="japanese"):
    expected = CONFIG["translations"]["english_v16"] if language == "english-v16" else {
        "size": CONFIG["disc"]["iso_size"], "sha256": CONFIG["disc"]["iso_sha256"]}
    if path.stat().st_size != expected["size"]:
        raise ValueError("Disc image size differs from the selected language identity")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected["sha256"]:
        raise ValueError("Disc image hash differs from the selected language identity")
    return digest

def build_directory(profile="diagnostic"):
    return ROOT / ("private/native-release/lordofapocalypse" if profile == "release" else "private/native-build/lordofapocalypse")

def make_arguments(profile="diagnostic"):
    release = profile == "release"
    output_root = "native-release" if release else "native-build"
    return [
        f"PYTHON={PYTHON.as_posix()}", "GAME_NAME=lordofapocalypse",
        "GAME_ELF=../../private/modules/EBOOT.elf",
        "GAME_PSP_HEADER=../../private/disc/PSP_GAME/SYSDIR/EBOOT.BIN",
        f"GAME_BASE={hex(CONFIG['module']['base'])}", f"GAME_ENTRY={hex(CONFIG['module']['entry'])}",
        "GAME_EXTRA_ELFS=../../private/modules/LIBFONT.elf@runtime",
        "TITLE_MANIFEST=../../config/lordofapocalypse.json",
        f"BUILD_ROOT=../../private/{output_root}", f"BUILD_DIR=../../private/{output_root}/lordofapocalypse",
        "CODEGEN_PROFILE_ARG=--profile=none", "FUNCS_PER_CHUNK=500", "CHUNK_TARGET_BYTES=2000000",
        "CODEGEN_TOOL=../../tools/import_trace_codegen.py",
        "PUBLIC_SAFE=1", f"TRACE={0 if release else 1}",
        f"RUNTIME_OPT={'-O2' if release else '-O1'}", f"RECOMP_OPT={'-O2' if release else '-O0'}",
    ]

def build(stage, jobs, profile="diagnostic"):
    verify_inputs()
    env = environment()
    make = SDK / "bin/mingw32-make.exe"
    if not make.is_file() or not PYTHON.is_file():
        raise FileNotFoundError("Local pinned compiler/Make/Python setup is incomplete")
    destination = build_directory(profile)
    destination.mkdir(parents=True, exist_ok=True)
    renderer=None
    media=None
    extra_make=[]
    if profile=='release':
        import mip_runtime_patch
        renderer_root=destination/'hd-renderer';renderer_root.mkdir(exist_ok=True)
        renderer=mip_runtime_patch.prepare(FRAMEWORK,renderer_root/'ge_gpu.c')
        extra_make=['-f','../../tools/renderer-enhancements.mk']
        import media_runtime_patch
        media_root=destination/'media-runtime';media_root.mkdir(exist_ok=True)
        media=media_runtime_patch.prepare(FRAMEWORK,media_root/'mpeg.c')
        media['audio']=media_runtime_patch.prepare_audio(FRAMEWORK,media_root/'hle_audio.c')
        extra_make+=['-f','../../tools/media-runtime.mk','-f','../../tools/coop-runtime.mk']
        if stage=='build' and (destination/'lordofapocalypse.exe').exists():
            backup_root=ROOT/'private/release-backups';backup_root.mkdir(exist_ok=True)
            previous=destination/'lordofapocalypse.exe'
            previous_hash=hashlib.sha256(previous.read_bytes()).hexdigest()
            backup=backup_root/(previous_hash+'.exe')
            # Keep the initial recovery executable, not a full copy per edit.
            if not any(backup_root.glob('*.exe')):shutil.copy2(previous,backup)
    flat=destination/'lordofapocalypse_image.bin'
    flat_before=hashlib.sha256(flat.read_bytes()).hexdigest() if flat.exists() else None
    # Codegen rewrites every chunk. Preserve timestamps for byte-identical output
    # so a small title seam change does not recompile all unrelated functions.
    stamps={p:(hashlib.sha256(p.read_bytes()).digest(),p.stat().st_atime_ns,p.stat().st_mtime_ns)
            for p in destination.glob('lordofapocalypse_recomp*')
            if stage=='generate' and p.suffix in ('.c','.h')}
    command = [str(make), '-f', 'Makefile', '-f', '../../tools/overlay-settings.mk', '-f', '../../tools/gameplay-fps.mk', *extra_make,
               *make_arguments(profile), f"-j{jobs}", "pipeline" if stage == "generate" else "compile"]
    log_path = destination / (stage + ".log")
    print(f"{stage}: running pinned framework; log: {log_path}", flush=True)
    with log_path.open("w") as log:
        run = subprocess.run(command, cwd=FRAMEWORK, env=env, stdout=log, stderr=subprocess.STDOUT)
    if run.returncode:
        print("\n".join(log_path.read_text(errors="replace").splitlines()[-12:]), file=sys.stderr)
        raise SystemExit(run.returncode)
    if stage == "generate":
        for path,(digest,access,modified) in stamps.items():
            if path.exists() and hashlib.sha256(path.read_bytes()).digest()==digest:
                os.utime(path,ns=(access,modified))
        stub_path = destination / "lordofapocalypse_recomp_stubs.txt"
        if not stub_path.is_file() or stub_path.read_text().strip():
            raise RuntimeError("Generation has trapping fallbacks; review the protected stub report")
        print("Generation finished with an empty fallback report. Execution is not yet validated.")
    else:
        executable = destination / "lordofapocalypse.exe"
        data = executable.read_bytes()
        pe = int.from_bytes(data[0x3c:0x40], "little")
        if data[pe:pe + 4] != b"PE\0\0" or int.from_bytes(data[pe + 4:pe + 6], "little") != 0x8664:
            raise RuntimeError("Expected an AMD64 Windows PE")
        dll = SDK / "bin/SDL3.dll"
        if dll.is_file():
            shutil.copy2(dll, destination / dll.name)
        extension = {name: hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest()
                     for name in ('in-game-settings.c', 'title_settings_menu.h', 'overlay-settings.mk', 'gameplay_fps.c', 'gameplay-fps.mk', 'frame_rate_codegen.py',
                                  'coop-runtime.mk','coop_hle.c','coop_service_wait.h','coop_transport.c','coop_transport.h','online_runtime.c','online_runtime.h',
                                  'movie_subtitles.c','movie_caption_format.h','media-runtime.mk','audio_diagnostics.h')}
        (destination/'host-ui-build.json').write_text(json.dumps({
            'framework_commit': CONFIG['runtime']['commit'], 'host_extension_sha256': extension,
            'executable_sha256': hashlib.sha256(data).hexdigest(),
            'scope': 'title-owned-overlay-renderer-and-optional-timing' if renderer else 'title-owned-overlay-and-optional-timing',
            'renderer':renderer, 'media_runtime':media, 'guest_code_modified': 'conditional-60fps-timing', 'guest_image_modified': False,
            'flat_image_sha256':hashlib.sha256(flat.read_bytes()).hexdigest()}, indent=2)+'\n')
        if flat_before and hashlib.sha256(flat.read_bytes()).hexdigest()!=flat_before:
            raise RuntimeError('Unexpected guest image change during host-only build')
        print("Built Windows x64 PE; no runtime milestone is implied.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("generate", "build"))
    parser.add_argument("--jobs", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--profile", choices=("diagnostic", "release"), default="diagnostic")
    args = parser.parse_args()
    build(args.stage, args.jobs, args.profile)

if __name__ == "__main__":
    main()
