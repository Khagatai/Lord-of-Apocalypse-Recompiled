import importlib.util,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ui_runtime
spec=importlib.util.spec_from_file_location('package_test_build',ROOT/'tools/package-test-build.py')
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)

class PackageMenu(unittest.TestCase):
    def test_player_filter_keeps_menu_network_and_integrity_helpers(self):
        helpers=package.player_tools()
        for name in ('launch-preview','tester-start','tester_setup','launcher_settings','survey-disc','online_agent','coop_lobby','steam_agent','steam_native','test_support','import_trace_codegen','frame_rate_codegen'):
            self.assertTrue(package.player_member('tools/'+name+'.py',helpers),name)
        for name in ('steam_bridge.cpp','steam_flat.h'):
            self.assertTrue(package.player_member('tools/'+name,helpers))
        for name in ('AGENTS.md','README.md','docs/STATUS.md','tests/test_package_menu.py','tools/check-game-settings.py','external/nakagawa-recomp/docs/VALIDATION.md'):
            self.assertFalse(package.player_member(name,helpers),name)
        for name in ('LICENSE','CREDITS.md','external/nakagawa-recomp/LICENSE','external/nakagawa-recomp/assets/fonts/ui/geist/Geist-Regular.ttf','external/nakagawa-recomp/assets/vfpu/table.bin','private/native-release/lordofapocalypse/RELINK.md'):
            self.assertTrue(package.player_member(name,helpers),name)
    def test_patch_verification_rejects_stale_target_and_changed_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            delta=Path(tmp)/'test.vcdiff';delta.write_bytes(b'verified delta fixture')
            target=dict(size=123,sha256='target')
            row=dict(name='wip',source_sha256='source',target_sha256='target',
                     target_size=123,patch_sha256=package.sha(delta),
                     patch_size=delta.stat().st_size,decoded_payload_hash_verified=True,
                     source_unchanged=True)
            proof=dict(status='PASS',patches=[row])
            self.assertEqual(package.verify_patch_proof(proof,'wip','source',target,delta),row['patch_sha256'])
            with self.assertRaisesRegex(ValueError,'Stale'):
                package.verify_patch_proof(proof,'wip','source',dict(size=123,sha256='new target'),delta)
            delta.write_bytes(b'changed delta fixture!')
            with self.assertRaisesRegex(ValueError,'Stale'):
                package.verify_patch_proof(proof,'wip','source',target,delta)
    def test_dynamic_menu_library_and_sibling_dependencies_are_packaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sdk=root/'bin';sdk.mkdir();system=root/'system';system.mkdir()
            for name in ('SDL3_ttf.dll','libfreetype.dll','zlib.dll'):(sdk/name).write_bytes(b'synthetic')
            exe=root/'game.exe';exe.write_bytes(b'synthetic');(system/'KERNEL32.dll').touch()
            imports={'game.exe':['KERNEL32.dll'],'SDL3_ttf.dll':['libfreetype.dll'],'libfreetype.dll':['zlib.dll'],'zlib.dll':[]}
            with patch.object(package,'pe_imports',side_effect=lambda p:imports[p.name]):
                files=package.dll_closure([exe,*(sdk/n for n in package.DYNAMIC_DLLS)],sdk,system)
            self.assertEqual({p.name for p in files},{'game.exe','SDL3_ttf.dll','libfreetype.dll','zlib.dll'})
    def test_missing_menu_library_has_an_actionable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError,'menu-fix ZIP'):ui_runtime.verify(Path(tmp))
    def test_missing_transitive_dependency_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dll=root/'SDL3_ttf.dll';dll.touch()
            with patch.object(package,'pe_imports',return_value=['missing.dll']):
                with self.assertRaisesRegex(FileNotFoundError,'missing.dll'):package.dll_closure([dll],root,root/'system')

if __name__=='__main__':unittest.main()
