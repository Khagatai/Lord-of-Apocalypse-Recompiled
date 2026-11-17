"""Compare normally paced native frame cadence and update deltas with copied saves."""
import argparse,csv,hashlib,importlib.util,json,re,sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title,graphics_settings as settings,save_storage

def movie_pts(log):
    """Global decoder log counters span movies; compare a single stream's prefix."""
    sessions=[];current=None;audio_base=None
    for line in log.splitlines():
        if 'LOA_FPS: media event=0 ' in line:
            current={'video':{},'audio':{}};sessions.append(current);audio_base=None
        elif 'LOA_FPS: media event=1 ' in line:current=None
        if current is None:continue
        video=re.search(r'MpegAvcDecode #\d+.*?pts=(\d+).*?frames=(\d+)',line)
        audio=re.search(r'MpegGetAtracAu #(\d+) pts=(\d+)',line)
        if video:current['video'][int(video[2])]=int(video[1])
        if audio:
            if audio_base is None:audio_base=int(audio[1])-1
            current['audio'][int(audio[1])-audio_base]=int(audio[2])
    return max(sessions,key=lambda s:len(s['video']),default={'video':{},'audio':{}})

def compare_movie_pts(runs):
    result={}
    for stream in ('video','audio'):
        a=runs['30']['movie_'+stream+'_pts'];b=runs['60']['movie_'+stream+'_pts']
        common=set(a)&set(b)
        identical=len(common)>=16 and all(a[k]==b[k] for k in common)
        if stream=='audio':
            # Decoder log counters span contexts and become sparse after #16.
            # Compare start PTS and every sampled interval per AU, not log-row index.
            slopes=[]
            for values in (a,b):
                items=sorted(values.items())
                slopes.append({Fraction(v-items[0][1],k-items[0][0]) for k,v in items[1:]} if items else set())
            identical=(len(a)>=4 and len(b)>=4 and a[min(a)]==b[min(b)]
                and len(slopes[0])==1 and slopes[0]==slopes[1] and next(iter(slopes[0]))>0)
        result[stream]=dict(common_samples=len(common),samples_30=len(a),samples_60=len(b),identical=identical)
    return result

