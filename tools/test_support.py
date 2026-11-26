"""Local, allowlisted diagnostic export. No saves, game payloads or uploads."""
from datetime import datetime, timezone
import json,os,re,tempfile,time,zipfile
from pathlib import Path
import graphics_settings
from settings_bridge import atomic_json

PREFIXES = ('AUDIOSTAT', 'PERF ', 'PERF_ATTRIB ', 'PERF_AUDIO', 'PSMF_AV_', 'LOA_AUDIO_ORIGIN', 'LOA_MOVIE_TIMING', 'LOA_AUDIO_PUSH', 'LOA_AUDIO_MIX')
NUMBER = re.compile(r'(?<![\w.])([A-Za-z][A-Za-z0-9_]{0,48})=(-?(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?))(?![\w.:/\\-])')
FIELDS = set('ch pushes q_min_ms q_max_ms underruns starved_ms pushed overruns queued frames '
    'calls withmix pre_nonzero post_nonzero erased pre_peak post_peak no_voice no_voice_overwrite '
    'win end_us vn an voff_us aoff_us av_us windows paired av_min_us av_max_us av_mean_us '
    'header pts raw_pts valid frame picture vblank elapsed_ms alead_us av_submit_us '
    'backpressure pause_enters pause_held_frames pause_stash_failures peak_q lead_ms '
    'block_frames gap_max_us input_peak input_rails scaled_clips clipped_samples mix_peak '
    'vblank_total wall_ms fps frame_ms vblank_hz cpu_ms ge_wait_ms present_ms idle_ms '
    'ge_cpu_ms vk_wait_ms texture_decode_ms iso_read_ms vfs_read_ms h264_ms atrac_ms mix_ms output_ms'.split())

def telemetry(folder, *, network=False):
    path=Path(folder)/'native.log'
    lines=[]
    if path.is_file():
        with path.open('rb') as stream:
            size=stream.seek(0,2);stream.seek(max(0,size-2*1024*1024))
            data=stream.read(2*1024*1024).decode('utf-8',errors='replace')
        for line in data.splitlines():
            prefixes=('LOA_IPC:', 'LOA_COOP_FAULT:', 'NULL_CODE_POINTER:') if network else PREFIXES
            if not line.startswith(prefixes):continue
            # Export only numeric fields, never raw lines, device names, paths or IDs.
            prefix=line.split(':',1)[0].split(' ',1)[0]
            if not re.fullmatch(r'[A-Z_]{3,40}',prefix):continue
            allowed=set('requests failures total_ms max_ms pc ra sp uid vblank fps a0 a1 a2 s0 s1'.split()) if network else FIELDS
            fields={k:v for k,v in NUMBER.findall(line) if k in allowed}
            if network and prefix=='NULL_CODE_POINTER':
                match=re.search(r'computed transfer at (0x[0-9a-fA-F]{8}) targets 0x00000000',line)
                if match:fields['pc']=match[1]
            if fields:lines.append({'kind':prefix,'fields':fields})
    report={'scope':'last-2-MiB-of-log', 'samples':lines[-2000:],
            'complete_session':False,
            'note':'Missing samples are unavailable measurements, not zero errors.'}
    report['multiplayer_validated' if network else 'audio_quality_validated']=False
    return report

def build_identity(root):
    path=Path(root)/'private/native-release/lordofapocalypse/host-ui-build.json'
    data=json.loads(path.read_text())
    result={}
    for key,length in (('framework_commit',40),('executable_sha256',64),('flat_image_sha256',64)):
        value=data.get(key,'')
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{'+str(length)+'}',value):
            raise ValueError('Invalid build identity for report')
        result[key]=value
    return result

