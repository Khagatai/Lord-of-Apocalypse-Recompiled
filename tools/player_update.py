"""Offer verified updates from the project's public GitHub releases."""
import ctypes
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

REPOSITORY = 'Khagatai/Lord-of-Apocalypse-Recompiled'
RELEASES = f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=30'
DOWNLOAD = f'https://github.com/{REPOSITORY}/releases/download/'
MAX_INSTALLER_SIZE = 16 * 1024 * 1024


def version_key(tag):
    match = re.fullmatch(r'v?([0-9]{1,6})\.([0-9]{1,6})\.([0-9]{1,6})(?:-(alpha|beta|rc)\.([0-9]{1,6}))?', tag)
    if match is None:
        raise ValueError('Unsupported release version')
    major, minor, patch, channel, serial = match.groups()
    return int(major), int(minor), int(patch), ('alpha', 'beta', 'rc', None).index(channel), int(serial or 0)


def choose_release(releases, installed):
    current = version_key(installed)
    best = None
    for release in releases:
        tag = release.get('tag_name', '')
        try:
            key = version_key(tag)
        except (ValueError, TypeError):
            continue
        if (release.get('draft') or key <= current or not tag.startswith('v')
                or (current[3] == 3 and (key[3] != 3 or release.get('prerelease')))):
            continue
        url = DOWNLOAD + tag + '/Setup.exe'
        # Updates using the older, fresh-install-only Setup.exe are excluded.
        if not any(asset.get('name') == 'Launcher-Update-v1.txt' and asset.get('state') == 'uploaded'
                   for asset in release.get('assets', [])):
            continue
        for asset in release.get('assets', []):
            digest = asset.get('digest') or ''
            size = asset.get('size')
            if (asset.get('name') == 'Setup.exe' and asset.get('state') == 'uploaded'
                    and asset.get('browser_download_url') == url and re.fullmatch(r'sha256:[a-f0-9]{64}', digest)
                    and type(size) is int and 0 < size <= MAX_INSTALLER_SIZE):
                if best is None or key > best[0]:
                    best = key, (tag, url, size, digest[7:])
    return best[1] if best else None


class GithubRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != 'https' or target.hostname not in (
                'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'):
            raise URLError('Unexpected update download address')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def offer(root, launcher_pid):
    """Return True after handing off to a verified updater outside the game folder."""
    try:
        manifest = json.loads((root/'PACKAGE-MANIFEST.json').read_text(encoding='utf-8'))
        if manifest.get('schema') != 2 or manifest.get('builds_native_game_locally') is not True:
            return False
        opener = build_opener(GithubRedirect())
        headers = {'User-Agent': 'LordOfApocalypse-Launcher/1', 'Accept': 'application/vnd.github+json'}
        with opener.open(Request(RELEASES, headers=headers), timeout=4) as response:
            data = response.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError('GitHub release listing is too large')
        release = choose_release(json.loads(data), manifest['version'])
        if release is None:
            return False
        tag, url, size, digest = release
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f'Update check unavailable: {error}', flush=True)
        return False

    box = ctypes.windll.user32.MessageBoxW
    answer = box(None, f'{tag} is available. Install it now?\n\nChoose No to play your installed version.',
                 'Lord of Apocalypse Update', 0x00000124 | 0x00040000)
    if answer != 6:
        return False
    temporary = None
    try:
        cache = Path(os.environ['LOCALAPPDATA'])/'LoARecompSetup'/tag/'updater'
        cache.mkdir(parents=True, exist_ok=True)
        installer = cache/f'Setup-{digest}.exe'
        print(f'Downloading verified update {tag}...', flush=True)
        if not installer.is_file() or installer.stat().st_size != size or hashlib.sha256(installer.read_bytes()).hexdigest() != digest:
            with tempfile.NamedTemporaryFile(dir=cache, suffix='.part', delete=False) as output:
                temporary = Path(output.name)
                with opener.open(Request(url, headers={'User-Agent': headers['User-Agent']}), timeout=20) as response:
                    payload = response.read(size + 1)
                if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
                    raise ValueError('GitHub installer digest or size differs')
                output.write(payload)
            temporary.replace(installer)
        subprocess.Popen([str(installer), '--update', str(root), '--wait', str(launcher_pid), '--tag', tag],
                         cwd=cache, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS)
    except (OSError, ValueError, KeyError) as error:
        box(None, f'The update could not start. Play will continue on the installed version.\n\n{error}',
            'Lord of Apocalypse Update', 0x00000030 | 0x00040000)
        return False
    finally:
        if temporary is not None:
            try:temporary.unlink(missing_ok=True)
            except OSError as error:print(f'Could not remove update scratch file: {error}', flush=True)
    return True
