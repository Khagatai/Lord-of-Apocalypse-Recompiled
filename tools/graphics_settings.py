"""Validated, persistent graphics choices shared by the title's Windows launchers."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import contextlib
import hashlib

def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).exists() else 'missing'

@contextlib.contextmanager
def preference_lock(path):
    """Serialize Windows launcher/F1 writes to the same preference file."""
    if os.name!='nt':
        yield;return
    import ctypes
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=(ctypes.c_void_p,w.BOOL,w.LPCWSTR);kernel.CreateMutexW.restype=w.HANDLE
    kernel.WaitForSingleObject.argtypes=(w.HANDLE,w.DWORD);kernel.ReleaseMutex.argtypes=(w.HANDLE,);kernel.CloseHandle.argtypes=(w.HANDLE,)
    identity=hashlib.sha256(str(Path(path).resolve()).casefold().encode('utf-8')).hexdigest()
    handle=kernel.CreateMutexW(None,False,'Local\\LOA-settings-'+identity)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    acquired=False
    try:
        result=kernel.WaitForSingleObject(handle,5000)
        if result not in (0,0x80):raise OSError('Settings are busy. Please try again.')
        acquired=True;yield
    finally:
        if acquired:kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / 'private/settings/graphics.json'
WIP_FOLDER = ROOT / 'private/translation/text-pass-16-image'
# This ordered contract also drives the native menu's combo-box selections.
OPTIONS = {
    'variant': ('english-text-test', 'japanese'),
    'render_scale': (1, 2, 3, 4),
    'fullscreen': (False, True),
    'window_size': ((960, 544), (1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160)),
    'scaling': ('sharp', 'integer', 'bilinear'),
    'vsync': (False, True),
    'hud': (False, True),
    'upscale': ('off', 'fsr1'),
    'anisotropy': (0, 2, 4, 8, 16),
    'mipmaps': (False, True),
    'full_color': (False, True),
    'supersampling': (1, 2),
    'texture_scale': (1, 2, 3, 4, 5, 6),
    'hd_ui': (False, True),
    'gameplay_fps': (30, 60),
}
ORIGINAL = {key: values[0] for key, values in OPTIONS.items()}
ORIGINAL['vsync'] = True
QUALITY = dict(render_scale=4, upscale='fsr1', anisotropy=16, mipmaps=True,
               full_color=True, supersampling=2, texture_scale=4, hd_ui=True)
DEFAULTS = dict(ORIGINAL, **QUALITY)


def apply_preset(value, name):
    """Create an isolated run profile; Original also restores a small window."""
    value = validate({'schema': 1, **value})
    if name == 'quality':
        return dict(value, **QUALITY)
    if name not in ('original', 'balanced'):
        raise ValueError('Unknown graphics preset')
    result = dict(ORIGINAL)
    preserved = ('variant', 'fullscreen', 'window_size', 'hud', 'gameplay_fps') if name == 'balanced' else ('variant',)
    for key in preserved:
        result[key] = value[key]
    if name == 'balanced':
        result.update(render_scale=2, anisotropy=4)
    return result


def validate(value):
    if not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 1 or set(value) != {'schema', *OPTIONS}:
        raise ValueError('Unrecognized graphics settings format')
    result = {}
    for key, choices in OPTIONS.items():
        entry = value[key]
        if key == 'window_size' and isinstance(entry, list):
            entry = tuple(entry)
        if key == 'window_size' and (not isinstance(entry, tuple) or any(type(part) is not int for part in entry)):
            raise ValueError('Unsupported graphics setting: window_size')
        if entry not in choices or type(entry) is not type(choices[0]):
            raise ValueError(f'Unsupported graphics setting: {key}')
        result[key] = entry
    return result


def load(path=SETTINGS):
    if not path.exists():
        return dict(DEFAULTS)
    value = json.loads(path.read_text(encoding='utf-8'))
    # Exact legacy schema only: retain every saved choice and default the new
    # opt-in effect to off. Do not conceal malformed or unknown preferences.
    if isinstance(value, dict) and value.get('schema') == 1:
        if value.get('variant')=='english-v16':value['variant']='english-text-test'
        missing = set(OPTIONS)-set(value)
        legacy_missing=missing-{'gameplay_fps'}
        if missing and legacy_missing in (set(), {'texture_scale', 'hd_ui'}, {'hd_ui'}) and set(value) == {'schema', *(set(OPTIONS)-missing)}:
            for key in missing:
                value[key] = ORIGINAL[key]
    return validate(value)


def save(value, path=SETTINGS, *, expected=None):
    with preference_lock(path):
        if expected is not None and fingerprint(path)!=expected:
            raise ValueError('Settings changed elsewhere. Reopen settings to load the latest choices.')
        _save(value,path)

def _save(value, path):
    checked = validate({'schema': 1, **value})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False, suffix='.tmp') as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps({'schema': 1, **checked}, indent=2)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def menu_codes(value):
    return [choices.index(value[key]) for key, choices in OPTIONS.items()]


def from_menu(codes):
    if len(codes) != len(OPTIONS):
        raise ValueError('Graphics menu contract differs')
    result = {}
    for code, (key, choices) in zip(codes, OPTIONS.items()):
        if not 0 <= code < len(choices):
            raise ValueError(f'Invalid menu choice: {key}')
        result[key] = choices[code]
    return result


def environment(value, renderer='vulkan'):
    """Explicitly overwrite diagnostic overrides so saved choices are effective."""
    value = validate({'schema': 1, **value})
    enhanced = any((value['anisotropy'], value['mipmaps'], value['full_color'], value['supersampling'] > 1, value['texture_scale'] > 1))
    ace = ('v1;tier=enhanced;af={};text=off;readout=off;notice=off;wide=off;smooth=off;'
           'sas=off;tess=off;twin={};mips={};ssaa={}').format(
               value['anisotropy'], 'on' if value['full_color'] else 'off',
               'on' if value['mipmaps'] else 'off', value['supersampling'] if value['supersampling'] > 1 else 'off')
    gpu = renderer == 'vulkan'
    return {
        'SR_RESOLUTION_SCALE': str(value['render_scale'] if gpu else 1),
        'SR_GPU_SCALE': str(value['render_scale'] if gpu else 1),
        'SR_PRESENT_SCALING': value['scaling'],
        'SR_PRESENT_UPSCALE': value['upscale'] if gpu else 'off',
        'SR_FULLSCREEN': '1' if value['fullscreen'] and gpu else '0',
        'SR_VSYNC': '1' if value['vsync'] else '0',
        'SR_HUD': '1' if value['hud'] and gpu else '0',
        'SR_FPS_CAP': 'native',
        'LOA_GAMEPLAY_FPS': str(value['gameplay_fps']),
        'SR_ACE': ace if gpu and enhanced else 'off',
        'SR_UI_ROOT': str(ROOT / 'external/nakagawa-recomp'),
        'SR_GAME_TITLE': 'Lord of Apocalypse', 'SR_DISC_ID': 'NPJH50503',
        'SR_TEX_SCALE': str(value['texture_scale']) if gpu and value['texture_scale'] > 1 else 'off',
        'SR_TEX_SCALE_BUDGET_MB': '512', 'SR_SMART_2D': 'off', 'SR_TEX_REPLACE': '',
        'SR_GPU_TWIN_COLOR': '1' if value['full_color'] and gpu else 'off',
        'LOA_MIP_TEXTURES': '1' if gpu and (value['texture_scale']>1 or value['hd_ui']) else '0',
        'LOA_MIP_CAPTURE': '0',
        'LOA_ORIGINAL_UI': '1',
        'LOA_SAMPLER_PACK': '0', 'LOA_ART_CAPTURE': '0', 'LOA_ART_CAPTURE_UI': '0',
    }


def variant_arguments(variant):
    if variant == 'japanese':
        return ['--language', 'japanese']
    if variant == 'english-text-test':
        folder = WIP_FOLDER
        return ['--language', 'english-v16', '--image', str(folder/'LordOfApocalypse-English-WIP.iso'),
                '--candidate-report', str(folder/'result.json')]
    raise ValueError('Unknown game version')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--menu', action='store_true')
    group.add_argument('--set-menu', nargs=len(OPTIONS), type=int)
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.set_menu is not None:
        save(from_menu(args.set_menu))
        print('Graphics settings saved.')
    elif args.menu:
        print(' '.join(map(str, menu_codes(load()))))
    else:
        value = load()
        print(json.dumps({'settings': value, 'environment': environment(value)}, indent=2))


if __name__ == '__main__':
    main()
