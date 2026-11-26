/* SPDX-License-Identifier: GPL-3.0-or-later
* Title-owned experimental ad-hoc HLE, written with Codex. PSP ABI/constants
* checked against the locally pinned PPSSPP and PSP measurements documented in
* pinned hle_network.c. Opt-in only; unsupported calls retain their real errors.
* Network traffic is lobby metadata and explicit guest PDP packets, never files. */
#include "hle_internal.h"
#include "coop_transport.h"
#include "coop_service_wait.h"
#define NETERR(n) (0x80410700u+(n))
#define CTLERR(n) (0x80410b00u+(n))
#define MATCHERR(n) (0x80410800u+(n))
#define MAX_PEERS 3
#define MAX_MATCH_PEERS 15
#define MAX_MATCH 4
#define MAX_OPTION 8192
typedef struct  {
    uint8_t mac[6];
    char nickname[129];
    uint32_t id;
}
Peer;
typedef struct  {
    uint32_t fn,arg,gp;
}
Handler;
typedef struct  {
    int used,transport;
    uint32_t capacity;
}
Pdp;
typedef struct  {
    uint32_t kind,len;
    uint8_t mac[6],data[MAX_OPTION];
}
MatchEvent;
typedef struct  {
    int state;
    uint8_t mac[6];
    uint16_t port;
    uint64_t seen;
    uint32_t pending_seq,pending_len;
    uint8_t pending[MAX_OPTION];
    uint64_t retry_at;
    unsigned retries;
    uint8_t control_op,control[MAX_OPTION];
    uint32_t control_seq,control_len;
    uint64_t control_at;
    unsigned control_retries;
}
MatchPeer;
typedef struct  {
    int used,running,mode,max,transport;
    uint16_t port;
    uint32_t fn,gp,scratch_uid,scratch,thread,generation;
    uint32_t hello_interval,keepalive_interval,retry_interval,retry_count,sequence,hello_len;
    uint8_t hello[MAX_OPTION];
    uint64_t hello_due,ping_due,timeout,parent_first_at;
    uint8_t parent[6];
    MatchPeer peers[MAX_MATCH_PEERS];
    MatchEvent events[16];
    unsigned event_n;
}
Matching;
static struct  {
    int configured,enabled,adhoc,ctl,matching,state,pending;
    uint32_t thread,callback_thread,generation;
    struct {int kind;uint32_t error;} ctl_events[16];
    unsigned ctl_event_n;
    uint64_t disconnect_due;
    uint8_t mac[6],product[13],group[8],bssid[6];
    char nickname[129];
    NkAdhocTransport *transport;
    Peer peers[MAX_PEERS];
    unsigned peer_n;
    NkLobbyEvent scans[16];
    unsigned scan_n;
    Handler handlers[4];
    Pdp pdp[16];
    Matching contexts[MAX_MATCH];
    uint32_t matching_pool,matching_base,matching_size,discover_param;
    int discover_status;
    uint64_t discover_deadline;
}
net;
void __real_sr_hle_register(uint32_t,const char *,HleFn);
static int ready(void) {
    if(net.configured)return net.enabled;
    net.configured=1;
    const char *enabled=getenv("LOA_NET_ENABLED");
    if(!enabled || strcmp(enabled,"1"))return 0;
    const char *mac=getenv("LOA_NET_MAC"),*nick=getenv("LOA_NET_NICKNAME");
    unsigned m[6];
    if(!mac || sscanf(mac,"%2x:%2x:%2x:%2x:%2x:%2x",m,m+1,m+2,m+3,m+4,m+5)!=6 || !nick || !*nick) {
        fprintf(stderr,"LOA_NET: invalid explicit identity; networking remains disabled\n");
        return 0;
    }
    for(int i=0;i<6;i++)net.mac[i]=(uint8_t)m[i];
    if(!nk_relay_mac_ok(net.mac) || (net.mac[0]&1)) {
        fprintf(stderr,"LOA_NET: invalid unicast MAC\n");
        return 0;
    }
    snprintf(net.nickname,sizeof net.nickname,"%s",nick);
    net.enabled=1;
    fprintf(stderr,"LOA_NET: experimental native peer-to-peer networking enabled; game co-op not yet accepted\n");
    return 1;
}
static uint32_t arg(CpuState *s,unsigned n) {
    return n<8?s->r[4+n]:MEM_R32(s->r[29]+4*(n-8));
}
static int read_bytes(uint32_t address,void *out,uint32_t bytes) {
    if(!address||!sr_guest_span_readable(address,bytes))return 0;
    for(uint32_t i=0;i<bytes;i++)((uint8_t *)out)[i]=MEM_R8(address+i);
    return 1;
}
static void write_bytes(uint32_t address,const void *in,uint32_t bytes) {
    for(uint32_t i=0;i<bytes;i++)MEM_W8(address+i,((const uint8_t *)in)[i]);
}
static void zero_bytes(uint32_t address,uint32_t bytes) {
    for(uint32_t i=0;i<bytes;i++)MEM_W8(address+i,0);
}
static uint32_t transport_error(int error) {
    switch(error) {
        case NK_NET_OK:return 0;
        case NK_NET_AGAIN:return NETERR(9);
        case NK_NET_NO_SOCKET:return NETERR(1);
        case NK_NET_PORT_IN_USE:return NETERR(10);
        case NK_NET_TOO_BIG:return NETERR(5);
        case NK_NET_NO_SLOT:return NETERR(15);
        case NK_NET_NOT_LOGGED_IN:return NETERR(12);
        case NK_NET_NOT_IN_GROUP:return NETERR(11);
        case NK_NET_SHORT_BUFFER:return 0x80400706u;
        default:return NETERR(17);
    }
}
static void call(CpuState *s,uint32_t fn,uint32_t gp,uint32_t sp,const char *owner) {
    s->r[28]=gp;
    s->r[29]=sp;
    s->r[31]=SR_HOST_RETURN_PC;
    s->pc=fn;
    uint32_t fatal=0;
    if(hle_dispatch_guest_scoped(s,fn,owner,&fatal)) {
        fprintf(stderr,"SEMANTIC_BOUNDARY: native networking callback failed at %08x (%s)\n",fatal,owner);
        fflush(stderr);
        exit(1);
    }
}
static void ctl_event(CpuState *s,int event,uint32_t error) {
    uint32_t sp=s->r[29],generation=net.generation;
    for(unsigned i=0;i<4;i++) {
        if(!net.ctl || generation!=net.generation)return;
        Handler h=net.handlers[i];
        if(!h.fn)continue;
        s->r[4]=event;
        s->r[5]=error;
        s->r[6]=h.arg;
        call(s,h.fn,h.gp,sp,"LOA native adhocctl");
    }
}
static Matching *matching(uint32_t id) {
    return id>=1 && id<=MAX_MATCH && net.contexts[id-1].used?&net.contexts[id-1]:NULL;
}
static void matching_poll(CpuState *,Matching *);
static void ctl_queue(int kind,uint32_t error) {
    if(net.ctl_event_n>=16) {
        fprintf(stderr,"SEMANTIC_BOUNDARY: native adhocctl event queue overflow\n");exit(1);
    }
    net.ctl_events[net.ctl_event_n].kind=kind;
    net.ctl_events[net.ctl_event_n++].error=error;
    if(net.callback_thread)sched_service_kick(net.callback_thread);
}
static void ctl_callbacks(CpuState *s,void *opaque) {
    uint32_t generation=(uint32_t)(uintptr_t)opaque;
    while(net.ctl && generation==net.generation) {
        while(net.ctl_event_n && net.ctl && generation==net.generation) {
            int kind=net.ctl_events[0].kind;uint32_t error=net.ctl_events[0].error;
            memmove(net.ctl_events,net.ctl_events+1,(--net.ctl_event_n)*sizeof net.ctl_events[0]);
            ctl_event(s,kind,error);
        }
        if(net.ctl && generation==net.generation)sched_service_wait(UINT64_MAX);
    }
}
static void ctl_thread(CpuState *s,void *opaque) {
    uint32_t generation=(uint32_t)(uintptr_t)opaque;
    while(net.ctl && generation==net.generation) {
        NkLobbyEvent events[8];
        size_t count=0;
        if(!loa_coop_poll(events,8,&count)) {
            net.state=0;
            net.pending=0;
            net.peer_n=0;
            ctl_queue(0,CTLERR(9));
            for(unsigned i=0;i<MAX_MATCH;i++)if(net.contexts[i].used && net.contexts[i].running)
                matching_poll(s,&net.contexts[i]);
            net.thread=0;
            return;
        }
        for(size_t i=0;i<count;i++) {
            if(!net.ctl || generation!=net.generation)return;
            NkLobbyEvent *e=&events[i];
            if(e->kind==NK_LOBBY_CONNECT) {
                unsigned n;
                for(n=0;n<net.peer_n;n++)if(net.peers[n].id==e->peer_id)break;
                if(n>=MAX_PEERS) {
                    ctl_queue(0,NETERR(15));
                    continue;
                }
                memcpy(net.peers[n].mac,e->mac,6);
                memcpy(net.peers[n].nickname,e->nickname,129);
                net.peers[n].id=e->peer_id;
                if(n==net.peer_n)net.peer_n++;
                fprintf(stderr,"LOA_NET: peer joined (%u peers)\n",net.peer_n);
            }
            else if(e->kind==NK_LOBBY_DISCONNECT) {
                for(unsigned n=0;n<net.peer_n;n++)if(net.peers[n].id==e->peer_id) {
                    net.peers[n]=net.peers[--net.peer_n];
                    break;
                }
                fprintf(stderr,"LOA_NET: peer left (%u peers)\n",net.peer_n);
            }
            else if(e->kind==NK_LOBBY_CONNECT_BSSID) {
                memcpy(net.bssid,e->bssid,6);
                net.state=1;
                net.pending=0;
                ctl_queue(1,0);
            }
            else if(e->kind==NK_LOBBY_SCAN && net.scan_n<16)net.scans[net.scan_n++]=*e;
            else if(e->kind==NK_LOBBY_SCAN_COMPLETE) {
                net.state=0;
                net.pending=0;
                ctl_queue(3,0);
            }
        }
        if(!net.ctl || generation!=net.generation)return;
        if(net.disconnect_due && sched_vtime_us()>=net.disconnect_due) {
            net.disconnect_due=0;
            net.state=0;
            net.pending=0;
            ctl_queue(2,0);
        }
        /* Host IPC polls at low priority. Guest callbacks are separate workers
         * at the requested priorities, parked until real events are queued. */
        for(unsigned i=0;i<MAX_MATCH;i++)if(net.contexts[i].used && net.contexts[i].running)
            matching_poll(s,&net.contexts[i]);
        loa_coop_service_wait(2000);
    }
}
static uint32_t wlan_mac(CpuState *s) {
    if(!A0||!sr_guest_span_writable(A0,6))return SCE_KERNEL_ERROR_ILLEGAL_ADDR;
    write_bytes(A0,net.mac,6);
    return 0;
}
static uint32_t adhoc_init(CpuState *s) {
    (void)s;
    if(net.adhoc)return NETERR(19);
    net.adhoc=1;
    return 0;
}
static uint32_t adhoc_term(CpuState *s) {
    (void)s;
    for(unsigned i=0;i<16;i++)if(net.pdp[i].used && net.transport) {
        net.transport->ops->pdp_close(net.transport,net.pdp[i].transport);
        net.pdp[i].used=0;
    }
    for(unsigned i=0;i<16;i++)loa_coop_ptp_close((int)i);
    net.adhoc=0;
    return 0;
}
static uint32_t ctl_init(CpuState *s) {
    if(net.ctl)return CTLERR(7);
    if(A0<0xc00)return CTLERR(19);
    if(!read_bytes(A2,net.product,13))return CTLERR(4);
    if(MEM_R32(A2)==3)return CTLERR(4);
    const char *host=getenv("LOA_NET_HOST"),*bind=getenv("LOA_NET_BIND"),*port=getenv("LOA_NET_PORT"),*offset=getenv("LOA_NET_OFFSET");
    net.transport=loa_coop_transport(host?host:"127.0.0.1",port?(unsigned)strtoul(port,NULL,10):27312,bind?bind:"0.0.0.0",offset?(unsigned)strtoul(offset,NULL,10):10000);
    if(!net.transport)return CTLERR(4);
    char product[10];
    memcpy(product,net.product+4,9);
    product[9]=0;
    if(net.transport->ops->login(net.transport,net.mac,net.nickname,product)) {
        loa_coop_transport_close();
        net.transport=NULL;
        return CTLERR(9);
    }
    net.generation++;
    net.state=net.pending=0;
    net.peer_n=net.scan_n=net.ctl_event_n=0;
    memset(net.handlers,0,sizeof net.handlers);
    net.ctl=1;
    net.callback_thread=sched_create_service_thread("LOAAdhocctl",(int)A1,A0,ctl_callbacks,(void *)(uintptr_t)net.generation);
    if(net.callback_thread>=0x80000000u) {
        uint32_t error=net.callback_thread;
        net.ctl=0;
        net.callback_thread=0;
        net.transport->ops->logout(net.transport);
        loa_coop_transport_close();
        net.transport=NULL;
        return error;
    }
    net.thread=sched_create_service_thread("LOANetInput",0x77,0x1000,ctl_thread,(void *)(uintptr_t)net.generation);
    if(net.thread>=0x80000000u) {
        uint32_t error=net.thread;net.thread=0;net.ctl=0;net.generation++;
        sched_service_kick(net.callback_thread);net.callback_thread=0;
        net.transport->ops->logout(net.transport);loa_coop_transport_close();net.transport=NULL;
        return error;
    }
    fprintf(stderr,"LOA_NET: host input polling priority=119; adhocctl callback priority=%u\n",A1);
    fprintf(stderr,"LOA_NET: lobby connected; product=%s\n",product);
    return 0;
}
static uint32_t ctl_term(CpuState *s) {
    (void)s;
    if(net.ctl) {
        uint32_t thread=net.thread,callback_thread=net.callback_thread;
        net.ctl=0;
        net.generation++;
        net.state=net.pending=0;
        net.peer_n=0;
        net.thread=0;
        net.callback_thread=0;
        net.ctl_event_n=0;
        if(net.transport)net.transport->ops->logout(net.transport);
        loa_coop_transport_close();
        net.transport=NULL;
        if(thread)sched_service_kick(thread);
        if(callback_thread)sched_service_kick(callback_thread);
    }
    return 0;
}
static uint32_t ctl_add(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    if(!A0)return CTLERR(4);
    for(unsigned i=0;i<4;i++)if(!net.handlers[i].fn) {
        net.handlers[i]=(Handler) {
            A0,A1,s->r[28]
        }
        ;
        return i;
    }
    return CTLERR(18);
}
static uint32_t ctl_delete(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    if(A0>=4 || !net.handlers[A0].fn)return CTLERR(6);
    memset(&net.handlers[A0],0,sizeof(Handler));
    return 0;
}
static uint32_t ctl_state(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    if(!A0||!sr_guest_span_writable(A0,4))return CTLERR(4);
    MEM_W32(A0,net.state);
    return 0;
}
static uint32_t ctl_group(CpuState *s,uint32_t address) {
    if(!net.ctl)return CTLERR(8);
    if(net.pending)return CTLERR(16);
    if(net.state==1)return CTLERR(2);
    uint8_t group[8];
    if(!read_bytes(address,group,8))return CTLERR(4);
    for(unsigned i=0;i<8 && group[i];i++)if(!((group[i]>='A'&&group[i]<='Z')||(group[i]>='a'&&group[i]<='z')||(group[i]>='0'&&group[i]<='9')))return CTLERR(4);
    int result=net.transport->ops->connect(net.transport,group);
    if(result)return CTLERR(9);
    memcpy(net.group,group,8);
    net.pending=1;
    if(net.thread)sched_service_kick(net.thread);
    (void)s;
    return 0;
}
static uint32_t ctl_connect(CpuState *s) {
    return ctl_group(s,A0);
}
static uint32_t ctl_join(CpuState *s) {
    if(!A0||!sr_guest_span_readable(A0,28))return CTLERR(4);
    return ctl_group(s,A0+8);
}
static uint32_t ctl_scan(CpuState *s) {
    (void)s;
    if(!net.ctl)return CTLERR(8);
    if(net.pending)return CTLERR(16);
    if(net.state==1)return CTLERR(2);
    int r=net.transport->ops->scan(net.transport);
    if(r)return CTLERR(9);
    net.scan_n=0;
    net.pending=1;
    net.state=2;
    sched_service_kick(net.thread);
    return 0;
}
static uint32_t ctl_disconnect(CpuState *s) {
    (void)s;
    if(!net.ctl)return CTLERR(8);
    if(net.pending)return CTLERR(16);
    if(net.state==1 && net.transport->ops->disconnect(net.transport))return CTLERR(9);
    net.peer_n=0;
    net.pending=1;
    net.disconnect_due=sched_vtime_deadline_after(104638);
    sched_service_kick(net.thread);
    return 0;
}
static void peer_info(uint32_t out,const Peer *peer,uint32_t next) {
    zero_bytes(out,152);
    MEM_W32(out,next);
    write_bytes(out+4,peer->nickname,128);
    write_bytes(out+132,peer->mac,6);
    MEM_W32(out+140,0x400);
    MEM_W32(out+144,(uint32_t)sched_vtime_us());
    MEM_W32(out+148,(uint32_t)(sched_vtime_us()>>32));
}
static uint32_t ctl_peer_list(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    if(!A0||!sr_guest_span_writable(A0,4))return CTLERR(4);
    uint32_t capacity=MEM_R32(A0),needed=net.peer_n*152u;
    MEM_W32(A0,needed);
    if(!A1)return 0;
    uint32_t count=capacity/152u;
    if(count>net.peer_n)count=net.peer_n;
    if(count && !sr_guest_span_writable(A1,count*152))return CTLERR(4);
    for(uint32_t i=0;i<count;i++)peer_info(A1+152*i,&net.peers[i],i+1<count?A1+152*(i+1):0);
    MEM_W32(A0,count*152);
    return 0;
}
static uint32_t ctl_peer_info(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    uint8_t mac[6];
    if(!read_bytes(A0,mac,6)||A1<152||!A2||!sr_guest_span_writable(A2,152))return CTLERR(4);
    for(unsigned i=0;i<net.peer_n;i++)if(!memcmp(mac,net.peers[i].mac,6)) {
        peer_info(A2,&net.peers[i],0);
        return 0;
    }
    return NETERR(22);
}
static uint32_t ctl_scan_info(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    if(!A0||!sr_guest_span_writable(A0,4))return CTLERR(4);
    uint32_t cap=MEM_R32(A0),needed=net.scan_n*28u;
    MEM_W32(A0,needed);
    if(!A1)return 0;
    uint32_t count=cap/28;
    if(count>net.scan_n)count=net.scan_n;
    if(count && !sr_guest_span_writable(A1,count*28))return CTLERR(4);
    for(uint32_t i=0;i<count;i++) {
        uint32_t out=A1+28*i;
        zero_bytes(out,28);
        MEM_W32(out,i+1<count?out+28:0);
        MEM_W32(out+4,1);
        write_bytes(out+8,net.scans[i].group,8);
        write_bytes(out+16,net.scans[i].bssid,6);
    }
    MEM_W32(A0,count*28);
    return 0;
}
static uint32_t ctl_parameter(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    if(net.state!=1)return CTLERR(9);
    if(!A0||!sr_guest_span_writable(A0,148))return CTLERR(4);
    zero_bytes(A0,148);
    MEM_W32(A0,1);
    write_bytes(A0+4,net.group,8);
    write_bytes(A0+12,net.nickname,128);
    write_bytes(A0+140,net.bssid,6);
    return 0;
}
static uint32_t pdp_create(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(!net.ctl||!net.transport)return NETERR(11);
    uint8_t mac[6];
    if(!read_bytes(A0,mac,6)||memcmp(mac,net.mac,6))return NETERR(2);
    if(A1>65535)return NETERR(3);
    if(!A2 || A2>1024*1024)return NETERR(4);
    for(unsigned i=0;i<16;i++)if(!net.pdp[i].used) {
        int handle=net.transport->ops->pdp_open(net.transport,(uint16_t)A1);
        if(handle<0)return transport_error(handle);
        net.pdp[i]=(Pdp) {
            1,handle,A2
        }
        ;
        return i+1;
    }
    return NETERR(15);
}
static Pdp *pdp(uint32_t id) {
    return id>=1 && id<=16 && net.pdp[id-1].used?&net.pdp[id-1]:NULL;
}
static uint32_t pdp_delete(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    Pdp *p=pdp(A0);
    if(!p)return NETERR(1);
    int r=net.transport?net.transport->ops->pdp_close(net.transport,p->transport):NK_NET_NO_SOCKET;
    p->used=0;
    return transport_error(r);
}
static uint32_t pdp_send(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    Pdp *p=pdp(A0);
    if(!p)return NETERR(1);
    if(!net.transport)return NETERR(12);
    uint8_t mac[6],data[NK_RELAY_PDP_MAX];
    uint32_t size=arg(s,4),timeout=arg(s,5),nonblock=arg(s,6);
    if(A2>65535)return NETERR(3);
    if(size>sizeof data || !size)return NETERR(5);
    if(!read_bytes(A1,mac,6)||!read_bytes(A3,data,size))return NETERR(2);
    uint64_t end=sched_vtime_deadline_after(timeout);
    int broadcast=!memcmp(mac,"\xff\xff\xff\xff\xff\xff",6),result;
    do {
        result=NK_NET_OK;
        if(broadcast) {
            if(net.state!=1)return NETERR(11);
            for(unsigned i=0;i<net.peer_n;i++) {
                int r=net.transport->ops->pdp_send(net.transport,p->transport,net.peers[i].mac,(uint16_t)A2,data,size);
                if(r)result=r;
            }
        }
        else result=net.transport->ops->pdp_send(net.transport,p->transport,mac,(uint16_t)A2,data,size);
        if(result!=NK_NET_AGAIN)return transport_error(result);
        if(nonblock)return NETERR(9);
        if(timeout && sched_vtime_us()>=end)return NETERR(21);
        sched_delay_current(1000);
    }
    while(1);
}
static uint32_t pdp_recv(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    Pdp *p=pdp(A0);
    if(!p)return NETERR(1);
    if(!net.transport)return NETERR(12);
    uint32_t size_addr=arg(s,4),timeout=arg(s,5),nonblock=arg(s,6);
    if(!size_addr||!sr_guest_span_writable(size_addr,4))return NETERR(2);
    uint32_t capacity=MEM_R32(size_addr);
    if(!A1||!A2||!A3||!sr_guest_span_writable(A1,6)||!sr_guest_span_writable(A2,2)||!sr_guest_span_writable(A3,capacity))return NETERR(2);
    uint64_t end=sched_vtime_deadline_after(timeout);
    uint8_t data[NK_RELAY_PDP_MAX],mac[6];
    uint16_t port;
    uint32_t bytes;
    do {
        bytes=0;
        int result=net.transport->ops->pdp_recv(net.transport,p->transport,mac,&port,data,capacity<sizeof data?capacity:sizeof data,&bytes);
        if(result==NK_NET_OK) {
            write_bytes(A1,mac,6);
            MEM_W16(A2,port);
            write_bytes(A3,data,bytes);
            MEM_W32(size_addr,bytes);
            return 0;
        }
        if(result==NK_NET_SHORT_BUFFER) {
            MEM_W32(size_addr,bytes);
            return 0x80400706u;
        }
        if(result!=NK_NET_AGAIN)return transport_error(result);
        if(nonblock)return NETERR(9);
        if(timeout && sched_vtime_us()>=end)return NETERR(21);
        sched_delay_current(1000);
    }
    while(1);
}
static uint32_t pdp_stat(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(!A0||!sr_guest_span_writable(A0,4))return NETERR(2);
    uint32_t cap=MEM_R32(A0),count=0;
    for(unsigned i=0;i<16;i++)count+=net.pdp[i].used;
    MEM_W32(A0,count*20);
    if(!A1)return 0;
    unsigned available=cap/20;
    if(count>available)count=available;
    if(count && !sr_guest_span_writable(A1,count*20))return NETERR(2);
    unsigned n=0;
    for(unsigned i=0;i<16 && n<count;i++)if(net.pdp[i].used) {
        uint16_t port;uint32_t pending;
        int status=loa_coop_socket_info(net.pdp[i].transport,&port,&pending);
        if(status!=NK_NET_OK)return transport_error(status);
        uint32_t out=A1+20*n;
        zero_bytes(out,20);
        MEM_W32(out,++n<count?out+20:0);
        MEM_W32(out+4,i+1);
        write_bytes(out+8,net.mac,6);
        MEM_W16(out+14,port);
        MEM_W32(out+16,pending);
    }
    return 0;
}
/* Native-to-native matching protocol LOAM/1. Guest event numbers/ABI follow
* PSP matching; this is not claimed compatible with PPSSPP/aemu matching.
* Data confirmation follows an actual receipt ACK, not local send success. */
static uint32_t u32le(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void put32(uint8_t *p,uint32_t x) {
    p[0]=(uint8_t)x;
    p[1]=(uint8_t)(x>>8);
    p[2]=(uint8_t)(x>>16);
    p[3]=(uint8_t)(x>>24);
}
static MatchPeer *match_peer(Matching *m,const uint8_t mac[6],int create) {
    for(unsigned i=0;i<MAX_MATCH_PEERS;i++)if(m->peers[i].state && !memcmp(m->peers[i].mac,mac,6))return &m->peers[i];
    if(create)for(unsigned i=0;i<MAX_MATCH_PEERS;i++)if(!m->peers[i].state) {
        MatchPeer *p=&m->peers[i];
        memset(p,0,sizeof *p);
        memcpy(p->mac,mac,6);
        p->state=1;
        p->port=m->port;
        p->seen=sched_vtime_us();
        return p;
    }
    return NULL;
}
static unsigned match_members(Matching *m) {
    unsigned count=1;
    for(unsigned i=0;i<MAX_MATCH_PEERS;i++)count+=m->peers[i].state==4;
    return count;
}
static void match_event(Matching *m,unsigned kind,const uint8_t mac[6],const void *data,unsigned len) {
    if(len>MAX_OPTION || m->event_n>=16) {
        fprintf(stderr,"SEMANTIC_BOUNDARY: native matching event queue overflow\n");
        exit(1);
    }
    MatchEvent *e=&m->events[m->event_n++];
    e->kind=kind;
    e->len=len;
    memcpy(e->mac,mac,6);
    if(len)memcpy(e->data,data,len);
    if(m->thread)sched_service_kick(m->thread);
}
static int match_send(Matching *m,const uint8_t mac[6],uint16_t port,uint8_t op,uint32_t seq,const void *data,uint32_t len) {
    if(len>MAX_OPTION || !net.transport)return NK_NET_BAD_ARG;
    uint8_t packet[MAX_OPTION+13];
    memcpy(packet,"LOAM",4);
    packet[4]=op;
    put32(packet+5,seq);
    put32(packet+9,len);
    if(len)memcpy(packet+13,data,len);
    int result=net.transport->ops->pdp_send(net.transport,m->transport,mac,port,packet,len+13);
    if(getenv("LOA_NET_TRACE"))fprintf(stderr,"LOA_NET_TRACE: send mode=%d op=%u seq=%u port=%u result=%d\n",m->mode,op,seq,port,result);
    return result;
}
static void matching_poll(CpuState *s,Matching *m) {
    (void)s;
    uint64_t now=sched_vtime_us();
    if(!net.transport || net.state!=1) {
        for(unsigned i=0;i<MAX_MATCH_PEERS;i++)if(m->peers[i].state) {
            match_event(m,8,m->peers[i].mac,NULL,0);
            memset(&m->peers[i],0,sizeof(MatchPeer));
        }
        return;
    }
    if(m->mode!=2 && now>=m->hello_due && match_members(m)<(unsigned)m->max) {
        for(unsigned i=0;i<net.peer_n;i++)match_send(m,net.peers[i].mac,m->port,1,0,m->hello,m->hello_len);
        m->hello_due=sched_vtime_deadline_after(m->hello_interval);
    }
    if(now>=m->ping_due) {
        for(unsigned i=0;i<MAX_MATCH_PEERS;i++)if(m->peers[i].state)match_send(m,m->peers[i].mac,m->peers[i].port,0,0,NULL,0);
        m->ping_due=sched_vtime_deadline_after(m->keepalive_interval);
    }
    for(unsigned input=0;input<32;input++) {
        uint8_t packet[NK_RELAY_PDP_MAX],mac[6];
        uint16_t port;
        uint32_t len=0;
        int result=net.transport->ops->pdp_recv(net.transport,m->transport,mac,&port,packet,sizeof packet,&len);
        if(result!=NK_NET_OK)break;
        if(len<13 || memcmp(packet,"LOAM",4))continue;
        uint8_t op=packet[4];
        uint32_t seq=u32le(packet+5),bytes=u32le(packet+9);
        if(bytes>MAX_OPTION || bytes!=len-13)continue;
        uint8_t *data=packet+13;
        MatchPeer *p=match_peer(m,mac,op==1 || op==2);
        if(!p)continue;
        if(getenv("LOA_NET_TRACE"))fprintf(stderr,"LOA_NET_TRACE: receive mode=%d op=%u seq=%u state=%d\n",m->mode,op,seq,p->state);
        p->seen=now;
        p->port=port;
        if(op==1 && p->state==1 && m->mode!=1) {
            match_event(m,1,mac,data,bytes);
        }
        else if(op==2 && m->mode!=2) {
            if(p->state==4)match_send(m,mac,port,3,seq,NULL,0);
            else if(p->state!=3) {
                p->state=3;
                match_event(m,2,mac,data,bytes);
            }
        }
        else if(op==3 && (p->state==2 || p->state==4)) {
            int was=p->state;
            p->state=4;
            p->control_op=0;
            match_send(m,mac,port,4,seq,NULL,0);
            if(m->mode==2 && was!=4) {
                memcpy(m->parent,mac,6);
                m->parent_first_at=sched_vtime_deadline_after(m->keepalive_interval);
            }
            if(was!=4) {
                match_event(m,6,mac,data,bytes);
                match_event(m,7,mac,NULL,0);
            }
        }
        else if(op==4 && p->state==3 && p->control_op==3 && seq==p->control_seq) {
            p->state=4;
            p->control_op=0;
            match_event(m,7,mac,NULL,0);
            /* Tell existing children about the new member and vice versa. */ if(m->mode==1)for(unsigned i=0;i<MAX_MATCH_PEERS;i++)if(m->peers[i].state==4 && &m->peers[i]!=p) {
                match_send(m,m->peers[i].mac,m->peers[i].port,8,0,mac,6);
                match_send(m,mac,port,8,0,m->peers[i].mac,6);
            }
        }
        else if(op==8 && m->mode==2 && p->state==4 && bytes==6) {
            MatchPeer *sibling=match_peer(m,data,1);
            if(sibling)sibling->state=4;
        }
        else if(op==5 || op==9) {
            unsigned event=p->state==4?10:p->state==2?4:5;
            match_event(m,event,mac,data,bytes);
            memset(p,0,sizeof *p);
        }
        else if(op==16 && p->state==4) {
            /* Duplicate sequence numbers are acknowledged without redelivery. */ if(seq!=p->pending_seq || !p->pending_seq) {
                match_event(m,11,mac,data,bytes);
                p->pending_seq=seq;
            }
            match_send(m,mac,port,17,seq,NULL,0);
        }
        else if(op==17 && p->state==4 && p->pending_len && seq==u32le(p->pending)) {
            p->pending_len=0;
            match_event(m,12,mac,NULL,0);
        }
    }
    for(unsigned i=0;i<MAX_MATCH_PEERS;i++) {
        MatchPeer *p=&m->peers[i];
        if(!p->state)continue;
        int present=0;
        for(unsigned n=0;n<net.peer_n;n++)present|=!memcmp(net.peers[n].mac,p->mac,6);
        if(!present || now-p->seen>m->timeout) {
            match_event(m,8,p->mac,NULL,0);
            memset(p,0,sizeof *p);
            continue;
        }
        if(p->control_op && now>=p->control_at) {
            if(p->control_retries++>=m->retry_count) {
                match_event(m,8,p->mac,NULL,0);
                memset(p,0,sizeof *p);
                continue;
            }
            match_send(m,p->mac,p->port,p->control_op,p->control_seq,p->control,p->control_len);
            p->control_at=sched_vtime_deadline_after(m->retry_interval);
        }
        if(p->pending_len && now>=p->retry_at) {
            if(p->retries++>=m->retry_count) {
                p->pending_len=0;
                match_event(m,13,p->mac,NULL,0);
            }
            else {
                match_send(m,p->mac,p->port,16,u32le(p->pending),p->pending+4,p->pending_len);
                p->retry_at=sched_vtime_deadline_after(m->retry_interval);
            }
        }
    }
}
static void match_thread(CpuState *s,void *opaque) {
    Matching *m=opaque;
    uint32_t generation=m->generation,sp=s->r[29];
    while(m->used && m->running && generation==m->generation) {
        while(m->event_n && m->running && m->used && generation==m->generation) {
            MatchEvent event=m->events[0];
            memmove(m->events,m->events+1,(--m->event_n)*sizeof(MatchEvent));
            write_bytes(m->scratch,event.mac,6);
            if(event.len)write_bytes(m->scratch+16,event.data,event.len);
            s->r[4]=(uint32_t)(m-net.contexts)+1;
            s->r[5]=event.kind;
            s->r[6]=m->scratch;
            s->r[7]=event.len;
            s->r[8]=event.len?m->scratch+16:0;
            fprintf(stderr,"LOA_NET: matching id=%u event=%u bytes=%u\n",s->r[4],event.kind,event.len);
            call(s,m->fn,m->gp,sp,"LOA native matching");
        }
        if(m->used && m->running && generation==m->generation)sched_service_wait(UINT64_MAX);
    }
}
static uint32_t match_init(CpuState *s) {
    if(net.matching)return MATCHERR(18);
    if(!A0 || A0>4*1024*1024)return MATCHERR(9);
    uint32_t pool=alloc_block(A0);
    if(pool==0xffffffffu)return MATCHERR(9);
    net.matching_pool=pool;
    net.matching_base=block_addr(pool);
    net.matching_size=A0;
    net.matching=1;
    return 0;
}
static void match_stop_context(Matching *m) {
    if(!m->running)return;
    if(net.transport)for(unsigned i=0;i<MAX_MATCH_PEERS;i++)if(m->peers[i].state)match_send(m,m->peers[i].mac,m->peers[i].port,9,0,NULL,0);
    m->running=0;
    m->generation++;
    m->event_n=0;
    memset(m->peers,0,sizeof m->peers);
    if(m->thread)sched_service_kick(m->thread);
    m->thread=0;
}
static uint32_t match_term(CpuState *s) {
    (void)s;
    if(!net.matching)return 0;
    for(unsigned i=0;i<MAX_MATCH;i++)if(net.contexts[i].used) {
        Matching *m=&net.contexts[i];
        match_stop_context(m);
        if(net.transport)net.transport->ops->pdp_close(net.transport,m->transport);
        m->used=0;
    }
    free_block(net.matching_pool);
    net.matching_pool=0;
    net.matching=0;
    return 0;
}
static uint32_t match_create(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    if(!net.adhoc||!net.ctl||!net.transport)return MATCHERR(6);
    uint32_t mode=A0,max=A1,port=A2,rx=A3,hello=arg(s,4),keepalive=arg(s,5),retries=arg(s,6),interval=arg(s,7),fn=arg(s,8);
    if(mode<1||mode>3)return MATCHERR(1);
    /* PSP matching permits 2..16 members. The guest requests five even when
     * the outer Steam lobby is limited to four players. These are separate
     * limits: do not reject a valid matching context based on lobby capacity. */
    if(max<2||max>MAX_MATCH_PEERS+1)return MATCHERR(3);
    if(port>65535||!port)return MATCHERR(2);
    if(rx<6*max+4)return MATCHERR(4);
    if(rx>1024*1024 || !fn || ((mode==1||mode==3)&&(!hello||!keepalive)) || !interval)return MATCHERR(6);
    for(unsigned i=0;i<MAX_MATCH;i++)if(net.contexts[i].used && net.contexts[i].port==port)return MATCHERR(20);
    for(unsigned i=0;i<MAX_MATCH;i++)if(!net.contexts[i].used) {
        uint32_t size=MAX_OPTION+16,offset=i*size;
        if(offset+size>net.matching_size)return MATCHERR(9);
        int handle=net.transport->ops->pdp_open(net.transport,(uint16_t)port);
        if(handle<0)return handle==NK_NET_PORT_IN_USE?MATCHERR(20):MATCHERR(9);
        Matching *m=&net.contexts[i];
        uint32_t generation=m->generation+1;
        memset(m,0,sizeof *m);
        m->used=1;
        m->generation=generation;
        m->mode=(int)mode;
        m->max=(int)max;
        m->transport=handle;
        m->port=(uint16_t)port;
        m->fn=fn;
        m->gp=s->r[28];
        m->scratch=net.matching_base+offset;
        m->hello_interval=hello?hello:1000000;
        m->keepalive_interval=keepalive?keepalive:1000000;
        m->retry_interval=interval;
        m->retry_count=retries?retries:1;
        m->timeout=(uint64_t)m->keepalive_interval*m->retry_count+1000000;
        fprintf(stderr,"LOA_NET: matching created id=%u mode=%u max=%u port=%u rx=%u\n",i+1,mode,max,port,rx);
        return i+1;
    }
    return MATCHERR(8);
}
static uint32_t match_start(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    if(m->running)return MATCHERR(10);
    uint32_t bytes=arg(s,5),data=arg(s,6);
    if(bytes>MAX_OPTION || (bytes && !read_bytes(data,m->hello,bytes)))return MATCHERR(5);
    /* Transport input is polled by the host, not a separate guest input
     * thread. A zero input-stack request is used by this title and accepted
     * by pinned PPSSPP; it must not prevent starting the real event worker. */
    uint32_t input_stack=arg(s,4);
    if(A2<0x400 || (input_stack && input_stack<0x400))return MATCHERR(21);
    m->hello_len=bytes;
    m->hello_due=m->ping_due=0;
    m->running=1;
    m->generation++;
    m->thread=sched_create_service_thread("LOAMatching",(int)A1,A2,match_thread,m);
    if(m->thread>=0x80000000u) {
        m->running=0;
        fprintf(stderr,"LOA_NET: matching start failed id=%u error=%08x\n",A0,m->thread);
        return m->thread;
    }
    fprintf(stderr,"LOA_NET: matching started id=%u event_priority=%u event_stack=%u input_stack=%u option_bytes=%u\n",A0,A1,A2,input_stack,bytes);
    if(net.thread)sched_service_kick(net.thread);
    return 0;
}
static uint32_t match_stop(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    match_stop_context(m);
    return 0;
}
static uint32_t match_delete(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    match_stop_context(m);
    if(net.transport)net.transport->ops->pdp_close(net.transport,m->transport);
    m->used=0;
    return 0;
}
static uint32_t match_hello(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    if(A1>MAX_OPTION || (A1&&!read_bytes(A2,m->hello,A1)))return MATCHERR(5);
    m->hello_len=A1;
    m->hello_due=0;
    return 0;
}
static uint32_t match_select(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    if(!m->running)return MATCHERR(11);
    uint8_t mac[6],data[MAX_OPTION];
    if(!read_bytes(A1,mac,6)||A2>MAX_OPTION||(A2&&!read_bytes(A3,data,A2)))return MATCHERR(6);
    MatchPeer *p=match_peer(m,mac,0);
    if(!p)return MATCHERR(12);
    if(p->state==4)return MATCHERR(16);
    uint8_t op=(m->mode==1 || p->state==3)?3:2;
    if(op==3 && match_members(m)>=(unsigned)m->max)return MATCHERR(14);
    uint32_t seq=++m->sequence;
    int r=match_send(m,mac,p->port,op,seq,data,A2);
    if(r)return transport_error(r);
    p->state=op==3?3:2;
    p->control_op=op;
    p->control_seq=seq;
    p->control_len=A2;
    if(A2)memcpy(p->control,data,A2);
    p->control_at=sched_vtime_deadline_after(m->retry_interval);
    p->control_retries=0;
    return 0;
}
static uint32_t match_cancel(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    uint8_t mac[6];
    if(!read_bytes(A1,mac,6))return MATCHERR(6);
    MatchPeer *p=match_peer(m,mac,0);
    if(!p)return MATCHERR(12);
    int r=match_send(m,mac,p->port,5,0,NULL,0);
    if(r)return transport_error(r);
    memset(p,0,sizeof *p);
    return 0;
}
static uint32_t match_send_data(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    if(!m->running)return MATCHERR(11);
    uint8_t mac[6];
    if(!read_bytes(A1,mac,6)||!A2||A2>MAX_OPTION-4)return MATCHERR(22);
    MatchPeer *p=match_peer(m,mac,0);
    if(!p||p->state!=4)return MATCHERR(23);
    if(p->pending_len)return MATCHERR(24);
    if(!read_bytes(A3,p->pending+4,A2))return MATCHERR(6);
    uint32_t seq=++m->sequence;
    put32(p->pending,seq);
    int r=match_send(m,mac,p->port,16,seq,p->pending+4,A2);
    if(r)return transport_error(r);
    p->pending_len=A2;
    p->retries=0;
    p->retry_at=sched_vtime_deadline_after(m->retry_interval);
    return 0;
}
static uint32_t match_abort(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    uint8_t mac[6];
    if(!read_bytes(A1,mac,6))return MATCHERR(6);
    MatchPeer *p=match_peer(m,mac,0);
    if(!p)return MATCHERR(12);
    p->pending_len=0;
    return 0;
}
static uint32_t match_get_members(CpuState *s) {
    if(!net.matching)return MATCHERR(19);
    Matching *m=matching(A0);
    if(!m)return MATCHERR(7);
    if(!m->running)return MATCHERR(11);
    if(!A1||!sr_guest_span_writable(A1,4))return MATCHERR(6);
    unsigned total=match_members(m),cap=MEM_R32(A1)/12;
    MEM_W32(A1,total*12);
    if(!A2)return 0;
    if(cap>total)cap=total;
    if(cap&&!sr_guest_span_writable(A2,cap*12))return MATCHERR(6);
    const uint8_t *order[MAX_MATCH_PEERS+1];
    unsigned count=0;
    int parent_first=m->mode==2 && m->parent_first_at && sched_vtime_us()>=m->parent_first_at;
    MatchPeer *parent=parent_first?match_peer(m,m->parent,0):NULL;
    if(parent && parent->state==4)order[count++]=parent->mac;
    else parent=NULL;
    order[count++]=net.mac;
    for(unsigned i=0;i<MAX_MATCH_PEERS;i++)if(m->peers[i].state==4 && &m->peers[i]!=parent)order[count++]=m->peers[i].mac;
    for(unsigned i=0;i<cap;i++) {
        uint32_t out=A2+12*i;
        zero_bytes(out,12);
        write_bytes(out+4,order[i],6);
        MEM_W32(out,i+1<cap?out+12:0);
    }
    MEM_W32(A1,cap*12);
    return 0;
}
static uint32_t ptp_open(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(!net.transport)return NETERR(11);
    uint8_t local[6],peer[6];
    if(!read_bytes(A0,local,6)||memcmp(local,net.mac,6)||!read_bytes(A2,peer,6))return NETERR(2);
    if(A1>65535||!A3||A3>65535)return NETERR(3);
    if(!arg(s,4))return NETERR(4);
    int handle=loa_coop_ptp_open((uint16_t)A1,peer,(uint16_t)A3,0);
    return handle<0?transport_error(handle):(uint32_t)handle+17;
}
static uint32_t ptp_listen(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(!net.transport)return NETERR(11);
    uint8_t local[6];
    if(!read_bytes(A0,local,6)||memcmp(local,net.mac,6))return NETERR(2);
    if(A1>65535)return NETERR(3);
    if(!A2)return NETERR(4);
    unsigned backlog=arg(s,5);
    if(!backlog || backlog>16)return NETERR(17);
    int handle=loa_coop_ptp_open((uint16_t)A1,NULL,0,(int)backlog);
    return handle<0?transport_error(handle):(uint32_t)handle+17;
}
static uint32_t ptp_connect(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(A0<17||A0>=33)return NETERR(1);
    int handle=(int)A0-17;
    uint64_t end=sched_vtime_deadline_after(A1);
    uint32_t timeout=A1,nonblock=A2;
    while(1) {
        int r=loa_coop_ptp_connect(handle);
        if(r==NK_NET_OK)return 0;
        if(r!=NK_NET_AGAIN)return r==NK_NET_BAD_ARG?NETERR(24):transport_error(r);
        if(nonblock)return NETERR(9);
        if(timeout&&sched_vtime_us()>=end)return NETERR(21);
        sched_delay_current(1000);
    }
}
static uint32_t ptp_accept(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(A0<17||A0>=33)return NETERR(1);
    if((A1&&!sr_guest_span_writable(A1,6))||(A2&&!sr_guest_span_writable(A2,2)))return NETERR(2);
    uint32_t timeout=A3,nonblock=arg(s,4);
    uint64_t end=sched_vtime_deadline_after(timeout);
    while(1) {
        int handle=loa_coop_ptp_accept((int)A0-17);
        if(handle>=0) {
            LoaPtpStat info;
            if(loa_coop_ptp_stat(handle,&info))return NETERR(1);
            if(A1)write_bytes(A1,info.peer,6);
            if(A2)MEM_W16(A2,info.peer_port);
            return (uint32_t)handle+17;
        }
        if(handle!=NK_NET_AGAIN)return transport_error(handle);
        if(nonblock)return NETERR(9);
        if(timeout&&sched_vtime_us()>=end)return NETERR(21);
        sched_delay_current(1000);
    }
}
static uint32_t ptp_close(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(A0<17||A0>=33)return NETERR(1);
    return transport_error(loa_coop_ptp_close((int)A0-17));
}
static uint32_t ptp_transfer(CpuState *s,int receive) {
    if(!net.adhoc)return NETERR(18);
    if(A0<17||A0>=33)return NETERR(1);
    if(!A2||!sr_guest_span_writable(A2,4))return NETERR(2);
    uint32_t capacity=MEM_R32(A2),timeout=A3,nonblock=arg(s,4);
    if(!capacity || capacity>50*1024)return NETERR(5);
    if(!A1 || !(receive?sr_guest_span_writable(A1,capacity):sr_guest_span_readable(A1,capacity)))return NETERR(2);
    uint8_t data[50*1024];
    if(!receive)read_bytes(A1,data,capacity);
    uint64_t end=sched_vtime_deadline_after(timeout);
    while(1) {
        uint32_t bytes=capacity;
        int r=receive?loa_coop_ptp_recv((int)A0-17,data,&bytes):loa_coop_ptp_send((int)A0-17,data,&bytes);
        if(r==NK_NET_OK) {
            if(receive)write_bytes(A1,data,bytes);
            MEM_W32(A2,bytes);
            return 0;
        }
        if(r!=NK_NET_AGAIN)return transport_error(r);
        if(nonblock)return NETERR(9);
        if(timeout&&sched_vtime_us()>=end)return NETERR(21);
        sched_delay_current(1000);
    }
}
static uint32_t ptp_send(CpuState *s) {
    return ptp_transfer(s,0);
}
static uint32_t ptp_recv(CpuState *s) {
    return ptp_transfer(s,1);
}
static uint32_t ptp_stat(CpuState *s) {
    if(!net.adhoc)return NETERR(18);
    if(!A0||!sr_guest_span_writable(A0,4))return NETERR(2);
    LoaPtpStat items[16];
    unsigned handles[16],count=0;
    for(unsigned i=0;i<16;i++)if(!loa_coop_ptp_stat((int)i,&items[count]))handles[count++]=i+17;
    unsigned cap=MEM_R32(A0)/36;
    MEM_W32(A0,count*36);
    if(!A1)return 0;
    if(cap>count)cap=count;
    if(cap&&!sr_guest_span_writable(A1,cap*36))return NETERR(2);
    for(unsigned i=0;i<cap;i++) {
        uint32_t out=A1+36*i;
        zero_bytes(out,36);
        MEM_W32(out,i+1<cap?out+36:0);
        MEM_W32(out+4,handles[i]);
        write_bytes(out+8,net.mac,6);
        write_bytes(out+14,items[i].peer,6);
        MEM_W16(out+20,items[i].local_port);
        MEM_W16(out+22,items[i].peer_port);
        MEM_W32(out+28,items[i].available);
        MEM_W32(out+32,items[i].state);
    }
    return 0;
}
/* Discovery maps a real matching room to a nearby console; it never declares
* PEER_FOUND because a timer or a local socket succeeded. Radio WOL is not
* implemented and is explicitly refused. PSP stack-error ordering is unmeasured. */
static uint32_t discover_start(CpuState *s) {
    if(!net.ctl)return CTLERR(8);
    if(net.discover_status)return 0x80411301u;
    if(!A0 || !sr_guest_span_writable(A0,20))return SCE_KERNEL_ERROR_ILLEGAL_ADDR;
    uint32_t mode=MEM_R32(A0),timeout=MEM_R32(A0+12);
    if(mode>1 || !timeout)return 0x80411302u;
    if(mode==1)return hle_unmodelled_stop("sceNetAdhocDiscoverInitStart","radio WOL mode is not supported by the native Internet transport");
    uint32_t result=0;
    if(net.state==0)result=ctl_group(s,A0+4);
    else {
        uint8_t group[8];
        read_bytes(A0+4,group,8);
        if(net.state!=1 || memcmp(net.group,group,8))return CTLERR(16);
    }
    if(result)return result;
    net.discover_param=A0;
    net.discover_status=1;
    net.discover_deadline=sched_vtime_deadline_after((uint64_t)timeout*1000000);
    return 0;
}
static uint32_t discover_update(CpuState *s) {
    (void)s;
    if(net.discover_status!=1)return 0;
    int done=0;
    uint32_t result=0;
    if(net.state==1 && net.peer_n) {
        done=1;
        result=0;
    }
    else if(!net.transport || !loa_coop_transport_alive()) {
        done=1;
        result=CTLERR(9);
    }
    else if(sched_vtime_us()>=net.discover_deadline) {
        done=1;
        result=2;
    }
    if(done) {
        if(!sr_guest_span_writable(net.discover_param+16,4))return SCE_KERNEL_ERROR_ILLEGAL_ADDR;
        MEM_W32(net.discover_param+16,result);
        net.discover_status=2;
    }
    return 0;
}
static uint32_t discover_status(CpuState *s) {
    (void)s;
    return (uint32_t)net.discover_status;
}
static uint32_t discover_stop(CpuState *s) {
    (void)s;
    if(net.discover_status==1) {
        if(!sr_guest_span_writable(net.discover_param+16,4))return SCE_KERNEL_ERROR_ILLEGAL_ADDR;
        MEM_W32(net.discover_param+16,1);
        net.discover_status=2;
    }
    return 0;
}
static uint32_t discover_term(CpuState *s) {
    (void)s;
    if(net.discover_status==1)return 0x80411301u;
    net.discover_status=0;
    net.discover_param=0;
    return 0;
}
HleFn loa_net_handler(uint32_t nid) {
    if(!ready())return NULL;
    if(nid==0xe26f226eu) {
        __real_sr_hle_register(0x941b3877u,"sceNetAdhocDiscoverInitStart",discover_start);
        __real_sr_hle_register(0x52de1b97u,"sceNetAdhocDiscoverUpdate",discover_update);
        __real_sr_hle_register(0x944ddbc6u,"sceNetAdhocDiscoverGetStatus",discover_status);
        __real_sr_hle_register(0xa2246614u,"sceNetAdhocDiscoverTerm",discover_term);
    }
    switch(nid) {
        case 0x0c622081u:case 0x0bf0a3aeu:return wlan_mac;
        case 0xe1d621d7u:return adhoc_init;
        case 0xa62c6f57u:return adhoc_term;
        case 0xe26f226eu:return ctl_init;
        case 0x9d689e13u:return ctl_term;
        case 0x20b317a0u:return ctl_add;
        case 0x6402490bu:return ctl_delete;
        case 0x75ecd386u:return ctl_state;
        case 0xec0635c1u:case 0x0ad043edu:return ctl_connect;
        case 0x5e7f79c9u:return ctl_join;
        case 0x08fff7a0u:return ctl_scan;
        case 0x34401d65u:return ctl_disconnect;
        case 0xe162cb14u:return ctl_peer_list;
        case 0x8db83fdcu:return ctl_peer_info;
        case 0x81aee1beu:return ctl_scan_info;
        case 0xded9d28eu:return ctl_parameter;
        case 0x6f92741bu:return pdp_create;
        case 0x7f27bb5eu:return pdp_delete;
        case 0xabed3790u:return pdp_send;
        case 0xdfe53e03u:return pdp_recv;
        case 0xc7c1fc57u:return pdp_stat;
        case 0x2a2a1e07u:return match_init;
        case 0x7945ecdau:return match_term;
        case 0xca5eda6fu:return match_create;
        case 0x93ef3843u:return match_start;
        case 0x32b156b3u:return match_stop;
        case 0xf16eaf4fu:return match_delete;
        case 0xb58e61b7u:return match_hello;
        case 0x5e3d4b79u:return match_select;
        case 0xea3c6108u:return match_cancel;
        case 0xf79472d7u:return match_send_data;
        case 0xec19337du:return match_abort;
        case 0xc58bcd9eu:return match_get_members;
        case 0x877f6d66u:return ptp_open;
        case 0xe08bdac1u:return ptp_listen;
        case 0xfc6fc07bu:return ptp_connect;
        case 0x9df81198u:return ptp_accept;
        case 0x157e6225u:return ptp_close;
        case 0x4da4c788u:return ptp_send;
        case 0x8bea2b3eu:return ptp_recv;
        case 0xb9685118u:return ptp_stat;
        case 0x941b3877u:return discover_start;
        case 0x52de1b97u:return discover_update;
        case 0x944ddbc6u:return discover_status;
        case 0xa2246614u:return discover_term;
        case 0xf7d13214u:return discover_stop;
        default:return NULL;
    }
}
void __real_sr_hle_register(uint32_t,const char *,HleFn);
void __real_sr_hle_register_unsupported(uint32_t,const char *,uint32_t);
void __wrap_sr_hle_register_unsupported(uint32_t nid,const char *name,uint32_t error) {
    HleFn fn=loa_net_handler(nid);
    if(fn)__real_sr_hle_register(nid,name,fn);
    else __real_sr_hle_register_unsupported(nid,name,error);
}
