import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import local_player_setup as setup


class PlayerSetupAdmission(unittest.TestCase):
    def test_base_launch_skips_hd_and_remains_ready_after_interrupted_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(setup, 'ROOT', Path(tmp)):
            image = Path(tmp)/'game.iso'
            image.write_bytes(b'verified ISO')
            manifest = setup.local('private/distribution/release.json')
            manifest.parent.mkdir(parents=True)
            manifest.write_text('release')
            plan = dict(original=dict(size=image.stat().st_size, sha256=setup.sha(image)), recipes={})

            def base(*args):
                for name in setup.base_outputs():
                    path = setup.local(name)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'test output')

            with (patch.object(setup, 'plan', return_value=plan),
                  patch.object(setup.source_identity, 'verify'),
                  patch.object(setup, 'prepare_base', side_effect=base) as build_base,
                  patch.object(setup, 'prepare_hd', side_effect=RuntimeError('interrupted')) as build_hd):
                self.assertFalse(setup.prepare(image, jobs=1)['HD_requested'])
                build_hd.assert_not_called()
                with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                    setup.prepare(image, jobs=1, with_hd=True)
                self.assertTrue(setup.ready())
                self.assertFalse(setup.ready(with_hd=True))
                self.assertTrue(setup.prepare(image, jobs=1)['already_prepared'])
                build_base.assert_called_once()

                build_hd.side_effect = None
                output = setup.local(setup.HD_OUTPUT)
                output.parent.mkdir(parents=True)
                output.write_text('HD output')
                setup.prepare(image, jobs=1, with_hd=True)
                self.assertTrue(setup.ready(with_hd=True))
                output.unlink()
                self.assertTrue(setup.ready())
                self.assertFalse(setup.ready(with_hd=True))

    def test_wrong_dump_creates_no_game_files_or_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image=root/'game.iso';image.write_bytes(b'wrong')
            manifest=dict(original=dict(size=5,sha256='0'*64),recipes={})
            with patch.object(setup,'ROOT',root),patch.object(setup,'plan',return_value=manifest),patch.object(setup.source_identity,'verify') as verify:
                with self.assertRaisesRegex(ValueError,'unmodified Japanese'):setup.prepare(image)
                verify.assert_not_called()
            self.assertFalse((root/'private').exists())

    def test_partial_generation_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'private/local-build';folder.mkdir(parents=True)
            (folder/'ready.json').write_text(json.dumps(dict(state='GENERATING',outputs=[])))
            with patch.object(setup,'ROOT',root):self.assertFalse(setup.ready())

    def test_ready_marker_cannot_survive_replaced_release_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dist=root/'private/distribution';dist.mkdir(parents=True)
            manifest=dist/'release.json';manifest.write_text('original')
            folder=root/'private/local-build';folder.mkdir()
            (folder/'ready.json').write_text(json.dumps(dict(state='READY',release_manifest_sha256=setup.sha(manifest),outputs=[])))
            manifest.write_text('replaced')
            with patch.object(setup,'ROOT',root):self.assertFalse(setup.ready())

    def test_recipe_change_fails_before_game_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config';config.mkdir();dist=root/'private/distribution';dist.mkdir(parents=True)
            text=dist/'words.json';text.write_text('changed')
            plan=config/'player-build.json';plan.write_text(json.dumps(dict(schema=1,original={},recipes=dict(messages=dict(path='private/distribution/words.json',sha256='0'*64)))))
            (dist/'release.json').write_text(json.dumps(dict(schema=2,kind='ISO-local-native-build',original={},build_plan=dict(path='config/player-build.json',sha256=setup.sha(plan)))))
            with patch.object(setup,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'recipe changed'):setup.plan()
            self.assertFalse((root/'private/modules').exists())


if __name__=='__main__':unittest.main()
