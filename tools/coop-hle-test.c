/* SPDX-License-Identifier: GPL-3.0-or-later
* Synthetic guest RAM and callbacks, real HLE handlers and real Winsock traffic.
* The small fiber driver is test infrastructure, not a substitute PSP scheduler
* or evidence of a game mission. Unused renderer/debug seams abort loudly. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdarg.h>
#include "coop_hle.c"
uint8_t *g_mem;
CpuState *s_cpu;
int g_sr_heap_watch,g_sr_watch_enabled,g_sr_last_writer_enabled,g_sr_mem_watch_count;
uint32_t g_sr_store_context_pc,g_sr_store_context_mem_offset;
int g_sr_store_context_mem_gpr=-1;
unsigned g_sr_store_context_mem_words;
SrMemWatch g_sr_mem_watches[SR_MAX_MEM_WATCHES];
volatile int g_sr_vram_read_pending;
void sr_oor(uint32_t a,uint32_t v,int store) {
    (void)a;
    (void)v;
    (void)store;
    abort();
}
void sr_ge_vram_read_prepare(uint32_t a,uint32_t b) {
    (void)a;
    (void)b;
    abort();
}
void sr_ge_vram_write_prepare(uint32_t a,uint32_t b) {
    (void)a;
    (void)b;
    abort();
}
void sr_ge_vram_write_commit(uint32_t a,uint32_t b) {
    (void)a;
    (void)b;
    abort();
}
uint32_t sr_get_ge_status(void) {
    return 0;
}
void sr_heap_note_write(uint32_t a,uint32_t b,uint32_t c,uint32_t d) {
    (void)a;
    (void)b;
    (void)c;
    (void)d;
    abort();
}
void sr_note_mem_write(uint32_t a,uint32_t b,uint32_t c,uint32_t d) {
    (void)a;
    (void)b;
    (void)c;
    (void)d;
    abort();
}
void sr_watch_store(uint32_t a,uint32_t b,uint32_t c,uint32_t d) {
    (void)a;
    (void)b;
    (void)c;
    (void)d;
    abort();
}
uint32_t hle_unmodelled_stop(const char *name,const char *format,...) {
    (void)format;
    fprintf(stderr,"TEST_UNSUPPORTED: %s\n",name);
    return 0x80010086u;
}
void __real_sr_hle_register(uint32_t nid,const char *name,HleFn fn) {
    (void)nid;
    (void)name;
    (void)fn;
}
void __real_sr_hle_register_unsupported(uint32_t nid,const char *name,uint32_t error) {
    (void)nid;
    (void)name;
    (void)error;
    abort();
}
static uint32_t allocated;
uint32_t alloc_block(uint32_t size) {
    if(size>0x100000)return 0xffffffffu;
    return ++allocated;
}
uint32_t block_addr(uint32_t uid) {
    return 0x08020000u+(uid-1)*0x100000u;
}
uint32_t free_block(uint32_t uid) {
    assert(uid>0 && uid<=allocated);
    return 0;
}
typedef struct  {
    SrSchedServiceBody body;
    void *arg,*fiber;
    CpuState cpu;
    uint64_t due;
    int alive;
    int priority;
}
Service;
static Service services[16];
static unsigned service_count;
static Service *current_service;
static void *main_fiber;
static ULONGLONG began;
uint64_t sched_vtime_us(void) {
    return (GetTickCount64()-began)*1000;
}
/* This older transport harness reads the live clock on every query. The
 * separate wait regression models the production scheduler's cached clock. */
