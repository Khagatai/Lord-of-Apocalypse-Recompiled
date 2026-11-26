"""Bounded Win32 F1/pause and physical client-size check using copied saves."""
import argparse
import contextlib
import ctypes
from ctypes import wintypes as w
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import graphics_settings
import save_storage
import title
import window_settings
import settings_bridge
import test_support
import controller_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--restart', action='store_true', help='Exercise advanced/language/presets and clean restart into WIP English')
    parser.add_argument('--fps',action='store_true',help='Exercise the gameplay 30/60 FPS setting and revert the isolated fixture to 30')
    parser.add_argument('--controls',action='store_true',help='Exercise native F1 binding save, live reload and defaults with isolated controller preferences')
    parser.add_argument('--support',action='store_true',help='Exercise F1 audio marking and safe local diagnostic export')
    parser.add_argument('--relocated',action='store_true',help='Verify an existing packaged release without development Git metadata')
    parser.add_argument('--preferences',type=Path,help='Existing private QA preferences shared with a launcher fixture')
    parser.add_argument('--network',action='store_true',help='Visit the standalone F1 Networking page, then verify Settings still works')
    parser.add_argument('--online',action='store_true',help='Create a real room from F1 through an owned loopback service and native WebRTC peer')
    parser.add_argument('--steam',action='store_true',help='Create and leave one real friends-only Steam App ID 480 lobby through F1; no invitations or peer claims')
    args = parser.parse_args()
    if args.online:args.network=True
    if args.steam:
        if args.online:parser.error('Choose a single networking backend per check.')
        args.network=True
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use a fresh private output directory')
    title.verify_launch_inputs('release') if args.relocated else title.verify_inputs()
    output.mkdir(parents=True)
    stack=contextlib.ExitStack()
    fixture = ROOT/'private/memstick/japanese'
    before = save_storage.tree_hashes(fixture)
    shutil.copytree(fixture, output/'memstick')
    preferences = graphics_settings.SETTINGS
    original = preferences.read_bytes() if preferences.exists() else None
    env = title.environment()
    for key in ('SR_HEADLESS', 'SR_WINDOW_HIDDEN', 'SR_PADSCRIPT', 'SR_PAD', 'SR_NOINPUT', 'SR_EXIT_AT_VBLANK'):
        env.pop(key, None)
    env.update(graphics_settings.environment(dict(graphics_settings.ORIGINAL, render_scale=2, anisotropy=4)))
    env.update(PSP_ISO=str(title.disc_image('japanese')),
               SR_MEMSTICK=str(output/'memstick'), SR_MODULE_DIR=str(ROOT/'private/modules'),
               SR_REAL_MODULE_START='1', SR_BOOT_PATH=title.CONFIG['module']['start_thread']['argument'],
               SR_PADWIDTH='0', SR_VIDEO='vulkan', SR_GPU_GE='1')
    profile=dict(graphics_settings.ORIGINAL, variant='japanese', render_scale=2, anisotropy=4)
    fixture_preferences=(args.preferences or output/'graphics-fixture.json').resolve()
    if not fixture_preferences.is_relative_to(ROOT/'private') or fixture_preferences.suffix!='.json':
        parser.error('QA preferences must be a private JSON file')
    bridge=settings_bridge.Bridge(output, fixture_preferences)
    controls=controller_settings.Bridge(output,output/'controller-fixture.json',output/'controller-profile.json')
    support=test_support.Support(ROOT,output,output/'memstick',profile)
    env.update(bridge.environment(profile))
    env.update(controls.environment())
    env.update(SR_AUDIOSTAT='1',SR_MPEGAV='1',LOA_MOVIE_TIMING='1',SR_PERF='1')
    env['LOA_SETTINGS_TRACE']='1'
    if args.online:
        from room_service import Rooms,Server
        import network_settings,online_session
        server=Server(('127.0.0.1',0),Rooms());thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        stack.callback(server.server_close);stack.callback(server.shutdown)
        identity=dict(network_settings.defaults(),mac='02:00:00:00:00:01')
        env.update(network_settings.environment(identity))
        session=online_session.Session(output,identity,service=f'http://127.0.0.1:{server.server_port}')
        env.update(stack.enter_context(session))
    if args.steam:
        import network_settings,online_session
        identity=dict(network_settings.defaults(),mac='02:48:00:00:00:01');env.update(network_settings.environment(identity))
        session=online_session.Session(output,identity,service='',backend='rooms',preferences=output/'online-fixture.json');env.update(stack.enter_context(session))
    title.verify_disc_image(Path(env['PSP_ISO']), 'japanese')
    build = title.build_directory('release')
    command = [str(build/'lordofapocalypse.exe'), '--image', str(build/'lordofapocalypse_image.bin'),
               f"{title.CONFIG['module']['base']:08x}", f"{title.CONFIG['module']['entry']:08x}",
               str(ROOT/'private/oracle-prefix/entry-prefix.trace'), 'none', '--sched', '--gui']
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.PostMessageW.argtypes = (w.HWND, w.UINT, w.WPARAM, w.LPARAM)
    user.GetWindowThreadProcessId.argtypes = (w.HWND, ctypes.POINTER(w.DWORD))
    user.GetClassNameW.argtypes = (w.HWND, w.LPWSTR, ctypes.c_int)
    user.SetForegroundWindow.argtypes = (w.HWND,)
    callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    user.EnumWindows.argtypes = (callback_type, w.LPARAM)
    windows = []
    log_path = output/'native.log'
    report = {'scope': 'native-window-and-pause', 'passed': False}
    with stack,log_path.open('wb') as log:
        process = subprocess.Popen(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            report['window_size'] = window_settings.apply(process.pid, (1280, 720))
            @callback_type
            def visit(window, _):
                owner = w.DWORD()
                name = ctypes.create_unicode_buffer(128)
                user.GetWindowThreadProcessId(window, ctypes.byref(owner))
                user.GetClassNameW(window, name, 128)
                if owner.value == process.pid and name.value == 'SDL_app':
                    windows.append(window)
                    return False
                return True
            user.EnumWindows(visit, 0)
            if not windows:
                raise RuntimeError('Owned SDL game window not found')
            window = windows[0]
            def key(code):
                scan = user.MapVirtualKeyW(code, 0)
                extended = (1 << 24) if code in (0x25, 0x26, 0x27, 0x28) else 0
                user.PostMessageW(window, 0x100, code, 1 | (scan << 16) | extended)
                time.sleep(0.08)
                user.PostMessageW(window, 0x101, code, 1 | (scan << 16) | extended | (3 << 30))
            def wait_for(marker, seconds=8):
                deadline = time.monotonic()+seconds
                while time.monotonic() < deadline:
                    bridge.poll()
                    controls.poll()
                    support.poll()
                    if marker in log_path.read_text(errors='replace'):
                        return
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                raise RuntimeError('Not observed: '+marker)
            def step(code):
                key(code)
                time.sleep(0.25)
                bridge.poll()
                controls.poll()
                support.poll()
            def saved(seq):
                wait_for(f'LOA_SETTINGS: saved sequence={seq}')
            user.SetForegroundWindow(window)
            time.sleep(5)
            key(0x70)  # F1, delivered only to this child process.
            wait_for('SR_PAUSE: entered')
            time.sleep(1)
            if args.controls:
                for code in (0x28,0x28,0x28,0x0d):step(code)
                wait_for('LOA_CONTROLS: focus=630')
                subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),'-Window',str(window),'-Owner',str(process.pid),'-Output',str(output/'controller-bindings.png')],check=True,timeout=10,capture_output=True)
                step(0x27);wait_for('LOA_CONTROLS: saved sequence=1 reloaded=1')
                expected=controller_settings.assign(controller_settings.defaults(),0,2)
                if controller_settings.load(output/'controller-fixture.json')!=expected:raise RuntimeError('F1 controller change was not saved')
                for _ in range(12):
                    focuses=re.findall(r'LOA_CONTROLS: focus=(\d+)',log_path.read_text(errors='replace'))
                    if focuses and focuses[-1]=='661':break
                    step(0x28)
                else:raise RuntimeError('Could not focus Restore default controller bindings')
                step(0x0d);wait_for('LOA_CONTROLS: saved sequence=2 reloaded=1')
                if controller_settings.load(output/'controller-fixture.json')!=controller_settings.defaults():raise RuntimeError('F1 defaults were not restored')
                for code in (0x28,0x28,0x28,0x28,0x0d):step(code)
                step(0x27);wait_for('LOA_CONTROLS: saved sequence=3 reloaded=1')
                step(0x28);step(0x27);wait_for('LOA_CONTROLS: saved sequence=4 reloaded=1')
                if controller_settings.load(output/'controller-fixture.json')[-2:]!=[1,3]:raise RuntimeError('F1 camera mode and speed did not persist')
                subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),'-Window',str(window),'-Owner',str(process.pid),'-Output',str(output/'camera-settings.png')],check=True,timeout=10,capture_output=True)
                step(0x1b)
                for _ in range(12):
                    focuses=re.findall(r'LOA_CONTROLS: focus=(\d+)',log_path.read_text(errors='replace'))
                    if focuses and focuses[-1]=='661':break
                    step(0x28)
                else:raise RuntimeError('Could not restore defaults after Camera settings')
                step(0x0d)
                wait_for('LOA_CONTROLS: saved sequence=5 reloaded=1')
                if controller_settings.load(output/'controller-fixture.json')!=controller_settings.defaults():raise RuntimeError('F1 did not restore camera defaults')
                report['controller_bindings']='PASS: native page, acknowledged saves, live profile reload and restored defaults'
                report['camera_settings']='PASS: experimental horizontal mode and speed persisted, then defaults restored'
                step(0x1b);step(0x26);step(0x26)
            elif args.support:
                for code in (0x28,0x28,0x28,0x28,0x0d):step(code)
                wait_for('LOA_MENU: tester support opened')
                step(0x28);step(0x0d)
                ack=output/'support-ack.json'
                if json.loads(ack.read_text()).get('sequence')!=1 or not support.markers:
                    raise RuntimeError('F1 audio marker did not reach the supervisor')
                step(0x26);step(0x0d)
                if not support.last_report or not support.last_report.is_file():
                    raise RuntimeError('F1 export did not create a diagnostic archive')
                import zipfile
                with zipfile.ZipFile(support.last_report) as archive:
                    if set(archive.namelist())!={'report.json','audio-diagnostics.json','network-diagnostics.json','TESTER-NOTES.txt'}:
                        raise RuntimeError('Unexpected diagnostic report payload')
                report['tester_support']='PASS: actual F1 audio marker and local ZIP export'
                subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                    '-Window',str(window),'-Owner',str(process.pid),'-Output',str(output/'tester-support.png')],
                    check=True,timeout=10,capture_output=True)
                step(0x1b)
                for code in (0x26,0x26,0x26):step(code)
            elif args.network:
                for name in ('pause-menu','networking'):
                    if name=='networking':
                        for code in (0x28,0x28,0x0d):step(code)
                        wait_for('LOA_MENU: networking opened')
                        if args.steam:
                            # Exercise the same live provider switch used by a normal launch.
                            for _ in range(15):
                                focuses=re.findall(r'LOA_NETWORK: focus=(\d+)',log_path.read_text(errors='replace'))
                                focus=int(focuses[-1]) if focuses else 0
                                if focus==461:break
                                step(0x25 if focus==462 else 0x26)
                            else:raise RuntimeError('Could not focus the Steam provider button.')
                            step(0x0d);time.sleep(.5)
                            status=session.client.call('status')
                            if status['backend']!='steam':raise RuntimeError('F1 did not switch to Steam.')
                            if not status['service_configured']:raise RuntimeError(status['error'])
                            import online_config
                            if online_config.load(output/'online-fixture.json')['backend']!='steam':raise RuntimeError('Provider selection did not persist.')
                            report['steam_provider_saved']='PASS: switched live through F1 and saved in isolated profile'
                            step(0x28) # Host Steam lobby below the provider row.
                            step(0x0d)
                            deadline=time.monotonic()+30
                            while time.monotonic()<deadline:
                                status=session.client.call('status')
                                if status['lobby']:break
                                if status['state']=='error':raise RuntimeError(status['error'])
                                time.sleep(.05)
                            else:raise RuntimeError('F1 did not create a real Steam lobby.')
                            if status['players']!=1 or status['connected']!=0:raise RuntimeError('Unexpected membership in the single-account Steam check.')
                            report['steam_lobby']='Actual App ID 480 lobby created through F1, one local member, zero confirmed peers; not a multiplayer mission'
                            report['steam_overlay_available']=status['overlay_available'];time.sleep(.8)
                        if args.online:
                            step(0x0d) # Create room is the default enabled action.
                            deadline=time.monotonic()+8
                            while time.monotonic()<deadline:
                                status=session.client.call('status')
                                if status['code']:break
                                time.sleep(.05)
                            else:raise RuntimeError('F1 Create Room did not obtain a server-issued code.')
                            peer_folder=output/'peer';peer_folder.mkdir()
                            peer=online_session.Session(peer_folder,dict(mac='02:00:00:00:00:02',nickname='Peer'),service=f'http://127.0.0.1:{server.server_port}')
                            stack.enter_context(peer)
                            assert peer.client.call('join',code=status['code'])['result']==0
                            deadline=time.monotonic()+12
                            while time.monotonic()<deadline:
                                status=session.client.call('status')
                                if status['connected']==1:break
                                time.sleep(.05)
                            else:raise RuntimeError('The real native peer did not connect to the F1-created room.')
                            report['online_room']='Server-issued code created through F1; independent native WebRTC peer joined; direct connection confirmed'
                            time.sleep(.8)
                    subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                                    '-Window',str(window),'-Owner',str(process.pid),'-Output',str(output/(name+'.png'))],
                                   check=True,timeout=10,capture_output=True)
                if args.steam:
                    # The current room card focuses Back after Create disappears.
                    # Up selects Leave Lobby. Confirm must leave the real room.
                    step(0x26);step(0x0d)
                    deadline=time.monotonic()+5
                    while time.monotonic()<deadline:
                        if not session.client.call('status')['lobby']:break
                        time.sleep(.05)
                    else:raise RuntimeError('F1 Leave Lobby did not leave the actual Steam lobby.')
                    report['steam_leave']='PASS: left through F1'
                step(0x1b)  # Back restores focus to Networking.
                step(0x26)  # Settings above Networking.
                report['network_page']='Opened from F1 and returned to Settings; no public internet game mission tested'
            else:
                key(0x28)  # Settings below Resume.
            time.sleep(0.4)
            key(0x0d)
            time.sleep(1)
            key(0x28)  # From the selected Display tab to internal resolution.
            time.sleep(0.3)
            key(0x27)
            wait_for('LOA_SETTINGS: saved sequence=1')
            actual=graphics_settings.load(fixture_preferences)
            if actual['render_scale'] != 3:
                raise RuntimeError('Internal resolution change was not persisted as 3x')
            if args.fps:
                if args.restart:raise ValueError('Use a separate FPS control check')
                for code in (0x28,0x28,0x28,0x28,0x27):step(code)
                saved(2)
                if graphics_settings.load(fixture_preferences)['gameplay_fps']!=60:
                    raise RuntimeError('60 FPS choice did not persist')
                subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                                '-Window',str(window),'-Owner',str(process.pid),'-Output',str(output/'fps-settings.png')],
                               check=True,timeout=10,capture_output=True)
                step(0x25);saved(3)
                actual=graphics_settings.load(fixture_preferences)
                if actual['gameplay_fps']!=30:raise RuntimeError('30 FPS choice did not persist')
                report['gameplay_fps_control']='PASS: 30 -> 60 -> 30; normal preferences untouched'
            if args.restart:
                step(0x28)  # Image scaling, live.
                step(0x27)
                saved(2)
                if graphics_settings.load(fixture_preferences)['scaling'] != 'integer':
                    raise RuntimeError('Live image scaling did not persist')
                # Return to the Graphics tab, select Advanced, then change shimmer.
                # Spatial Up lands on the rightmost tab above a full-width row.
                for code in (0x26,0x26,0x25,0x25,0x25,0x27,0x27,0x0d,0x28,0x27):
                    step(code)
                saved(3)
                if not graphics_settings.load(fixture_preferences)['mipmaps']:
                    raise RuntimeError('Advanced mipmap setting did not persist')
                for code in (0x28,0x28,0x28,0x27):
                    step(code)
                saved(4)
                report['texture_scale_saved']=graphics_settings.load(fixture_preferences)['texture_scale']
                if report['texture_scale_saved'] != 2:
                    raise RuntimeError('Texture smoothing setting did not persist')
                for code in (0x28,0x27):
                    step(code)
                saved(5)
                report['hd_ui_saved']=graphics_settings.load(fixture_preferences)['hd_ui']
                if not report['hd_ui_saved']:
                    raise RuntimeError('HD English UI setting did not persist')
                subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                                '-Window',str(window),'-Owner',str(process.pid),'-Output',str(output/'texture-settings.png')],
                               check=True,timeout=10,capture_output=True)
                for code in (0x26,0x26,0x26,0x26):
                    step(code)
                # Advanced tab -> Language -> Japanese -> WIP.
                for code in (0x26,0x25,0x25,0x25,0x27,0x27,0x27,0x0d,0x28,0x25):
                    step(code)
                saved(6)
                if graphics_settings.load(fixture_preferences)['variant'] != 'english-text-test':
                    raise RuntimeError('WIP language selection did not persist')
                # Balanced preset keeps the selected language.
                for code in (0x28,0x28,0x0d):
                    step(code)
                saved(7)
                actual=graphics_settings.load(fixture_preferences)
                if actual['render_scale'] != 2 or actual['anisotropy'] != 4 or actual['variant'] != 'english-text-test' or actual['texture_scale'] != 1 or actual['hd_ui']:
                    raise RuntimeError('Balanced preset or language preservation failed')
                for code in (0x28,0x0d):
                    step(code)
                saved(8)
                quality=graphics_settings.load(fixture_preferences)
                if any(quality[key]!=value for key,value in graphics_settings.QUALITY.items()) or quality['variant']!='english-text-test':
                    raise RuntimeError('High Quality preset or language preservation failed')
                report['quality_preset']='PASS'
                subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                                '-Window',str(window),'-Owner',str(process.pid),'-Output',str(output/'quality-preset.png')],
                               check=True,timeout=10,capture_output=True)
                for code in (0x26,0x0d):
                    step(code)
                saved(9)
                actual=graphics_settings.load(fixture_preferences)
            subprocess.run(['powershell', '-NoProfile', '-File', str(ROOT/'tools/capture-owned-window.ps1'),
                            '-Window', str(window), '-Owner', str(process.pid), '-Output', str(output/'in-game-settings.png')],
                           check=True, timeout=10, capture_output=True)
            if 'SR_PAUSE: resumed' in log_path.read_text(errors='replace'):
                raise RuntimeError('Navigation resumed the game before Settings could be inspected')
            if args.restart:
                # Balanced -> Quality -> logs -> restart. Confirmation is separate.
                for code in (0x28,0x28,0x28,0x0d):
                    step(code)
                if 'LOA_SETTINGS: restart confirmed' in log_path.read_text(errors='replace'):
                    raise RuntimeError('Restart occurred without a separate confirmation')
                step(0x0d)
                wait_for('LOA_SETTINGS: restart confirmed')
            else:
                key(0x1b)
                time.sleep(0.4)
                key(0x1b)
                wait_for('SR_PAUSE: resumed')
                user.PostMessageW(window, 0x10, 0, 0)
            report['returncode'] = process.wait(timeout=10)
            support.finish()
            if support.last_report:
                # Move this owned tiny QA report into its evidence folder.
                support.last_report.replace(output/'exported-report.zip')
            text = log_path.read_text(errors='replace')
            report['pause_events'] = [line for line in text.splitlines() if 'SR_PAUSE:' in line]
            report['overlay_failure'] = any(marker in text for marker in ('overlay pages are unavailable', 'could not be drawn'))
            report['saved_internal_resolution'] = actual['render_scale']
            if args.restart:
                report['restart_variant'] = bridge.restart_after_exit(report['returncode'])
                if report['restart_variant'] != 'english-text-test':
                    raise RuntimeError('Confirmed clean exit did not select WIP English')
                followup=output/'restarted'
                followup.mkdir()
                candidate=graphics_settings.WIP_FOLDER/'LordOfApocalypse-English-WIP.iso'
                from translation_candidate import verify
                verify(candidate,candidate.parent/'result.json')
                env.update(graphics_settings.environment(actual))
                env.update(PSP_ISO=str(candidate), SR_EXIT_AT_VBLANK='500', SR_DETERMINISTIC_CLOCK='1', SR_NOVBPACE='1')
                with (followup/'native.log').open('wb') as followup_log:
                    run=subprocess.run(command,cwd=followup,env=env,stdout=followup_log,stderr=subprocess.STDOUT,timeout=25)
                report['restarted_returncode']=run.returncode
                if run.returncode != 0 or 'gegpu: render scale 2x' not in (followup/'native.log').read_text(errors='replace'):
                    raise RuntimeError('Restarted WIP game did not initialize the saved Balanced settings')
            report['passed'] = report['window_size']['applied'] and not report['overlay_failure'] and report['returncode'] == 0
        except Exception as error:
            report['error'] = str(error)
            if windows and process.poll() is None:
                subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),
                                '-Window',str(windows[0]),'-Owner',str(process.pid),'-Output',str(output/'failure.png')],
                               timeout=10,capture_output=True)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    report['save_source_unchanged'] = before == save_storage.tree_hashes(fixture)
    report['preferences_unchanged'] = original == (preferences.read_bytes() if preferences.exists() else None)
    report['passed'] = report['passed'] and report['save_source_unchanged'] and report['preferences_unchanged']
    (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