def helper(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'private') or out.exists():p.error('Use a fresh private report folder')
    title.verify_inputs();out.mkdir(parents=True)
    # Let the complete opening movie play before sending menu input. The short
    # stock-mode movie-skip script is not a verified route at the upgraded rate.
    route=('1150 CIRCLE 20\n1400 START 20\n1700 START 20\n'
        '7200 START 20\n7500 CIRCLE 20\n7800 CIRCLE 20\n8100 CIRCLE 20\n8400 CIRCLE 20\n'
        '9600 LEFT 60\n10100 0 60 128 0\n10600 RIGHT 60\n11100 0 60 255 128\n')
    window=(11800,11810);sample_low,sample_high=11400,11700
    pad=out/'route.pad';pad.write_text(route)
    image=settings.WIP_FOLDER/'LordOfApocalypse-English-WIP.iso'
    helper('check-text-sharpening')
    from translation_candidate import verify
    verify(image,image.parent/'result.json')
    fixture=ROOT/'private/memstick/english-text-test';before=save_storage.tree_hashes(fixture)
    preferences=settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None
    runs={}
    for mode in (60,30):
        folder=out/str(mode)
        env=title.environment();env.update(settings.environment(dict(settings.ORIGINAL,gameplay_fps=mode,render_scale=2)))
        env.update(LOA_FPS_TRACE='1',SR_PERF_FRAMES=str(folder/'frames.csv'),SR_MPEGLOG='1')
        result=helper('check-text-sharpening').window_check(folder,image,env,
            frame_window=window,padscript=pad,timeout_seconds=300,save_fixture=fixture,deterministic=False)
        log=(folder/'native.log').read_text(errors='replace')
        frames=list(csv.DictReader((folder/'frames.csv').open()))
        town=[row for row in frames if sample_low<=int(row['vcount'])<=sample_high]
        if len(town)<10:raise ValueError('Too few town frames')
        gaps=[int(row['vblanks']) for row in town]
        mean_gap=sum(gaps)/len(gaps)
        dominant_gap,dominant_count=Counter(gaps).most_common(1)[0]
        samples=[dict(v=int(m[0]),enhanced=int(m[1]),media=int(m[2]),delta=float(m[3]),minimum=float(m[4]),updates=int(m[5]),sum=float(m[6]))
            for m in re.findall(r'LOA_FPS: sample v=(\d+) object=\w+ enhanced=(\d) media=(\d) delta=([\d.]+) min=([\d.]+) updates=(\d+) sum=([\d.]+)',log)]
        stable=[s for s in samples if sample_low<=s['v']<=sample_high]
        media_samples=[s for s in samples if s['media']]
        pts=movie_pts(log)
        expected=2 if mode==30 else 1
        cadence_passed=(dominant_gap==expected and dominant_count/len(gaps)>=0.85 and abs(mean_gap/expected-1)<0.1)
        floor_passed=bool(stable) and all(s['minimum']==float(expected) for s in stable)
        movie_protection_passed=bool(media_samples) and all(s['minimum']==2.0 and s['enhanced']==0 for s in media_samples)
        runs[str(mode)]=dict(native=result,mean_guest_vblanks_per_frame=mean_gap,
            host_fps_in_sample=1000/(sum(float(row['wall_ms']) for row in town)/len(town)),
            dominant_guest_vblanks_per_frame=dominant_gap,gap_counts=dict(Counter(gaps)),
            cadence_passed=cadence_passed,update_floor_passed=floor_passed,movie_protection_passed=movie_protection_passed,
            guest_fps=(60000/1001)/mean_gap,observed_frames=len(town),stable_samples=stable,
            media_samples=media_samples,
            movie_video_pts=pts['video'],movie_audio_pts=pts['audio'],
            media_events=[line for line in log.splitlines() if 'LOA_FPS: media event=' in line],
            timing_summary=[line for line in log.splitlines() if 'LOA_FPS: exit' in line],
            interpreter_summary=[line for line in log.splitlines() if line.startswith('EXEC_SHARE')])
        if result['returncode'] or result['timed_out'] or not result['save_fixture_source_unchanged'] or not result['font_files_unchanged']:
            raise ValueError('Native checkpoint failed')
    unchanged=before==save_storage.tree_hashes(fixture) and preferences==(settings.SETTINGS.read_bytes() if settings.SETTINGS.exists() else None)
    rates={mode:(r['stable_samples'][-1]['sum']-r['stable_samples'][0]['sum'])/(r['stable_samples'][-1]['v']-r['stable_samples'][0]['v'])
        for mode,r in runs.items() if len(r['stable_samples'])>=2}
    speed_passed=len(rates)==2 and rates['30']>0 and abs(rates['60']/rates['30']-1)<0.03
    pts_comparisons=compare_movie_pts(runs)
    pts_passed=all(c['identical'] for c in pts_comparisons.values())
    passed=unchanged and speed_passed and pts_passed and all(all(r[k] for k in ('cadence_passed','update_floor_passed','movie_protection_passed')) for r in runs.values())
    report=dict(scope='native-paced-town-cadence-at-2x-not-full-profile-performance',passed=passed,
        framework_commit=title.CONFIG['runtime']['commit'],source_saves_and_preferences_unchanged=unchanged,
        update_time_per_vblank=rates,update_speed_passed=speed_passed,
        movie_pts_comparisons=pts_comparisons,movie_source_pts_unchanged=pts_passed,
        movie_context_protection_validated=all(r['movie_protection_passed'] for r in runs.values()),
        full_movie_playback_validated=False,combat_validated=False,host_performance_validated=False,runs=runs)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({mode:dict(guest_fps=r['guest_fps'],frames=r['observed_frames']) for mode,r in runs.items()},indent=2))
    if not passed:raise ValueError('Cadence, update speed, movie protection or protected input check failed; inspect result.json')

if __name__=='__main__':main()
