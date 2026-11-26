import json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import test_support,graphics_settings,save_storage
from settings_bridge import atomic_json

class TestSupport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.run=self.root/'private/preview-fixture';self.run.mkdir(parents=True)
        build=self.root/'private/native-release/lordofapocalypse';build.mkdir(parents=True)
        (build/'host-ui-build.json').write_text(json.dumps(dict(framework_commit='a'*40,executable_sha256='b'*64,flat_image_sha256='c'*64)))
        self.saves=save_storage.memstick_path(self.root,'japanese')
        savedata=self.saves/'PSP/SAVEDATA/NPJH50503USERID_0000';savedata.mkdir(parents=True)
        (savedata/'DATA.BIN').write_bytes(b'SECRET SAVE BYTES')
        self.opened=[]
        self.support=test_support.Support(self.root,self.run,self.saves,graphics_settings.DEFAULTS,self.opened.append)
    def request(self,seq,op):
        atomic_json(self.run/'support-request.json',{'sequence':seq,'op':op});self.support.poll()
        return json.loads((self.run/'support-ack.json').read_text())
    def test_export_excludes_game_data_paths_identities_and_raw_logs(self):
        (self.run/'native.log').write_text('SECRET LOCAL PATH C:/Users/Somebody game strings\n'
            'PERF_AUDIO ch=8 pushes=9 underruns=2 starved_ms=4.000 account=76561199123456789 ip=192.168.1.1 token=SECRET\n'
            'AUDIOSTAT_HOST: pushed=22 driver=SECRET underruns=3\n')
        self.assertTrue(self.request(1,'export')['ok'])
        with zipfile.ZipFile(self.support.last_report) as archive:
            self.assertEqual(set(archive.namelist()),{'report.json','audio-diagnostics.json','network-diagnostics.json','TESTER-NOTES.txt'})
            data=b''.join(archive.read(n) for n in archive.namelist())
            for secret in (b'SECRET',b'Somebody',b'76561199123456789',b'192.168.1.1'):
                self.assertNotIn(secret,data)
            metrics=json.loads(archive.read('audio-diagnostics.json'))
            self.assertEqual(metrics['samples'][0]['fields']['underruns'],'2')
    def test_stale_request_not_repeated_and_open_save_folder_is_explicit(self):
        self.request(1,'open-saves');self.request(1,'open-saves')
        self.assertEqual(self.opened,[str(self.saves/'PSP/SAVEDATA')])
        self.assertFalse(self.request(2,'delete-saves')['ok'])
        self.assertTrue((self.saves/'PSP/SAVEDATA/NPJH50503USERID_0000/DATA.BIN').exists())
    def test_audio_markers_and_exit_stats_refresh_the_same_report(self):
        self.assertTrue(self.request(1,'mark-audio')['ok']);self.request(2,'export')
        target=self.support.last_report
        (self.run/'native.log').write_text('AUDIOSTAT_HOST: underruns=7 pushed=50\n')
        self.support.finish()
        self.assertEqual(list(target.parent.glob('*.zip')),[target])
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(len(json.loads(archive.read('report.json'))['audio_markers']),1)
            self.assertEqual(json.loads(archive.read('audio-diagnostics.json'))['samples'][0]['fields']['underruns'],'7')
    def test_missing_telemetry_is_not_a_zero_error_pass(self):
        metrics=test_support.telemetry(self.run)
        self.assertEqual(metrics['samples'],[]);self.assertFalse(metrics['audio_quality_validated'])
    def test_network_fault_and_ipc_export_is_numeric_and_excludes_memory(self):
        (self.run/'native.log').write_text('LOA_IPC: requests=60 failures=2 total_ms=12.5 max_ms=9 account=76561199123456789 token=SECRET\n'
            'LOA_COOP_FAULT: pc=0x08bf386c ra=0x08bf3804 sp=0x09ffe910 uid=0x125 vblank=139387 fps=60 s1=0x09000000\n'
            'LOA_COOP_MEMORY: argument address=09000000 word0=SECRET\n'
            'NULL_CODE_POINTER: computed transfer at 0x08bf386c targets 0x00000000 ra=0x08bf3804 sp=0x09ffe910 uid=0x125\n')
        self.request(1,'export')
        with zipfile.ZipFile(self.support.last_report) as archive:
            raw=archive.read('network-diagnostics.json');report=json.loads(raw)
            self.assertEqual(len(report['samples']),3)
            self.assertEqual(report['samples'][0]['fields']['requests'],'60')
            self.assertEqual(report['samples'][1]['fields']['pc'],'0x08bf386c')
            self.assertEqual(report['samples'][2]['fields']['pc'],'0x08bf386c')
            for secret in (b'SECRET',b'76561199123456789',b'word0'):self.assertNotIn(secret,raw)
            self.assertFalse(report['multiplayer_validated'])
    def test_fatal_callback_exports_once_at_exit_without_a_menu_request(self):
        self.support.finish();self.assertIsNone(self.support.last_report)
        (self.run/'native.log').write_text('LOA_COOP_FAULT: pc=0x08bf386c ra=0x08bf3804 fps=60\n')
        self.support.finish();target=self.support.last_report;self.assertTrue(target.is_file())
        self.support.finish();self.assertEqual(self.support.last_report,target)
        self.assertEqual(list(target.parent.glob('*.zip')),[target]);self.assertEqual(self.opened,[])
    def test_audio_transition_measurements_remain_numeric_and_private(self):
        (self.run/'native.log').write_text('LOA_AUDIO_PUSH: elapsed_ms=2000 vblank=120 ch=8 gap_max_us=250000 input_rails=2 scaled_clips=0 path=C:/SECRET token=SECRET\n'
            'LOA_AUDIO_MIX: elapsed_ms=2000 frames=44100 clipped_samples=9 mix_peak=40000\n'
            'PERF vblank_total=120 wall_ms=1000 cpu_ms=800 fps=19 account=76561199123456789\n'
            'PERF_ATTRIB ge_cpu_ms=700 texture_decode_ms=6 path=C:/SECRET\n')
        self.request(1,'export')
        with zipfile.ZipFile(self.support.last_report) as archive:
            data=archive.read('audio-diagnostics.json');self.assertNotIn(b'SECRET',data)
            samples=json.loads(data)['samples']
            self.assertEqual(samples[0]['fields']['gap_max_us'],'250000')
            self.assertEqual(samples[1]['fields']['clipped_samples'],'9')
            self.assertEqual(samples[2]['fields']['cpu_ms'],'800')
            self.assertEqual(samples[3]['fields']['ge_cpu_ms'],'700')
            self.assertNotIn(b'76561199123456789',data)
    def test_report_failure_returns_failure_and_never_uploads_or_opens(self):
        build=self.root/'private/native-release/lordofapocalypse/host-ui-build.json';build.write_text('{}')
        self.assertFalse(self.request(1,'export')['ok']);self.assertEqual(self.opened,[])
        self.assertEqual(list((self.root/'private/bug-reports').iterdir()),[])

if __name__=='__main__':unittest.main()
