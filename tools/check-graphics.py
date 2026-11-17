"""Bounded graphics-profile startup checks; never a gameplay-quality/FPS claim."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import graphics_settings as settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    output.mkdir(parents=True)
    preferences_before = settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None
    profiles = {
        'original': dict(settings.ORIGINAL),
        'balanced': dict(settings.ORIGINAL, render_scale=2, anisotropy=4),
        # HD pack drawing is covered by check-hd-ui.py, not diagnostic-boot.py.
        'quality': dict(settings.DEFAULTS, hd_ui=False, render_scale=4, anisotropy=16, upscale='fsr1',
                        mipmaps=True, full_color=True, supersampling=2),
    }
    results = {}
    image = settings.WIP_FOLDER/'LordOfApocalypse-English-WIP.iso'
    for name, profile in profiles.items():
        path = output/(name+'-settings.json')
        path.write_text(json.dumps({'schema': 1, **profile}, indent=2)+'\n')
        command = [sys.executable, str(ROOT/'tools/diagnostic-boot.py'), str(image), '--language', 'english-v16',
                   '--candidate-report', str(image.parent/'result.json'), '--output', str(output/name),
                   '--save-fixture', str(ROOT/'private/memstick/japanese'), '--profile', 'release',
                   '--gpu-frames', '--frame-window', '300-310', '--deterministic', '--exit-vblank', '500',
                   '--seconds', '30', '--graphics-settings', str(path)]
        run = subprocess.run(command, capture_output=True, text=True, timeout=50)
        (output/(name+'-harness.log')).write_text(run.stdout+run.stderr)
        report_path = output/name/'result.json'
        if not report_path.exists():
            raise RuntimeError(f'{name} did not produce a diagnostic report')
        report = json.loads(report_path.read_text())
        log = (output/name/'native.log').read_text(errors='replace')
        initialization = [line for line in log.splitlines() if any(word in line for word in
                          ('render scale', 'ACE_MODE:', 'FSR 1 upscaling', 'HOST_MIPS: on', 'TWIN: on', 'SSAA: on'))]
        requirements = []
        if profile['render_scale'] > 1:
            requirements.append(f"gegpu: render scale {profile['render_scale']}x")
        if profile['anisotropy']:
            requirements.append(f"ACE_MODE: on (tier=enhanced, af={profile['anisotropy']},")
        if profile['upscale'] == 'fsr1':
            requirements.append('FSR 1 upscaling on')
        if profile['mipmaps']:
            requirements.append('HOST_MIPS: on')
        if profile['full_color']:
            requirements.append('TWIN: on (colour=full')
        if profile['supersampling'] > 1:
            requirements.append('SSAA: on (2x')
        missing = [text for text in requirements if text not in log]
        passed = (run.returncode == 0 and report['returncode'] == 0 and not report['timed_out'] and
                  report['save_fixture_source_unchanged'] and not missing)
        results[name] = {'passed': bool(passed), 'returncode': report['returncode'], 'timed_out': report['timed_out'],
                         'initialization': initialization, 'missing_feature_confirmations': missing,
                         'save_fixture_source_unchanged': report['save_fixture_source_unchanged']}
        print(json.dumps({'profile': name, **results[name]}), flush=True)
    after = settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None
    report = {'scope': 'bounded-graphics-startup', 'gameplay_quality_validated': False,
              'preferences_unchanged': preferences_before == after, 'profiles': results}
    (output/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    if preferences_before != after or not all(result['passed'] for result in results.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
