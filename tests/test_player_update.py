import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import player_update


def release(tag, *, ready=True, **fields):
    assets = [dict(name='Setup.exe', state='uploaded', size=100, digest='sha256:'+'a'*64,
                   browser_download_url=player_update.DOWNLOAD+tag+'/Setup.exe')]
    if ready:
        assets.append(dict(name='Launcher-Update-v1.txt', state='uploaded'))
    return dict(tag_name=tag, assets=assets, **fields)


class Discovery(unittest.TestCase):
    def test_newer_beta_sorted_numerically_and_requires_upgrade_installer(self):
        rows = [release('v0.9.0-beta.2'), release('v0.9.0-beta.10'), release('v0.9.1', ready=False),
                release('v1.0.0', draft=True), release('v0.8.0')]
        self.assertEqual(player_update.choose_release(rows, '0.9.0-beta.1')[0], 'v0.9.0-beta.10')
        self.assertIsNone(player_update.choose_release(rows, '0.9.0-beta.10'))

    def test_stable_channel_and_digest_verification(self):
        good = release('v1.0.1')
        invalid = release('v1.0.2')
        invalid['assets'][0]['browser_download_url'] = 'https://example.com/Setup.exe'
        no_digest = release('v1.0.3')
        no_digest['assets'][0]['digest'] = None
        rows = [good, invalid, no_digest, release('v2.0.0-beta.1', prerelease=True)]
        self.assertEqual(player_update.choose_release(rows, '1.0.0')[0], 'v1.0.1')


@unittest.skipUnless(os.name == 'nt', 'Windows setup engine')
class Upgrade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='loa-update-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        spec = importlib.util.spec_from_file_location('update_setup_builder', ROOT/'tools/build-online-setup.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        if not builder.CSC.is_file():raise unittest.SkipTest('Windows C# compiler unavailable')
        cls.runner = cls.root/'setup-test.exe'
        builder.build(None, cls.runner, ROOT/'tests/online_setup_runner.cs')

    def fixture(self, base, version, files):
        manifest = dict(schema=2, version=version, builds_native_game_locally=True, game_payloads_included=False,
                        files=[dict(path=name,size=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in files.items()])
        if base.is_dir():
            for name,data in files.items():
                path=base/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(data)
            (base/'PACKAGE-MANIFEST.json').write_text(json.dumps(manifest))
        else:
            with zipfile.ZipFile(base,'w') as archive:
                archive.writestr('LordOfApocalypse-Recomp/PACKAGE-MANIFEST.json',json.dumps(manifest))
                for name,data in files.items():archive.writestr('LordOfApocalypse-Recomp/'+name,data)

    def test_update_reuses_matching_files_and_can_roll_back(self):
        install=self.root/'installed';install.mkdir()
        old={'LordOfApocalypse.exe':b'launcher one','tools/keep.py':b'unchanged','tools/retired.py':b'retired'}
        new={'LordOfApocalypse.exe':b'launcher two','tools/keep.py':b'unchanged','tools/added.py':b'new'}
        self.fixture(install,'0.9.0-beta.1',old)
        persistent=('private/memstick/save.dat','private/settings/settings.json','private/hd-remaster-pack/owner.json',
                    'private/native-release/lordofapocalypse/lordofapocalypse.exe','private/distribution/local-image.json')
        for name in persistent:
            path=install/name
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'player data')
        stamp=(install/'tools/keep.py').stat().st_mtime_ns
        package=self.root/'payload.zip';self.fixture(package,'0.9.0-beta.2',new)
        metadata=self.root/'release.json'
        raw=package.read_bytes()
        metadata.write_text(json.dumps(dict(schema=1,version='0.9.0-beta.2',expanded_size=32768,assets=[
            dict(name=package.name,url='http://127.0.0.1/payload.zip',size=len(raw),sha256=hashlib.sha256(raw).hexdigest())])))
        args=[str(self.runner),str(metadata),str(install),str(self.root/'cache'),str(self.root)]
        failure=subprocess.run([*args,'rollback'],capture_output=True,text=True,timeout=30)
        self.assertEqual(failure.returncode,2,failure.stdout)
        self.assertIn('Simulated update failure',failure.stdout)
        self.assertEqual((install/'LordOfApocalypse.exe').read_bytes(),old['LordOfApocalypse.exe'])
        self.assertEqual(json.loads((install/'PACKAGE-MANIFEST.json').read_text())['version'],'0.9.0-beta.1')
        self.assertFalse((install/'tools/added.py').exists())
        updated=subprocess.run([*args,'upgrade'],capture_output=True,text=True,timeout=30)
        self.assertEqual(updated.returncode,0,updated.stdout)
        self.assertEqual((install/'LordOfApocalypse.exe').read_bytes(),new['LordOfApocalypse.exe'])
        self.assertEqual((install/'tools/added.py').read_bytes(),new['tools/added.py'])
        self.assertFalse((install/'tools/retired.py').exists())
        self.assertEqual((install/'tools/keep.py').stat().st_mtime_ns,stamp)
        self.assertEqual(json.loads((install/'PACKAGE-MANIFEST.json').read_text())['version'],'0.9.0-beta.2')
        self.assertFalse((install/'private/launcher/update-in-progress.json').exists())
        for name in persistent:self.assertEqual((install/name).read_bytes(),b'player data')