def export_report(root, folder, graphics, markers=(), replace_path=None):
    root,folder=Path(root).resolve(),Path(folder).resolve()
    if not folder.is_relative_to(root/'private'):raise ValueError('Report input must stay private')
    output=root/'private/bug-reports';output.mkdir(parents=True,exist_ok=True)
    if output.resolve()!=root/'private/bug-reports':raise ValueError('Report output is redirected')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    target=output/('LordOfApocalypse-report-'+stamp+'.zip')
    if replace_path is not None:
        target=Path(replace_path)
        if target.parent!=output or not re.fullmatch(r'LordOfApocalypse-report-\d{8}-\d{6}-\d{6}\.zip',target.name) or target.is_symlink():
            raise ValueError('Invalid report replacement')
    clean=graphics_settings.validate({'schema':1,**graphics})
    if any(set(m)!={'elapsed_seconds'} or type(m['elapsed_seconds']) not in (int,float) or
           not 0<=m['elapsed_seconds']<10**8 for m in markers):raise ValueError('Invalid audio marker')
    metadata={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),
        'build':build_identity(root),'startup_graphics':clean,'audio_markers':list(markers),
        'excluded':['saves','game files','screenshots','audio recordings','raw logs','network identities','local paths'],
        'gameplay_acceptance':False}
    fd,name=tempfile.mkstemp(prefix='report-',suffix='.tmp',dir=output);os.close(fd)
    temporary=Path(name)
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('report.json',json.dumps(metadata,indent=2))
            archive.writestr('audio-diagnostics.json',json.dumps(telemetry(folder),indent=2))
            archive.writestr('network-diagnostics.json',json.dumps(telemetry(folder,network=True),indent=2))
            archive.writestr('TESTER-NOTES.txt','Describe the location, steps, expected behaviour and what happened.\n'
                'For audio, say whether it was a movie or fight and whether 30 or 60 FPS was selected.\n'
                'For multiplayer, state FPS on every PC and whether it failed during loading, combat or returning.\n'
                'This ZIP was created locally. Nothing was uploaded.\n'
                'Raw logs, saves, game content and network identifiers are excluded.\n'
                'Audio measurements may be unavailable until the runtime exits.\n')
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip():raise RuntimeError('Diagnostic archive failed CRC verification')
        os.replace(temporary,target)
    finally:temporary.unlink(missing_ok=True)
    return target

class Support:
    def __init__(self,root,folder,memstick,graphics,opener=None):
        self.root=Path(root);self.folder=Path(folder);self.memstick=Path(memstick)
        self.graphics=graphics;self.sequence=0;self.started=time.monotonic();self.markers=[]
        self.last_report=None
        self.opener=opener or os.startfile

    def poll(self):
        path=self.folder/'support-request.json'
        if not path.is_file():return
        try:
            value=json.loads(path.read_text())
            if set(value)!={'sequence','op'} or type(value['sequence']) is not int or not 1<=value['sequence']<=1000000:
                raise ValueError('Invalid support request')
            if value['sequence']<=self.sequence:return
            self.sequence=value['sequence']
            operation=value['op']
            if operation=='export':
                target=export_report(self.root,self.folder,self.graphics,self.markers)
                self.last_report=target
                message='Report saved. Open report folder to find the ZIP.'
            elif operation=='mark-audio':
                if len(self.markers)>=100:raise ValueError('Audio marker limit reached')
                self.markers.append({'elapsed_seconds':round(time.monotonic()-self.started,3)})
                atomic_json(self.folder/'audio-markers.json',{'markers':self.markers})
                message='Audio problem marked. Export a report after playing.'
            elif operation in ('open-saves','open-reports'):
                target=self.memstick/'PSP/SAVEDATA' if operation=='open-saves' else self.root/'private/bug-reports'
                if not target.resolve().is_relative_to((self.root/'private').resolve()):raise ValueError('Folder is outside private storage')
                target.mkdir(parents=True,exist_ok=True);self.opener(str(target))
                message='Folder opened.'
            else:raise ValueError('Unknown support action')
            atomic_json(self.folder/'support-ack.json',{'sequence':self.sequence,'ok':True,'message':message})
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,zipfile.BadZipFile) as error:
            (self.folder/'support-error.txt').write_text(str(error)+'\n')
            atomic_json(self.folder/'support-ack.json',{'sequence':self.sequence,'ok':False,'message':'Action failed. See this run\'s support-error.txt.'})

    def finish(self):
        atomic_json(self.folder/'audio-diagnostics.json',telemetry(self.folder))
        network=telemetry(self.folder,network=True)
        atomic_json(self.folder/'network-diagnostics.json',network)
        fatal=any(row['kind'] in ('LOA_COOP_FAULT','NULL_CODE_POINTER') for row in network['samples'])
        if self.last_report or fatal:
            self.last_report=export_report(self.root,self.folder,self.graphics,self.markers,replace_path=self.last_report)
