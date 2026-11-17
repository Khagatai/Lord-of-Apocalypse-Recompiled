"""Bounded strict scheduler investigation; incomplete boot state means no acceptance pass."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title
import save_storage
import graphics_settings

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--language", choices=("japanese", "english-v16"), default="japanese")
    parser.add_argument("--candidate-report", type=Path, help="Explicit private translation-image build report; diagnostics only")
    parser.add_argument("--output", type=Path, default=ROOT / "private/diagnostic-boot")
    parser.add_argument("--io-log", action="store_true", help="Record local file-I/O diagnostics")
    parser.add_argument("--seconds", type=int, choices=range(1, 181), default=5)
    parser.add_argument("--offscreen-frames", action="store_true",
                        help="Capture CPU-presenter diagnostic frames privately; no window or frame acceptance claim")
    parser.add_argument("--gpu-frames", action="store_true", help="Use a hidden Vulkan GPU presenter for diagnostic captures")
    parser.add_argument("--frame-window", default="1-300", help="Bounded VBLANK snapshot range, e.g. 300-1800")
    parser.add_argument("--pad-script", type=Path, help="Explicit input script; automatic pulses stay disabled")
    parser.add_argument("--profile", choices=("diagnostic", "release"), default="diagnostic")
    parser.add_argument("--perf", action="store_true", help="Record performance counters in the private run folder")
    parser.add_argument("--deterministic", action="store_true")
    parser.add_argument("--exit-vblank", type=int, choices=range(1, 9001))
    parser.add_argument("--save-fixture", type=Path, help="Copy a saved memstick into the isolated diagnostic; never write the source")
    parser.add_argument('--graphics-settings', type=Path, help='Explicit graphics profile for this isolated diagnostic; never persists preferences')
    args = parser.parse_args()
    if args.offscreen_frames and args.gpu_frames:
        parser.error("Choose CPU offscreen or GPU frames")
    capture_frames = args.offscreen_frames or args.gpu_frames
    try:
        low, high = map(int, args.frame_window.split("-"))
    except ValueError:
        parser.error("Frame window must be LOW-HIGH")
    if not 0 <= low <= high <= 9000:
        parser.error("Frame window must stay between VBLANK 0 and 9000")
    revision = title.verify_inputs()
    candidate_report_hash = None
    if args.candidate_report:
        if args.language != "english-v16":
            parser.error("Translation candidates require --language english-v16")
        from translation_candidate import verify
        digest, candidate_report_hash = verify(args.image, args.candidate_report)
    else:
        digest = title.verify_disc_image(args.image, args.language)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private"):
        parser.error("Diagnostic outputs must stay under private/")
    if output.exists():
        raise ValueError("Archive prior private/diagnostic-boot evidence before repeating")
    output.mkdir()
    memstick = output / "memstick"
    fixture_hashes = save_storage.tree_hashes(args.save_fixture) if args.save_fixture else None
    if args.save_fixture:
        shutil.copytree(args.save_fixture, memstick)
    else:
        memstick.mkdir()
    env = title.environment()
    graphics = None
    if args.graphics_settings:
        if not args.graphics_settings.is_file():
            raise FileNotFoundError('Requested graphics profile does not exist')
        graphics = graphics_settings.load(args.graphics_settings)
        env.update(graphics_settings.environment(graphics))
    env.update({"PSP_ISO": str(args.image.resolve()), "SR_MEMSTICK": str(memstick),
                "SR_MODULE_DIR": str(ROOT / "private/modules"),
                "SR_PADWIDTH": "0",
                # Request genuine guest linking, including a library with no start entry.
                # This does not invent an entry or synthesize module readiness.
                "SR_REAL_MODULE_START": "1",
                "SR_BOOT_PATH": title.CONFIG["module"]["start_thread"]["argument"], "SR_HEADLESS": "1"})
    if args.io_log:
        env["SR_IOLOG"] = "1"
    env.pop("SR_PADSCRIPT", None)
    if args.pad_script:
        env["SR_PADSCRIPT"] = str(args.pad_script.resolve(strict=True))
        env["SR_INLOG"] = "1"
    if capture_frames:
        env.update({"SR_VIDEO": "vulkan" if args.gpu_frames else "offscreen", "SR_FIRST_FRAME_DUMP": "1",
                    "SR_FBSNAP": "30", "SR_FBSNAP_WINDOWS": f"{low}-{high}"})
    if args.gpu_frames:
        env.update({"SR_WINDOW_HIDDEN": "1", "SR_GPU_GE": "1"})
    if args.perf:
        env.update({"SR_PERF": "1", "SR_PERF_JSON": str(output / "perf.json"),
                    "SR_PERF_FRAMES": str(output / "frames.csv")})
    if args.deterministic:
        env.update({"SR_DETERMINISTIC_CLOCK": "1", "SR_NOVBPACE": "1"})
    if args.exit_vblank:
        env["SR_EXIT_AT_VBLANK"] = str(args.exit_vblank)
    build = title.build_directory(args.profile)
    command = [str(build / "lordofapocalypse.exe"), "--image",
               str(build / "lordofapocalypse_image.bin"), "08804000", "08be596c",
               str(ROOT / "private/oracle-prefix/entry-prefix.trace"), "none", "--sched"]
    if capture_frames:
        command.append("--gui")
    caption_path = Path(env['LOA_MOVIE_CAPTIONS']).resolve(strict=True) if env.get('LOA_MOVIE_CAPTIONS') else None
    caption_hash = hashlib.sha256(caption_path.read_bytes()).hexdigest() if caption_path else None
    timeout = False
    with (output / "native.log").open("wb") as log:
        # Built-in capture paths are relative. Keep all pixels and raw VRAM in private/.
        working_directory = output if capture_frames else title.FRAMEWORK
        process = subprocess.Popen(command, cwd=working_directory, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timeout = True
            process.terminate()
            code = process.wait(timeout=10)
    report = {"mode": "strict-scheduler-diagnostic", "returncode": code, "timeout_seconds": args.seconds,
              "timed_out": timeout, "boot_acceptance": "NOT_VALIDATED",
              "framework_commit": revision, "command": command,
              "executable_sha256": hashlib.sha256(Path(command[0]).read_bytes()).hexdigest(),
              "image_sha256": digest, "guest_module_start_policy": "1",
              "io_logging": args.io_log,
              "offscreen_frame_diagnostics": args.offscreen_frames,
              "gpu_frame_diagnostics": args.gpu_frames,
              "build_profile": args.profile, "performance_recording": args.perf,
              "language": args.language,
              'graphics_settings': graphics,
              'graphics_settings_sha256': hashlib.sha256(args.graphics_settings.read_bytes()).hexdigest() if args.graphics_settings else None,
              "translation_candidate_report_sha256": candidate_report_hash,
              "movie_caption_bundle_sha256": caption_hash,
              "movie_caption_bundle_unchanged": hashlib.sha256(caption_path.read_bytes()).hexdigest() == caption_hash if caption_path else None,
              "deterministic_clock": args.deterministic, "diagnostic_exit_vblank": args.exit_vblank,
              "frame_window": f"{low}-{high}" if capture_frames else None,
              "automatic_input": False,
              "save_fixture_files_sha256": fixture_hashes,
              "save_fixture_source_unchanged": save_storage.tree_hashes(args.save_fixture) == fixture_hashes if args.save_fixture else None,
              "pad_script_sha256": hashlib.sha256(args.pad_script.read_bytes()).hexdigest() if args.pad_script else None,
              "missing_contract": ["root-attributes", "next-uid", "initial-ge-counter", "complete-memory-writes"]}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
