"""Capture normally paced device audio and real movie-sync telemetry on copied saves."""
import argparse,array,hashlib,importlib.util,json,math,re,sys,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,graphics_settings as settings

def wav_stats(path):
    with wave.open(str(path),'rb') as stream:
        channels,rate,width,frames=stream.getnchannels(),stream.getframerate(),stream.getsampwidth(),stream.getnframes()
        if width!=2:raise ValueError('Expected captured signed 16-bit PCM')
        values=array.array('h',stream.readframes(frames))
    if sys.byteorder!='little':values.byteswap()
    clipped=sum(v in (-32768,32767) for v in values)
    return dict(channels=channels,rate=rate,frames=frames,seconds=frames/rate,
        peak=max(map(abs,values),default=0),clipped_samples=clipped,
        clipped_fraction=clipped/len(values) if values else 0,
        rms=math.sqrt(sum(v*v for v in values)/len(values)) if values else 0,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--modes',nargs='+',type=int,choices=(30,60),default=[30,60])
    args=p.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private') or out.exists():p.error('Use a fresh private report folder')
    title.verify_inputs();out.mkdir(parents=True)
    pad=out/'route.pad';pad.write_text('1150 CIRCLE 20\n1400 START 20\n')
    image=settings.WIP_FOLDER/'LordOfApocalypse-English-WIP.iso'
    from translation_candidate import verify
    verify(image,image.parent/'result.json')
    spec=importlib.util.spec_from_file_location('window_capture',ROOT/'tools/check-text-sharpening.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    prefs=settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None
    report=dict(scope='device-audio-and-movie-sync-diagnostic',framework_commit=title.CONFIG['runtime']['commit'],runs={},audio_quality_validated=False)
    for mode in args.modes:
        folder=out/str(mode);env=title.environment()
        env.update(settings.environment(dict(settings.ORIGINAL,render_scale=2,gameplay_fps=mode)))
        env.update(SR_AUDIODUMP=str(folder/'device.wav'),SR_AUDIOSTAT='1',SR_MPEGLOG='1',SR_PERF='1',LOA_FPS_TRACE='1',LOA_MOVIE_TIMING='1',LOA_AUDIO_DIAGNOSTICS='1')
        native=helper.window_check(folder,image,env,frame_window=(2700,2710),padscript=pad,timeout_seconds=100,
            save_fixture=ROOT/'private/memstick/english-text-test',deterministic=False)
        log=(folder/'native.log').read_text(errors='replace')
        run=dict(native=native,wav=wav_stats(folder/'device.wav'),
            audio_lines=[line for line in log.splitlines() if line.startswith(('AUDIODUMP:','AUDIOSTAT','PERF_AUDIO','audio:'))],
            movie_sync=[line for line in log.splitlines() if line.startswith('PSMF_AV_PRESENT')],
            picture_timing=[line for line in log.splitlines() if line.startswith('LOA_MOVIE_TIMING:')])
        report['runs'][str(mode)]=run
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(mode=mode,wav=run['wav'],sync=run['movie_sync'][-1:])),flush=True)
        if native['returncode'] or native['timed_out'] or not native['save_fixture_source_unchanged'] or not native['font_files_unchanged']:
            raise ValueError('Audio diagnostic did not exit cleanly or changed protected inputs')
    report['preferences_unchanged']=prefs==(settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['preferences_unchanged']:raise ValueError('Normal preferences changed')

if __name__=='__main__':main()
