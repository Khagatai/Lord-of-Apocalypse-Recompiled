"""Real single-account Steam test. No invitations, game files or fake peers."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from online_session import Session
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--host',action='store_true');args=parser.parse_args()
    folder=ROOT/'private/steam-connection-check';folder.mkdir(exist_ok=True)
    report=dict(scope='single-real-Steam-account-AppID480-not-two-player-gameplay',passed=False,gameplay_validated=False,peer_connection_validated=False)
    try:
        with Session(folder,dict(mac='02:48:00:00:00:01',nickname='Steam test'),service='',backend='steam') as env:
            # Keep the local token and Steam account identifiers out of stdout.
            from online_session import Client
            client=Client(dict(port=int(env['LOA_ONLINE_PORT']),token=env['LOA_ONLINE_TOKEN']))
            try:
                status=client.call('status');report['steam_initialized']=status['service_configured'];report['error']=status.get('error','')
                if not report['steam_initialized']:raise RuntimeError(report['error'])
                if args.host:
                    result=client.call('create')
                    if result['result']!=0:raise RuntimeError(result.get('error','Steam rejected creation.'))
                    deadline=time.monotonic()+30
                    while time.monotonic()<deadline:
                        status=client.call('status')
                        if status['lobby']:break
                        if status['state']=='error':raise RuntimeError(status['error'])
                        time.sleep(.05)
                    else:raise TimeoutError('Steam lobby creation timed out.')
                    report['real_lobby_created']=True;report['members']=status['players'];report['connected_peers']=status['connected']
                    if status['players']!=1 or status['connected']!=0:raise RuntimeError('Unexpected membership for the owned single-account test.')
                    client.call('refresh');time.sleep(.5);client.call('leave');report['left_lobby']=not client.call('status')['lobby']
                report['passed']=True
            finally:client.close()
    except Exception as error:report['error']=str(error)
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
