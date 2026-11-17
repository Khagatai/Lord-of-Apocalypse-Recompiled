import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import graphics_settings as settings


class GraphicsSettings(unittest.TestCase):
    def test_frame_rate_is_a_gameplay_choice_not_a_presentation_cap(self):
        self.assertEqual(settings.DEFAULTS['gameplay_fps'],30)
        value=dict(settings.DEFAULTS,gameplay_fps=60)
        self.assertEqual(settings.environment(value)['LOA_GAMEPLAY_FPS'],'60')
        self.assertEqual(settings.environment(value)['SR_FPS_CAP'],'native')
        for preset in ('quality','balanced'):
            self.assertEqual(settings.apply_preset(value,preset)['gameplay_fps'],60)
        self.assertEqual(settings.apply_preset(value,'original')['gameplay_fps'],30)
        with self.assertRaises(ValueError):settings.validate({'schema':1,**dict(value,gameplay_fps=120)})

    def test_existing_saved_profile_defaults_to_original_fps_without_a_write(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'graphics.json'
            old=dict(settings.DEFAULTS);del old['gameplay_fps']
            path.write_text(json.dumps({'schema':1,**old}))
            before=path.read_bytes()
            self.assertEqual(settings.load(path),dict(old,gameplay_fps=30))
            self.assertEqual(path.read_bytes(),before)
    def test_safe_profile_is_temporary_windowed_and_keeps_the_language(self):
        saved=dict(settings.DEFAULTS,fullscreen=True,window_size=(3840,2160),variant='japanese')
        before=copy.deepcopy(saved)
        safe=settings.apply_preset(saved,'original')
        self.assertEqual(saved,before)
        self.assertEqual(safe,dict(settings.ORIGINAL,variant='japanese'))
        self.assertEqual(settings.environment(safe)['SR_ACE'],'off')
        self.assertFalse(safe['hd_ui'])

    def test_quality_restores_effects_and_preserves_display_and_language(self):
        current=dict(settings.ORIGINAL,fullscreen=True,variant='japanese',window_size=(2560,1440),vsync=False)
        result=settings.apply_preset(current,'quality')
        for key in ('variant','fullscreen','window_size','vsync'):
            self.assertEqual(result[key],current[key])
        for key,value in settings.QUALITY.items():
            self.assertEqual(result[key],value)
        with self.assertRaises(ValueError):settings.apply_preset(current,'unknown')

    def test_presentation_upscaling_and_hd_opt_in_are_independent(self):
        self.assertFalse(settings.DEFAULTS['hd_ui'])
        for enabled in (False, True):
            saved = dict(settings.DEFAULTS, hd_ui=enabled)
            self.assertEqual(settings.apply_preset(saved, 'quality')['hd_ui'], enabled)
            self.assertEqual(settings.apply_preset(saved, 'balanced')['hd_ui'], enabled)
        environment = settings.environment(settings.DEFAULTS)
        self.assertEqual(environment['SR_PRESENT_UPSCALE'], 'fsr1')
        self.assertEqual(environment['SR_TEX_SCALE'], '4')
        self.assertEqual(environment['SR_TEX_REPLACE'], '')

    def test_roundtrip_and_invalid_choice_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'settings.json'
            self.assertEqual(settings.load(path), settings.DEFAULTS)
            value = dict(settings.DEFAULTS, render_scale=4, anisotropy=16, fullscreen=True)
            settings.save(value, path)
            self.assertEqual(settings.load(path), value)
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'render_scale'):
                settings.save(dict(value, render_scale=8), path)
            self.assertEqual(path.read_bytes(), before)

    def test_menu_contract_preserves_every_choice(self):
        for key, choices in settings.OPTIONS.items():
            for value in choices:
                chosen = dict(settings.DEFAULTS, **{key: value})
                self.assertEqual(settings.from_menu(settings.menu_codes(chosen)), chosen)
        with self.assertRaises(ValueError):
            settings.from_menu([0]*11)
        with self.assertRaises(ValueError):
            settings.from_menu([999]*12)

    def test_real_render_scale_overrides_diagnostic_alias_and_preserves_audio_policy(self):
        env = settings.environment(dict(settings.DEFAULTS, render_scale=4, anisotropy=16, mipmaps=True))
        self.assertEqual(env['SR_RESOLUTION_SCALE'], '4')
        self.assertEqual(env['SR_GPU_SCALE'], '4')
        self.assertIn('af=16', env['SR_ACE'])
        self.assertIn('mips=on', env['SR_ACE'])
        self.assertIn('sas=off', env['SR_ACE'])
        self.assertIn('smooth=off', env['SR_ACE'])
        self.assertNotIn('load=fast', env['SR_ACE'])

    def test_original_preset_has_no_enhancement_and_software_fallback_is_explicit(self):
        self.assertEqual(settings.environment(settings.ORIGINAL)['SR_ACE'], 'off')
        env = settings.environment(dict(settings.DEFAULTS, render_scale=4, fullscreen=True, upscale='fsr1', supersampling=2), 'gdi')
        self.assertEqual(env['SR_GPU_SCALE'], '1')
        self.assertEqual(env['SR_ACE'], 'off')
        self.assertEqual(env['SR_FULLSCREEN'], '0')
        self.assertEqual(env['SR_PRESENT_UPSCALE'], 'off')

    def test_version_selection_preserves_candidate_and_save_routing(self):
        args = settings.variant_arguments('english-text-test')
        self.assertIn('--candidate-report', args)
        self.assertIn('--image', args)
        self.assertNotIn('--candidate-report', settings.variant_arguments('japanese'))
        with self.assertRaises(ValueError):
            settings.variant_arguments('unknown')

    def test_texture_scaling_enables_real_renderer_and_software_disables_it(self):
        value = dict(settings.DEFAULTS, texture_scale=4)
        env = settings.environment(value)
        self.assertEqual(env['SR_TEX_SCALE'], '4')
        self.assertEqual(env['SR_TEX_SCALE_BUDGET_MB'], '512')
        self.assertNotEqual(env['SR_ACE'], 'off')
        self.assertEqual(env['SR_SMART_2D'], 'off')
        self.assertEqual(settings.environment(value, 'gdi')['SR_TEX_SCALE'], 'off')
        self.assertEqual(settings.environment(settings.ORIGINAL)['SR_TEX_SCALE'], 'off')
        self.assertEqual(env['LOA_MIP_TEXTURES'], '1')
        self.assertEqual(env['LOA_MIP_CAPTURE'], '0')
        self.assertEqual(settings.environment(value, 'gdi')['LOA_MIP_TEXTURES'], '0')
        self.assertEqual(settings.environment(settings.ORIGINAL)['LOA_MIP_TEXTURES'], '0')
        self.assertEqual(settings.environment(dict(settings.ORIGINAL, hd_ui=True))['LOA_MIP_TEXTURES'], '1')

    def test_legacy_settings_migrate_without_writing_or_losing_choices(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'settings.json'
            legacy = dict(settings.DEFAULTS, render_scale=4, fullscreen=True)
            del legacy['texture_scale']
            del legacy['hd_ui']
            path.write_text(json.dumps({'schema': 1, **legacy}))
            before = path.read_bytes()
            self.assertEqual(settings.load(path), dict(legacy, texture_scale=1, hd_ui=False))
            self.assertEqual(path.read_bytes(), before)
            with_texture = dict(legacy, texture_scale=4)
            path.write_text(json.dumps({'schema': 1, **with_texture}))
            self.assertEqual(settings.load(path), dict(with_texture, hd_ui=False))
            del legacy['vsync']
            path.write_text(json.dumps({'schema': 1, **legacy}))
            with self.assertRaises(ValueError): settings.load(path)


if __name__ == '__main__':
    unittest.main()