void sched_vtime_refresh(void) {}
uint64_t sched_vtime_deadline_after(uint64_t delta) {
    return UINT64_MAX-sched_vtime_us()<delta?UINT64_MAX:sched_vtime_us()+delta;
}
static VOID WINAPI service_body(void *arg) {
    Service *v=arg;
    v->body(&v->cpu,v->arg);
    v->alive=0;
    SwitchToFiber(main_fiber);
    abort();
}
uint32_t sched_create_service_thread(const char *name,int priority,uint32_t stack,SrSchedServiceBody body,void *arg) {
    (void)name;
    if(priority<8||priority>0x77)return 0x80020193u;
    if(stack<0x200)return 0x800201b4u;
    if(service_count>=16)return 0x80020190u;
    Service *v=&services[service_count++];
    v->body=body;
    v->arg=arg;
    v->alive=1;
    v->priority=priority;
    v->cpu.r[29]=0x08e00000u-service_count*0x10000;
    v->fiber=CreateFiber(256*1024,service_body,v);
    assert(v->fiber);
    return 100+service_count;
}
void sched_service_wait(uint64_t deadline) {
    assert(current_service);
    current_service->due=deadline;
    SwitchToFiber(main_fiber);
}
void sched_service_kick(uint32_t uid) {
    if(uid>100&&uid<=100+service_count)services[uid-101].due=0;
}
void sched_delay_current(uint64_t usec) {
    if(current_service)sched_service_wait(sched_vtime_deadline_after(usec));
    else Sleep((DWORD)((usec+999)/1000));
}
void sched_delay_current_dispatching(uint64_t usec) {sched_delay_current(usec);}
static void tick(void) {
    for(unsigned i=0;i<service_count;i++) {
        Service *v=&services[i];
        if(v->alive && v->due<=sched_vtime_us()) {
            current_service=v;
            SwitchToFiber(v->fiber);
            current_service=NULL;
        }
    }
    Sleep(1);
}
static CpuState cpu;
static unsigned role,complete,data_received,data_confirm,ctl_connected;
#define RAM 0x08001000u
#define OPTIONS (RAM+512)
static void arguments(CpuState *s,const uint32_t *args,unsigned count) {
    for(unsigned i=0;i<count;i++) {
        if(i<8)s->r[i+4]=args[i];
        else MEM_W32(s->r[29]+4*(i-8),args[i]);
    }
}
int hle_dispatch_guest_scoped(CpuState *s,uint32_t fn,const char *owner,uint32_t *fatal) {
    (void)owner;
    (void)fatal;
    if(fn==0x08801000) {
        ctl_connected+=s->r[4]==1;
        return 0;
    }
    assert(fn==0x08802000 && s->r[4]==1);
    assert(sr_guest_span_readable(s->r[6],6));
    unsigned event=s->r[5];
    if((event==1 && role==2) || (event==2 && role==1)) {
        unsigned bytes=event==1?768:8;
        assert(s->r[7]==bytes);
        for(unsigned i=0;i<bytes;i++)assert(MEM_R8(s->r[8]+i)==(uint8_t)(i*31));
        CpuState request=cpu;
        uint32_t args[]= {
            1,s->r[6],8,OPTIONS
        }
        ;
        arguments(&request,args,4);
        assert(match_select(&request)==0);
    }
    else if(event==7)complete++;
    else if(event==11) {
        assert(s->r[7]==8);
        for(unsigned i=0;i<8;i++)assert(MEM_R8(s->r[8]+i)==(uint8_t)(i*31));
        data_received++;
    }
    else if(event==12)data_confirm++;
    return 0;
}
int main(int argc,char **argv) {
    assert(argc==3);
    role=(unsigned)atoi(argv[1]);
    began=GetTickCount64();
    main_fiber=ConvertThreadToFiber(NULL);
    assert(main_fiber);
    g_mem=calloc(1,0x04000000);
    assert(g_mem);
    cpu.r[29]=0x08f00000;
    cpu.r[28]=0x08808000;
    s_cpu=&cpu;
    char mac[32],port[16];
    snprintf(mac,sizeof mac,"02:00:00:00:00:%02u",role);
    snprintf(port,sizeof port,"%s",argv[2]);
    _putenv_s("LOA_NET_ENABLED","1");
    _putenv_s("LOA_NET_MAC",mac);
    _putenv_s("LOA_NET_NICKNAME",role==1?"Test host":"Test guest");
    _putenv_s("LOA_NET_TRACE","1");
    _putenv_s("LOA_NET_HOST","127.0.0.1");
    _putenv_s("LOA_NET_BIND",role==1?"127.0.0.2":"127.0.0.3");
    _putenv_s("LOA_NET_PORT",port);
    _putenv_s("LOA_NET_OFFSET","10000");
    assert(loa_net_handler(0xdeadbeef)==NULL);
    assert(loa_net_handler(0xe1d621d7)==adhoc_init);
    assert(adhoc_init(&cpu)==0);
    assert(adhoc_init(&cpu)==NETERR(19));
    MEM_W32(RAM,0);
    write_bytes(RAM+4,"NPJH50503",9);
    uint32_t init[]= {
        4096,32,RAM
    }
    ;
    arguments(&cpu,init,3);
    assert(ctl_init(&cpu)==0);
    assert(services[0].priority==32 && services[1].priority==0x77);
    uint32_t handler[]= {
        0x08801000,0
    }
    ;
    arguments(&cpu,handler,2);
    assert(ctl_add(&cpu)==0);
    write_bytes(RAM+64,"LOATEST",8);
    cpu.r[4]=RAM+64;
    assert(ctl_connect(&cpu)==0);
    uint64_t deadline=sched_vtime_deadline_after(10000000);
    while((!net.peer_n||net.state!=1||ctl_connected!=1)&&sched_vtime_us()<deadline)tick();
    assert(net.peer_n==1 && ctl_connected==1);
    cpu.r[4]=RAM+128;
    assert(ctl_state(&cpu)==0 && MEM_R32(RAM+128)==1);
    MEM_W32(RAM+128,0);
    cpu.r[4]=RAM+128;
    cpu.r[5]=0;
    assert(ctl_peer_list(&cpu)==0 && MEM_R32(RAM+128)==152);
    MEM_W32(RAM+128,152);
    MEM_W32(RAM+400,0x12345678);
    cpu.r[4]=RAM+128;
    cpu.r[5]=RAM+248;
    assert(ctl_peer_list(&cpu)==0 && MEM_R32(RAM+400)==0x12345678);
    cpu.r[4]=32768;
    assert(match_init(&cpu)==0);
    assert(match_init(&cpu)==MATCHERR(18));
    /* The title asks for five matching slots in both host and client modes.
     * PSP accepts 2..16, independently of our four-player outer lobby. */
    uint32_t limits[]={1,2,5,16,17};
    for(unsigned mode=1;mode<=2;mode++)for(unsigned n=0;n<5;n++) {
        uint32_t probe[]={mode,limits[n],1,4096,1000000,100000,10,500000,0x08802000};
        arguments(&cpu,probe,9);
        uint32_t id=match_create(&cpu);
        if(limits[n]<2 || limits[n]>16)assert(id==MATCHERR(3));
        else {
            assert(id==1);
            if(limits[n]==16) {
                Matching *context=matching(id);
                for(unsigned i=0;i<15;i++) {
                    uint8_t mac[6]={2,0,0,1,0,(uint8_t)(i+1)};
                    MatchPeer *peer=match_peer(context,mac,1);
                    assert(peer);peer->state=4;
                }
                assert(match_members(context)==16);
                context->running=1;
                uint32_t list[]={id,RAM+128,RAM+512};
                arguments(&cpu,list,3);MEM_W32(RAM+128,16*12);
                MEM_W32(RAM+512+16*12,0x12345678);
                assert(match_get_members(&cpu)==0 && MEM_R32(RAM+128)==16*12);
                assert(MEM_R32(RAM+512+16*12)==0x12345678);
                assert(MEM_R32(RAM+512+15*12)==0);
                context->running=0;
            }
            cpu.r[4]=id;assert(match_delete(&cpu)==0);
        }
    }
    for(unsigned i=0;i<768;i++)MEM_W8(OPTIONS+i,(uint8_t)(i*31));
    uint32_t create[]= {
        role==1?1:2,5,32001,4096,100000,200000,10,100000,0x08802000
    }
    ;
    arguments(&cpu,create,9);
    assert(match_create(&cpu)==1);
    uint32_t start[]= {
        1,16,0x1c00,8,0,768,OPTIONS
    }
    ;
    arguments(&cpu,start,7);
    cpu.r[8]=1;
    assert(match_start(&cpu)==MATCHERR(21));
    assert(!matching(1)->running);
    arguments(&cpu,start,7);
    assert(match_start(&cpu)==0);
    assert(matching(1)->running && matching(1)->hello_len==768);
    assert(services[matching(1)->thread-101].priority==16);
    tick();
    assert(services[matching(1)->thread-101].due==UINT64_MAX);
    assert(match_start(&cpu)==MATCHERR(10));
    while(!complete&&sched_vtime_us()<deadline)tick();
    assert(complete==1);
    uint32_t members[]= {
        1,RAM+128,0
    }
    ;
    arguments(&cpu,members,3);
    MEM_W32(RAM+128,0);
    assert(match_get_members(&cpu)==0 && MEM_R32(RAM+128)==24);
    if(role==1) {
        write_bytes(RAM+32,net.peers[0].mac,6);
        uint32_t send[]= {
            1,RAM+32,8,OPTIONS
        }
        ;
        arguments(&cpu,send,4);
        assert(match_send_data(&cpu)==0);
        assert(match_send_data(&cpu)==MATCHERR(24));
    }
    while(!(role==1?data_confirm:data_received)&&sched_vtime_us()<deadline)tick();
    assert(role==1?data_confirm==1:data_received==1);
    /* Real game-facing PDP argument marshalling and a short-buffer retry. */ write_bytes(RAM+32,net.mac,6);
    uint32_t pdp_args[]= {
        RAM+32,32002,4096,0
    }
    ;
    arguments(&cpu,pdp_args,4);
    uint32_t socket=pdp_create(&cpu);
    assert(socket>=1&&socket<=16);
    uint64_t settle=sched_vtime_deadline_after(150000);
    while(sched_vtime_us()<settle)tick();
    write_bytes(RAM+32,net.peers[0].mac,6);
    int sent=0,received=0;
    while(!received&&sched_vtime_us()<deadline) {
        if(role==1&&!sent) {
            uint32_t send[]= {
                socket,RAM+32,32002,OPTIONS,8,0,1
            }
            ;
            arguments(&cpu,send,7);
            assert(pdp_send(&cpu)==0);
            sent=1;
        }
        uint32_t receive[]= {
            socket,RAM+80,RAM+88,RAM+600,RAM+128,0,1
        }
        ;
        arguments(&cpu,receive,7);
        MEM_W32(RAM+128,1);
        uint32_t r=pdp_recv(&cpu);
        if(r==0x80400706u) {
            assert(MEM_R32(RAM+128)==8);
            MEM_W32(RAM+128,8);
            r=pdp_recv(&cpu);
        }
        if(!r) {
            received=1;
            assert(MEM_R16(RAM+88)==32002);
            for(unsigned i=0;i<8;i++)assert(MEM_R8(RAM+600+i)==(uint8_t)(i*31));
            if(role==2) {
                uint32_t send[]= {
                    socket,RAM+80,32002,RAM+600,8,0,1
                }
                ;
                arguments(&cpu,send,7);
                assert(pdp_send(&cpu)==0);
            }
        }
        else assert(r==NETERR(9));
        tick();
    }
    assert(received);
    settle=sched_vtime_deadline_after(200000);
    while(sched_vtime_us()<settle)tick();
    cpu.r[4]=socket;
    assert(pdp_delete(&cpu)==0);
    assert(pdp_delete(&cpu)==NETERR(1));
    assert(match_term(&cpu)==0);
    assert(ctl_term(&cpu)==0);
    assert(adhoc_term(&cpu)==0);
    loa_coop_transport_close();
    for(unsigned i=0;i<service_count;i++)DeleteFiber(services[i].fiber);
    free(g_mem);
    puts("PASS: real HLE, EABI, guest lists, native matching callbacks and receipt ACK, bidirectional PDP, cleanup");
    return 0;
}
