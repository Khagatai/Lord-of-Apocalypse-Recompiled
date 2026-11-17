"""Explicitly hosted LAN lobby; PSP game packets travel directly between players.

Implements the PRO ad-hoc lobby wire format documented by the pinned framework
nk_adhoc_relay.h. No game files, public server discovery, UPnP or telemetry.
"""
import argparse,ipaddress,json,os,secrets,selectors,socket,time
from pathlib import Path

class Client:
    def __init__(self,sock,address):
        self.sock=sock;self.address=address;self.input=bytearray();self.output=bytearray()
        self.mac=None;self.product=None;self.nickname=None;self.group=None;self.last=time.monotonic();self.wire_ip=address[0]

class Lobby:
    def __init__(self,listen='127.0.0.1',port=27312,advertise_host=None):
        ipaddress.IPv4Address(listen)
        if advertise_host:ipaddress.IPv4Address(advertise_host)
        self.advertise_host=advertise_host
        self.selector=selectors.DefaultSelector();self.clients={};self.groups={};self.closed=False
        self.socket=socket.socket();self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.socket.bind((listen,port));self.socket.listen(8);self.socket.setblocking(False)
        self.selector.register(self.socket,selectors.EVENT_READ,None);self.address=self.socket.getsockname()

    def send(self,client,data):
        if len(client.output)+len(data)>65536:self.drop(client);return
        client.output.extend(data)
        self.selector.modify(client.sock,selectors.EVENT_READ|selectors.EVENT_WRITE,client)

    def leave(self,client):
        if client.group is None:return
        key=client.group;group=self.groups[key];group['members'].remove(client)
        for other in tuple(group['members']):self.send(other,b'\x03'+socket.inet_aton(client.wire_ip))
        if not group['members']:del self.groups[key]
        client.group=None

    def drop(self,client):
        if client.sock not in self.clients:return
        self.leave(client);self.clients.pop(client.sock,None)
        self.selector.unregister(client.sock);client.sock.close()

    def process(self,client,packet):
        opcode=packet[0]
        if opcode==0:return
        if opcode==1:
            mac,nick,product=packet[1:7],packet[7:135],packet[135:144]
            if (client.mac is not None or mac in (b'\0'*6,b'\xff'*6) or not nick[0] or
                any(not (65<=c<=90 or 48<=c<=57) for c in product) or
                any(c.mac==mac or c.wire_ip==client.wire_ip for c in self.clients.values() if c is not client and c.mac)):
                self.drop(client);return
            client.mac,client.nickname,client.product=mac,nick,product;return
        if client.mac is None:self.drop(client);return
        if opcode==2:
            group=packet[1:9];text=group.split(b'\0',1)[0]
            if client.group is not None or any(not (48<=c<=57 or 65<=c<=90 or 97<=c<=122) for c in text):self.drop(client);return
            key=client.product,group
            if key not in self.groups:
                bssid=bytearray(secrets.token_bytes(6));bssid[0]=(bssid[0]|2)&254
                self.groups[key]=dict(bssid=bytes(bssid),members=[])
            entry=self.groups[key]
            if len(entry['members'])>=4:self.drop(client);return
            for other in reversed(tuple(entry['members'])):
                self.send(other,b'\x02'+client.nickname+client.mac+socket.inet_aton(client.wire_ip))
                self.send(client,b'\x02'+other.nickname+other.mac+socket.inet_aton(other.wire_ip))
            client.group=key;entry['members'].append(client)
            self.send(client,b'\x06'+entry['bssid']);return
        if opcode==3:self.leave(client);return
        if opcode==4:
            if client.group is not None:self.drop(client);return
            for (product,name),entry in reversed(tuple(self.groups.items())):
                if product==client.product:self.send(client,b'\x04'+name+entry['bssid'])
            self.send(client,b'\x05');return
        self.drop(client)

    def step(self,timeout=.05):
        for key,events in self.selector.select(timeout):
            client=key.data
            try:
                if client is None:
                    sock,address=self.socket.accept();sock.setblocking(False)
                    if len(self.clients)>=16:sock.close();continue
                    client=Client(sock,address);self.clients[sock]=client
                    if self.advertise_host and ipaddress.IPv4Address(address[0]).is_loopback:client.wire_ip=self.advertise_host
                    self.selector.register(sock,selectors.EVENT_READ,client);continue
                if events&selectors.EVENT_READ:
                    data=client.sock.recv(4096)
                    if not data:self.drop(client);continue
                    client.last=time.monotonic();client.input.extend(data)
                    if len(client.input)>8192:self.drop(client);continue
                    while client.input and client.sock in self.clients:
                        size={0:1,1:144,2:9,3:1,4:1}.get(client.input[0])
                        if size is None:self.drop(client);break
                        if len(client.input)<size:break
                        packet=bytes(client.input[:size]);del client.input[:size];self.process(client,packet)
                if events&selectors.EVENT_WRITE and client.sock in self.clients:
                    count=client.sock.send(client.output);del client.output[:count]
                    if not client.output:self.selector.modify(client.sock,selectors.EVENT_READ,client)
            except (OSError,ValueError):
                if client is not None:self.drop(client)
        now=time.monotonic()
        for client in tuple(self.clients.values()):
            if now-client.last>30:self.drop(client)

    def close(self):
        if self.closed:return
        for client in tuple(self.clients.values()):self.drop(client)
        self.selector.unregister(self.socket);self.socket.close();self.selector.close();self.closed=True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--listen',default='127.0.0.1',help='Explicit local IPv4 interface; 0.0.0.0 permits LAN clients')
    parser.add_argument('--port',type=int,default=27312)
    parser.add_argument('--advertise-host',help='Host player public IPv4; applied to loopback clients only')
    parser.add_argument('--ready-file',type=Path,help='Private launcher readiness file')
    parser.add_argument('--stop-file',type=Path,help='Private owned-test shutdown marker')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Invalid port')
    lobby=Lobby(args.listen,args.port,args.advertise_host);print('LOA co-op lobby listening on %s:%d'%lobby.address,flush=True)
    if args.ready_file:
        ready=args.ready_file.resolve();private=Path(__file__).resolve().parents[1]/'private'
        if not ready.is_relative_to(private):raise ValueError('Readiness file must remain private')
        ready.write_text(json.dumps(dict(pid=os.getpid(),address=lobby.address))+'\n')
    stop=args.stop_file.resolve() if args.stop_file else None
    if stop and not stop.is_relative_to(Path(__file__).resolve().parents[1]/'private'):raise ValueError('Stop marker must remain private')
    try:
        while stop is None or not stop.exists():lobby.step()
    except KeyboardInterrupt:pass
    finally:lobby.close()
if __name__=='__main__':main()
