"""Isolated 4x glyph-reconstruction A/B; counters distinguish work from a no-op."""
import argparse
import ctypes
from ctypes import wintypes as w
import hashlib
import json
from pathlib import Path
import re
import subprocess
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import graphics_settings as settings
import title
import save_storage
import window_settings
import runtime_assets


def window_check(folder, image, env, executable=None, frame_window=(990,1000), padscript=None, timeout_seconds=None, save_fixture=None, deterministic=True):
    """A normal window-close preserves the GPU's exit statistics, unlike frame-exit."""
    folder.mkdir()
    fixture = Path(save_fixture).resolve() if save_fixture else ROOT/'private/memstick/japanese'
    if not fixture.is_relative_to(ROOT/'private') or not fixture.is_dir():
        raise ValueError('Save fixture must be an existing private directory')
    before = save_storage.tree_hashes(fixture)
    shutil.copytree(fixture, folder/'memstick', ignore=shutil.ignore_patterns('.preview.lock'))
    env.update(PSP_ISO=str(image), SR_MEMSTICK=str(folder/'memstick'), SR_MODULE_DIR=str(ROOT/'private/modules'),
               SR_REAL_MODULE_START='1', SR_BOOT_PATH=title.CONFIG['module']['start_thread']['argument'],
               SR_VIDEO='vulkan', SR_GPU_GE='1', SR_PADWIDTH='0', SR_DETERMINISTIC_CLOCK='1', SR_NOVBPACE='1',
               SR_FBSNAP='1', SR_FBSNAP_WINDOWS=f'{frame_window[0]}-{frame_window[1]}')
    if not deterministic:
        env.pop('SR_DETERMINISTIC_CLOCK',None)
        env.pop('SR_NOVBPACE',None)
    for key in ('SR_HEADLESS', 'SR_WINDOW_HIDDEN', 'SR_EXIT_AT_VBLANK', 'SR_PADSCRIPT', 'SR_PAD', 'SR_PAUSE_SCRIPT'):
        env.pop(key, None)
    if padscript is not None:
        env['SR_PADSCRIPT']=str(padscript.resolve())
    build = title.build_directory('release')
    # A diagnostic executable in another folder does not inherit the release's
    # sibling font/ directory. Match the real launch instead of probing blanks.
    font_root,font_hashes=runtime_assets.configure_fonts(env,build)
    command = [str(executable or build/'lordofapocalypse.exe'), '--image', str(build/'lordofapocalypse_image.bin'),
               f"{title.CONFIG['module']['base']:08x}", f"{title.CONFIG['module']['entry']:08x}",
               str(ROOT/'private/oracle-prefix/entry-prefix.trace'), 'none', '--sched', '--gui']
    user = ctypes.WinDLL('user32', use_last_error=True)
    visit_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    user.GetWindowThreadProcessId.argtypes = (w.HWND, ctypes.POINTER(w.DWORD))
    user.GetClassNameW.argtypes = (w.HWND, w.LPWSTR, ctypes.c_int)
    user.PostMessageW.argtypes = (w.HWND, w.UINT, w.WPARAM, w.LPARAM)
    user.EnumWindows.argtypes = (visit_type, w.LPARAM)
    windows = []
    report = {'returncode': None, 'timed_out': False, 'save_fixture_source_unchanged': False,
              'save_fixture_root':str(fixture),
              'font_root':str(font_root),'font_files_sha256':font_hashes,
              'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
              'executable_sha256': hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()}
    with (folder/'native.log').open('wb') as log:
        process = subprocess.Popen(command, cwd=folder, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            report['window_size'] = window_settings.apply(process.pid, (1920, 1088))
            @visit_type
            def visit(window, _):
                owner = w.DWORD()
                name = ctypes.create_unicode_buffer(128)
                user.GetWindowThreadProcessId(window, ctypes.byref(owner))
                user.GetClassNameW(window, name, 128)
                if owner.value == process.pid and name.value == 'SDL_app':
                    windows.append(window)
                    return False
                return True
            user.EnumWindows(visit, 0)
            if not windows:
                raise RuntimeError('Owned game window unavailable')
            seconds=timeout_seconds if timeout_seconds is not None else (60 if frame_window[1]>3600 else 30)
            report['checkpoint_timeout_seconds']=seconds
            deadline = time.monotonic()+seconds
            # Present parity can shift by one VBLANK. Require a successful GPU
            # capture in the bounded window, rather than one exact frame number.
            def captured():
                frames=re.findall(r'FBSNAP f=(\d+) swapchain capture .*\(result=1\)',
                                  (folder/'native.log').read_text(errors='replace'))
                return any(frame_window[0]<=int(frame)<=frame_window[1] for frame in frames)
            while not captured():
                if process.poll() is not None:
                    raise RuntimeError('Game exited before the text checkpoint')
                if time.monotonic()>deadline:
                    raise TimeoutError(f'Text checkpoint not reached within {seconds} seconds')
                time.sleep(0.1)
            time.sleep(0.3)
            subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                            '-Window',str(windows[0]),'-Owner',str(process.pid),'-Output',str(folder/'native-4x.png')],
                           capture_output=True, check=True, timeout=10)
            user.PostMessageW(windows[0],0x10,0,0)
            report['returncode'] = process.wait(timeout=10)
        except Exception as error:
            report['error'] = str(error)
            report['timed_out'] = isinstance(error, (TimeoutError, subprocess.TimeoutExpired))
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    report['save_fixture_source_unchanged'] = before == save_storage.tree_hashes(fixture)
    report['font_files_unchanged'] = font_hashes == save_storage.tree_hashes(font_root)
    (folder/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--windowed', action='store_true', help='Capture actual 4x output and close normally to collect GPU counters')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    output.mkdir(parents=True)
    preferences = settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None
    image = settings.WIP_FOLDER/'LordOfApocalypse-English-WIP.iso'
    title.verify_inputs()
    from translation_candidate import verify
    verify(image, image.parent/'result.json')
    results = {}
    for mode in ('off', 'on'):
        env = title.environment()
        env.update(settings.environment(dict(settings.ORIGINAL, render_scale=4, vsync=False)))
        # Same Enhanced baseline in both cells; the glyph key is the only difference.
        env['SR_ACE'] = ('v1;tier=enhanced;af=0;text=off;readout=off;notice=off;wide=off;'
                         'smooth=off;sas=off;tess=off;twin=off;mips=off;ssaa=off;glyphs='+mode)
        env.pop('SR_GLYPHS', None)  # Retired diagnostic alias must not override the key.
        command = [sys.executable, str(ROOT/'tools/diagnostic-boot.py'), str(image),
                   '--language', 'english-v16', '--candidate-report', str(image.parent/'result.json'),
                   '--output', str(output/mode), '--profile', 'release', '--gpu-frames',
                   '--frame-window', '990-1000', '--exit-vblank', '1000', '--deterministic',
                   '--seconds', '30', '--perf', '--save-fixture', str(ROOT/'private/memstick/japanese')]
        if args.windowed:
            report = window_check(output/mode, image, env)
            harness_ok = report['returncode'] == 0 and report.get('window_size', {}).get('applied', False)
        else:
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=45)
            (output/(mode+'-harness.log')).write_text(run.stdout+run.stderr)
            result_path = output/mode/'result.json'
            if not result_path.is_file():
                raise RuntimeError(mode+' produced no diagnostic report')
            report = json.loads(result_path.read_text())
            harness_ok = run.returncode == 0
        log = (output/mode/'native.log').read_text(errors='replace')
        counts = re.search(r'GLYPHS: draws \(bound=(\d+), tiles_built=(\d+)', log)
        captures = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted((output/mode).glob('*.ppm'))}
        passed = (harness_ok and report['returncode'] == 0 and not report['timed_out'] and
                  report['save_fixture_source_unchanged'] and 'ACE_MODE: refused' not in log)
        if mode == 'on':
            passed = passed and 'GLYPHS: on (' in log
        results[mode] = {'startup_passed': bool(passed), 'returncode': report['returncode'],
                         'timed_out': report['timed_out'],
                         'source_saves_unchanged': report['save_fixture_source_unchanged'],
                         'counter_reported': counts is not None,
                         'bound_draws': int(counts[1]) if counts else None,
                         'tiles_built': int(counts[2]) if counts else None,
                         'glyph_log': [line for line in log.splitlines() if 'GLYPHS:' in line or 'ACE_MODE: glyphs' in line],
                         'captures_sha256': captures,
                         'executable_sha256': report['executable_sha256'],
                         'iso_sha256': report['image_sha256']}
        print(json.dumps({'mode': mode, **results[mode]}), flush=True)
    unchanged = preferences == (settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None)
    common = sorted(results['off']['captures_sha256'].keys() & results['on']['captures_sha256'].keys())
    report = {'scope': '4x-save-loaded-prompt-glyph-ab', 'preferences_unchanged': unchanged,
              'visual_improvement_validated': False, 'gameplay_fps_validated': False,
              'feature_used': results['on']['bound_draws'] > 0 if results['on']['counter_reported'] else None,
              'runs': results, 'guest_captures_identical': results['off']['captures_sha256'] == results['on']['captures_sha256'],
              'common_capture_count': len(common),
              'common_captures_identical': bool(common) and all(results['off']['captures_sha256'][name] == results['on']['captures_sha256'][name]
                                                               for name in common),
              'window_capture_note': 'PrintWindow can return blank Vulkan pixels; inspect both PNGs before a visual verdict.'}
    (output/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'runs'}, indent=2))
    return 0 if unchanged and all(row['startup_passed'] for row in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
