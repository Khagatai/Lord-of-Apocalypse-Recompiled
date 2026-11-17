/* SPDX-License-Identifier: GPL-3.0-or-later
* Two independent native processes, synthetic payloads, loopback only. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "coop_transport.h"
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    int role=atoi(argv[1]);
    unsigned port=(unsigned)atoi(argv[2]);
    const uint8_t a[6]= {
        2,0,0,0,0,1
    }
    ,b[6]= {
        2,0,0,0,0,2
    }
    ;
    NkAdhocTransport *t=loa_coop_transport("127.0.0.1",port,role==1?"127.0.0.2":"127.0.0.3",10000);
    if(!t)return 3;
    const NkAdhocTransportOps *o=t->ops;
    if(o->login(t,role==1?a:b,role==1?"Synthetic host":"Synthetic guest","NPJH50503"))return 4;
    int h=o->pdp_open(t,31001);
    if(h<0)return 5;
    if(o->pdp_open(t,31001)!=NK_NET_PORT_IN_USE)return 6;
    uint8_t group[8]= {
        'L','O','A','T','E','S','T',0
    }
    ;
    if(o->connect(t,group))return 7;
    ULONGLONG deadline=GetTickCount64()+10000;
    int joined=0,peer=0,sent=0,received=0;
    uint8_t payload[2048],buffer[2048],mac[6];
    for(unsigned i=0;i<sizeof payload;i++)payload[i]=(uint8_t)(i*37u+19u);
    while(GetTickCount64()<deadline) {
        NkLobbyEvent events[8];
        size_t n=o->take_events(t,events,8);
        for(size_t i=0;i<n;i++) {
            joined|=events[i].kind==NK_LOBBY_CONNECT_BSSID;
            peer|=events[i].kind==NK_LOBBY_CONNECT;
        }
        if(!loa_coop_transport_alive())return 8;
        if(role==1 && joined && peer && !sent) {
            if(o->pdp_send(t,h,b,31001,payload,sizeof payload))return 9;
            sent=1;
        }
        uint32_t length=0;
        uint16_t from_port=0;
        int result=o->pdp_recv(t,h,mac,&from_port,buffer,role==2&&!received?2:sizeof buffer,&length);
        if(role==2 && result==NK_NET_SHORT_BUFFER) {
            if(length!=sizeof payload)return 10;
            result=o->pdp_recv(t,h,mac,&from_port,buffer,sizeof buffer,&length);
        }
        if(result==NK_NET_OK) {
            if(length!=sizeof payload||memcmp(buffer,payload,length)||memcmp(mac,role==1?b:a,6)||from_port!=31001)return 11;
            received=1;
            if(role==2 && o->pdp_send(t,h,a,31001,buffer,length))return 12;
            break;
        }
        if(result!=NK_NET_AGAIN && result!=NK_NET_NOT_IN_GROUP)return 13;
        Sleep(2);
    }
    if(!received)return 14;
    /* PTP uses real native TCP, including connect/accept and partial reads. */ uint16_t tcp_port=(uint16_t)(20000u+port%10000u);
    int tcp=loa_coop_ptp_open(role==1?tcp_port:(uint16_t)(tcp_port+1),role==1?NULL:a,role==1?0:tcp_port,role==1?4:0);
    if(tcp<0)return 16;
    int stream=-1;
    while(GetTickCount64()<deadline) {
        o->take_events(t,(NkLobbyEvent[8]) {
            {
                0
            }
        }
        ,8);
        int result=role==1?loa_coop_ptp_accept(tcp):loa_coop_ptp_connect(tcp);
        if(role==1 && result>=0) {
            stream=result;
            break;
        }
        if(role==2 && result==NK_NET_OK) {
            stream=tcp;
            break;
        }
        if(result!=NK_NET_AGAIN)return 17;
        Sleep(2);
    }
    if(stream<0)return 18;
    LoaPtpStat status;
    if(loa_coop_ptp_stat(stream,&status) || status.state!=4 || memcmp(status.peer,role==1?b:a,6))return 19;
    uint32_t written=0,read=0;
    while(GetTickCount64()<deadline && read<sizeof payload) {
        if(role==2 && written<sizeof payload) {
            uint32_t n=(uint32_t)sizeof payload-written;
            int r=loa_coop_ptp_send(stream,payload+written,&n);
            if(!r)written+=n;
            else if(r!=NK_NET_AGAIN)return 20;
        }
        uint32_t n=(uint32_t)sizeof buffer-read;
        int r=loa_coop_ptp_recv(stream,buffer+read,&n);
        if(!r)read+=n;
        else if(r!=NK_NET_AGAIN)return 21;
        if(role==1 && read==sizeof payload && written==0) {
            if(memcmp(buffer,payload,sizeof payload))return 22;
            while(written<sizeof payload && GetTickCount64()<deadline) {
                n=(uint32_t)sizeof payload-written;
                r=loa_coop_ptp_send(stream,payload+written,&n);
                if(!r)written+=n;
                else if(r!=NK_NET_AGAIN)return 23;
                Sleep(1);
            }
        }
        Sleep(2);
    }
    if(read!=sizeof payload || written!=sizeof payload || memcmp(buffer,payload,sizeof payload))return 24;
    if(loa_coop_ptp_close(stream))return 25;
    if(role==1 && loa_coop_ptp_close(tcp))return 26;
    /* Let the host receive before the peer logs out of the lobby. */ if(role==2)Sleep(100);
    if(o->pdp_close(t,h) || o->pdp_close(t,h)!=NK_NET_NO_SOCKET)return 15;
    o->logout(t);
    loa_coop_transport_close();
    puts("PASS: native lobby, peer MAC/IP, UDP reply, short-buffer retention, TCP connect/accept/reply, socket lifecycle");
    return 0;
}
