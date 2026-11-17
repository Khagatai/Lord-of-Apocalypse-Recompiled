"""Two independent native-WebRTC room clients; local service, synthetic packets only."""
import argparse,base64,contextlib,json,os,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from room_service import Rooms,Server
from online_session import Session
ROOT=Path(__file__).resolve().parents[1]
def wait(predicate,seconds=20):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=predicate()
        if result:return result
        time.sleep(.03)
    raise TimeoutError('Online checkpoint did not complete.')
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--relay',action='store_true');parser.add_argument('--local-relay',action='store_true');args=parser.parse_args()
    if args.local_relay:args.relay=True
    folder=ROOT/('private/online-relay-check' if args.relay else 'private/online-check');folder.mkdir(exist_ok=True)
    stack=contextlib.ExitStack()
    ice=[]
    if args.local_relay:
        from online_turn_fixture import local_turn
        ice=[stack.enter_context(local_turn(folder))]
    elif args.relay:
        url=os.environ.get('LOA_TEST_TURN_URL');username=os.environ.get('LOA_TEST_TURN_USER');password=os.environ.get('LOA_TEST_TURN_PASSWORD')
        if not all((url,username,password)):raise ValueError('Forced-relay test requires an explicit owned TURN fixture.')
        ice=[dict(url=url,username=username,password=password)]
    server=Server(('127.0.0.1',0),Rooms(ice=ice));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    report=dict(scope='two-independent-native-WebRTC-processes-local-room-service-not-gameplay',passed=False,gameplay_validated=False,relay_required=args.relay)
    try:
        url=f'http://127.0.0.1:{server.server_port}'
        a=folder/'a';b=folder/'b';a.mkdir(exist_ok=True);b.mkdir(exist_ok=True)
        host=Session(a,dict(mac='02:01:02:03:04:01',nickname='Host'),service=url,relay=args.relay)
        join=Session(b,dict(mac='02:01:02:03:04:02',nickname='Join'),service=url,relay=args.relay)
        with host,join:
            x=host.client;y=join.client
            assert x.call('create')['result']==0
            code=wait(lambda:x.call('status')['code']);assert len(code)==5 and code.isdigit()
            assert y.call('join',code=code)['result']==0
            wait(lambda:y.call('status')['code']==code)
            wait(lambda:x.call('status')['connected']==1 and y.call('status')['connected']==1)
            report['host_path']=x.call('status')['paths'];report['join_path']=y.call('status')['paths']
            if args.relay:assert 'relayed' in report['host_path']+report['join_path']
            assert x.call('login',mac='020102030401',product='NPJH50503')['result']==0
            assert y.call('login',mac='020102030402',product='NPJH50503')['result']==0
            assert x.call('group',group='LOATEST')['result']==0
            assert y.call('group',group='LOATEST')['result']==0
            seen=[[],[]]
            def discovered():
                for i,client in enumerate((x,y)):seen[i].extend(client.call('events',max=8).get('events',[]))
                return all(any(e['kind']==2 for e in events) and any(e['kind']==6 for e in events) for events in seen)
            wait(discovered);report['lobby']='real peer and BSSID events'
            p=x.call('pdp_open',port=31001)['result'];q=y.call('pdp_open',port=31002)['result'];assert p>=0 and q>=0
            payload=bytes(i%251 for i in range(8192))
            assert x.call('pdp_send',handle=p,mac='020102030402',port=31002,data=base64.b64encode(payload).decode())['result']==0
            short=wait(lambda:(r if (r:=y.call('pdp_recv',handle=q,capacity=1))['result']!=-1 else None));assert short==dict(result=-9,size=len(payload))
            received=y.call('pdp_recv',handle=q,capacity=10000);assert received['result']==0 and base64.b64decode(received['data'])==payload and received['port']==31001 and received['mac']=='020102030401'
            report['pdp']='8192-byte native encrypted unreliable channel; MAC/port and short-buffer retention'
            listener=x.call('ptp_open',port=32001,remote=0,backlog=4,mac='000000000000')['result']
            client=y.call('ptp_open',port=32002,remote=32001,backlog=0,mac='020102030401')['result'];assert listener>=0 and client>=0
            assert y.call('ptp_connect',handle=client)['result']==-1
            accepted=wait(lambda:(r if (r:=x.call('ptp_accept',handle=listener))['result']>=0 else None))['result']
            wait(lambda:y.call('ptp_connect',handle=client)['result']==0)
            assert y.call('ptp_send',handle=client,data=base64.b64encode(payload).decode())==dict(result=0,size=len(payload))
            first=wait(lambda:(r if (r:=x.call('ptp_recv',handle=accepted,capacity=3))['result']==0 else None))
            rest=x.call('ptp_recv',handle=accepted,capacity=20000);assert base64.b64decode(first['data'])+base64.b64decode(rest['data'])==payload
            assert x.call('ptp_send',handle=accepted,data=base64.b64encode(b'reply').decode())['result']==0
            reply=wait(lambda:(r if (r:=y.call('ptp_recv',handle=client,capacity=50))['result']==0 else None));assert base64.b64decode(reply['data'])==b'reply'
            report['ptp']='native reliable ordered channel; accept acknowledgement, partial stream reads and bidirectional reply'
            for c,h in ((x,accepted),(x,listener),(y,client)):assert c.call('ptp_close',handle=h)['result']==0
            wait(lambda:not x.call('status')['state'] in ('creating','joining'))
            def left():return x.call('leave')['result']==0
            wait(left);wait(lambda:y.call('status')['state']=='offline')
            report['cleanup']='host leave closes room on guest';report['passed']=True
    except Exception as error:report['error']=str(error);raise
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
        stack.close()
        (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
