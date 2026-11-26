/* SPDX-License-Identifier: GPL-3.0-or-later
* Native Winsock implementation of the pinned NkAdhocTransport seam.
* Lobby serialization/parsing uses the pinned framework; PDP is direct UDP.
* Written with Codex. No guest data, addresses or networking emulation process. */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <mstcpip.h>
#include <mswsock.h>
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "coop_transport.h"
#include "online_runtime.h"
#pragma weak loa_online_available
#pragma weak loa_online_transport
#pragma weak loa_online_alive
#pragma weak loa_online_poll
#pragma weak loa_online_close
#pragma weak loa_online_port
#pragma weak loa_online_pending
#pragma weak loa_online_socket_info
#pragma weak loa_online_ptp_open
#pragma weak loa_online_ptp_connect
#pragma weak loa_online_ptp_accept
#pragma weak loa_online_ptp_close
#pragma weak loa_online_ptp_stat
#pragma weak loa_online_ptp_send
#pragma weak loa_online_ptp_recv
static int online_mode;
#define SLOTS NK_NET_PDP_SOCKETS
typedef struct  {
    NkAdhocTransport base;
    SOCKET lobby,udp[SLOTS];
    uint16_t ports[SLOTS];
    SOCKET tcp[SLOTS];
    LoaPtpStat tcp_stat[SLOTS];
    struct in_addr server,local;
    unsigned lobby_port,offset;
    uint8_t mac[6],rx[16384],tx[16384];
    size_t rx_n,tx_n;
    NkLobbyEvent events[64],peers[4];
    unsigned event_n,peer_n;
    uint32_t event_drops,pdp_drops;
    int wsa,in_group;
    ULONGLONG ping;
}
Transport;
static Transport transport;
static int nonblock(SOCKET socket) {
    u_long one=1;
    return ioctlsocket(socket,FIONBIO,&one)==0;
}
static void close_sockets(void) {
    Transport *t=&transport;
    if(t->lobby!=INVALID_SOCKET) {
        closesocket(t->lobby);
        t->lobby=INVALID_SOCKET;
    }
    for(unsigned i=0;i<SLOTS;i++)if(t->udp[i]!=INVALID_SOCKET) {
        closesocket(t->udp[i]);
        t->udp[i]=INVALID_SOCKET;
        t->ports[i]=0;
    }
    for(unsigned i=0;i<SLOTS;i++)if(t->tcp[i]!=INVALID_SOCKET) {
        closesocket(t->tcp[i]);
        t->tcp[i]=INVALID_SOCKET;
        memset(&t->tcp_stat[i],0,sizeof t->tcp_stat[i]);
    }
    t->rx_n=t->tx_n=t->event_n=t->peer_n=0;
    t->in_group=0;
}
void loa_coop_transport_close(void) {
    if(online_mode) {loa_online_close();online_mode=0;return;}
    if(!transport.wsa)return;
    close_sockets();
    if(transport.wsa) {
        WSACleanup();
        transport.wsa=0;
    }
}
static void failure(const char *where) {
    fprintf(stderr,"LOA_NET: transport disconnected (%s, Winsock=%d)\n",where,WSAGetLastError());
    close_sockets();
}
static int queue(const void *bytes,size_t n) {
    Transport *t=&transport;
    if(t->lobby==INVALID_SOCKET)return NK_NET_NOT_LOGGED_IN;
    if(n>sizeof t->tx-t->tx_n)return NK_NET_AGAIN;
    memcpy(t->tx+t->tx_n,bytes,n);
    t->tx_n+=n;
    return NK_NET_OK;
}
static void pump(void) {
    Transport *t=&transport;
    if(t->lobby==INVALID_SOCKET)return;
    if(GetTickCount64()-t->ping>=5000) {
        uint8_t ping=0;
        queue(&ping,1);
        t->ping=GetTickCount64();
    }
    if(t->tx_n) {
        int n=send(t->lobby,(const char *)t->tx,(int)t->tx_n,0);
        if(n>0) {
            memmove(t->tx,t->tx+n,t->tx_n-(size_t)n);
            t->tx_n-=n;
        }
        else if(n==0 || WSAGetLastError()!=WSAEWOULDBLOCK) {
            failure("send");
            return;
        }
    }
    for(unsigned attempt=0;attempt<8;attempt++) {
        if(t->rx_n==sizeof t->rx) {
            failure("lobby input limit");
            return;
        }
        int n=recv(t->lobby,(char *)t->rx+t->rx_n,(int)(sizeof t->rx-t->rx_n),0);
        if(n>0)t->rx_n+=n;
        else if(n==0) {
            failure("server closed");
            return;
        }
        else if(WSAGetLastError()!=WSAEWOULDBLOCK) {
            failure("receive");
            return;
        }
        else break;
    }
    size_t used=0;
    while(used<t->rx_n) {
        NkLobbyEvent event;
        int n=nk_lobby_parse(t->rx+used,t->rx_n-used,&event);
        if(n==NK_LOBBY_NEED_MORE)break;
        if(n<0) {
            failure("invalid lobby packet");
            return;
        }
        used+=(size_t)n;
        if(event.kind==NK_LOBBY_CONNECT) {
            unsigned i;
            for(i=0;i<t->peer_n;i++)if(t->peers[i].peer_id==event.peer_id)break;
            if(i>=4) {
                failure("peer limit");
                return;
            }
            t->peers[i]=event;
            if(i==t->peer_n)t->peer_n++;
        }
        else if(event.kind==NK_LOBBY_DISCONNECT) {
            for(unsigned i=0;i<t->peer_n;i++)if(t->peers[i].peer_id==event.peer_id) {
                t->peers[i]=t->peers[--t->peer_n];
                break;
            }
        }
        else if(event.kind==NK_LOBBY_CONNECT_BSSID)t->in_group=1;
        if(t->event_n<64)t->events[t->event_n++]=event;
        else t->event_drops++;
    }
    if(used) {
        memmove(t->rx,t->rx+used,t->rx_n-used);
        t->rx_n-=used;
    }
}
int loa_coop_transport_alive(void) {
    if(online_mode)return loa_online_alive();
    pump();
    return transport.lobby!=INVALID_SOCKET;
}
int loa_coop_poll(NkLobbyEvent *out,size_t max,size_t *count) {
    if(online_mode)return loa_online_poll(out,max,count);
    *count=transport.base.ops->take_events(&transport.base,out,max);
    return loa_coop_transport_alive();
}
static int login(NkAdhocTransport *base,const uint8_t mac[6],const char *nickname,const char *product) {
    (void)base;
    Transport *t=&transport;
    if(!nk_relay_mac_ok(mac)||!nk_relay_nickname_ok(nickname)||!nk_relay_product_ok(product))return NK_NET_BAD_ARG;
    if(t->lobby!=INVALID_SOCKET)return NK_NET_BAD_ARG;
    SOCKET s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(s==INVALID_SOCKET)return NK_NET_AGAIN;
    struct sockaddr_in local= {
        0
    }
    ,server= {
        0
    }
    ;
    local.sin_family=server.sin_family=AF_INET;
    local.sin_addr=t->local;
    server.sin_addr=t->server;
    server.sin_port=htons((u_short)t->lobby_port);
    if(bind(s,(struct sockaddr *)&local,sizeof local)||!nonblock(s)) {
        closesocket(s);
        return NK_NET_AGAIN;
    }
    int result=connect(s,(struct sockaddr *)&server,sizeof server);
    if(result && WSAGetLastError()!=WSAEWOULDBLOCK) {
        closesocket(s);
        return NK_NET_NOT_LOGGED_IN;
    }
    if(result) {
        WSAPOLLFD fd= {
            s,POLLWRNORM,0
        }
        ;
        int error=0,len=sizeof error;
        if(WSAPoll(&fd,1,500)<=0||getsockopt(s,SOL_SOCKET,SO_ERROR,(char *)&error,&len)||error) {
            closesocket(s);
            return NK_NET_NOT_LOGGED_IN;
        }
    }
    int one=1;
    setsockopt(s,IPPROTO_TCP,TCP_NODELAY,(char *)&one,sizeof one);
    t->lobby=s;
    t->event_drops=t->pdp_drops=0;
    t->ping=GetTickCount64();
    memcpy(t->mac,mac,6);
    uint8_t packet[NK_LOBBY_LOGIN_SIZE];
    nk_lobby_login(packet,mac,nickname,product);
    queue(packet,sizeof packet);
    pump();
    return t->lobby!=INVALID_SOCKET?NK_NET_OK:NK_NET_NOT_LOGGED_IN;
}
static int logout(NkAdhocTransport *t) {
    (void)t;
    close_sockets();
    return NK_NET_OK;
}
static int join(NkAdhocTransport *base,const uint8_t group[8]) {
    (void)base;
    uint8_t packet[9];
    if(transport.in_group)return NK_NET_BAD_ARG;
    nk_lobby_connect(packet,group);
    int r=queue(packet,sizeof packet);
    pump();
    return r;
}
static int leave(NkAdhocTransport *base) {
    (void)base;
    uint8_t packet=3;
    int r=queue(&packet,1);
    pump();
    transport.in_group=0;
    transport.peer_n=0;
    return r;
}
static int scan(NkAdhocTransport *base) {
    (void)base;
    uint8_t packet=4;
    if(transport.in_group)return NK_NET_BAD_ARG;
    int r=queue(&packet,1);
    pump();
    return r;
}
static size_t take_events(NkAdhocTransport *base,NkLobbyEvent *out,size_t max) {
    (void)base;
    pump();
    Transport *t=&transport;
    size_t n=t->event_n<max?t->event_n:max;
    memcpy(out,t->events,n*sizeof(*out));
    memmove(t->events,t->events+n,(t->event_n-n)*sizeof(*out));
    t->event_n-=(unsigned)n;
    return n;
}
static uint32_t events_dropped(const NkAdhocTransport *t) {
    (void)t;
    return transport.event_drops;
}
static int pdp_open(NkAdhocTransport *base,uint16_t port) {
    (void)base;
    Transport *t=&transport;
    if(t->lobby==INVALID_SOCKET)return NK_NET_NOT_LOGGED_IN;
    for(unsigned i=0;i<SLOTS;i++)if(t->udp[i]!=INVALID_SOCKET && t->ports[i]==port && port)return NK_NET_PORT_IN_USE;
    for(unsigned i=0;i<SLOTS;i++)if(t->udp[i]==INVALID_SOCKET) {
        uint16_t chosen=port?port:(uint16_t)(40000u+i);
        SOCKET s=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
        if(s==INVALID_SOCKET)return NK_NET_NO_SLOT;
        /* A peer may not have opened its matching port yet. An ICMP port
        * unreachable must not permanently disable a connectionless socket. */
        BOOL report_reset=FALSE;
        DWORD returned=0;
        if(WSAIoctl(s,SIO_UDP_CONNRESET,&report_reset,sizeof report_reset,NULL,0,&returned,NULL,NULL)) {
            closesocket(s);
            return NK_NET_BAD_ARG;
        }
        struct sockaddr_in local= {
            0
        }
        ;
        local.sin_family=AF_INET;
        local.sin_addr=t->local;
        local.sin_port=htons((uint16_t)(chosen+t->offset));
        if(bind(s,(struct sockaddr *)&local,sizeof local)) {
            int e=WSAGetLastError();
            closesocket(s);
            return e==WSAEADDRINUSE?NK_NET_PORT_IN_USE:NK_NET_BAD_ARG;
        }
        if(!nonblock(s)) {
            closesocket(s);
            return NK_NET_BAD_ARG;
        }
        t->udp[i]=s;
        t->ports[i]=chosen;
        return (int)i;
    }
    return NK_NET_NO_SLOT;
}
uint16_t loa_coop_socket_port(int handle) {
    if(online_mode)return loa_online_port(handle);
    return handle>=0 && handle<(int)SLOTS?transport.ports[handle]:0;
}
uint32_t loa_coop_socket_pending(int handle) {
    if(online_mode)return loa_online_pending(handle);
    u_long bytes=0;
    if(handle>=0 && handle<(int)SLOTS && transport.udp[handle]!=INVALID_SOCKET)ioctlsocket(transport.udp[handle],FIONREAD,&bytes);
    return (uint32_t)bytes;
}
int loa_coop_socket_info(int handle,uint16_t *port,uint32_t *pending) {
    if(online_mode)return loa_online_socket_info(handle,port,pending);
    if(handle<0 || handle>=(int)SLOTS || transport.udp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    u_long bytes=0;
    if(ioctlsocket(transport.udp[handle],FIONREAD,&bytes))return NK_NET_BAD_ARG;
    *port=transport.ports[handle];*pending=(uint32_t)bytes;return NK_NET_OK;
}
static int pdp_send(NkAdhocTransport *base,int handle,const uint8_t mac[6],uint16_t port,const void *data,uint32_t len) {
    (void)base;
    Transport *t=&transport;
    pump();
    if(handle<0||handle>=(int)SLOTS||t->udp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    if(t->lobby==INVALID_SOCKET)return NK_NET_NOT_LOGGED_IN;
    if(!t->in_group)return NK_NET_NOT_IN_GROUP;
    if(len>NK_RELAY_PDP_MAX)return NK_NET_TOO_BIG;
    for(unsigned i=0;i<t->peer_n;i++)if(!memcmp(t->peers[i].mac,mac,6)) {
        struct sockaddr_in target= {
            0
        }
        ;
        target.sin_family=AF_INET;
        target.sin_addr.s_addr=t->peers[i].peer_id;
        target.sin_port=htons((uint16_t)(port+t->offset));
        int n=sendto(t->udp[handle],data,(int)len,0,(struct sockaddr *)&target,sizeof target);
        return n==(int)len?NK_NET_OK:WSAGetLastError()==WSAEWOULDBLOCK?NK_NET_AGAIN:NK_NET_BAD_ARG;
    }
    return NK_NET_BAD_ARG;
}
static int pdp_recv(NkAdhocTransport *base,int handle,uint8_t mac[6],uint16_t *port,void *buf,uint32_t cap,uint32_t *len) {
    (void)base;
    Transport *t=&transport;
    pump();
    if(handle<0||handle>=(int)SLOTS||t->udp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    if(t->lobby==INVALID_SOCKET)return NK_NET_NOT_LOGGED_IN;
    if(!t->in_group)return NK_NET_NOT_IN_GROUP;
    uint8_t packet[NK_RELAY_PDP_MAX];
    struct sockaddr_in source;
    int size=sizeof source;
    int n=recvfrom(t->udp[handle],(char *)packet,sizeof packet,MSG_PEEK,(struct sockaddr *)&source,&size);
    if(n<0)return WSAGetLastError()==WSAEWOULDBLOCK?NK_NET_AGAIN:NK_NET_BAD_ARG;
    for(unsigned i=0;i<t->peer_n;i++)if(source.sin_addr.s_addr==t->peers[i].peer_id) {
        *len=(uint32_t)n;
        if(cap<(uint32_t)n)return NK_NET_SHORT_BUFFER;
        n=recvfrom(t->udp[handle],buf,(int)cap,0,(struct sockaddr *)&source,&size);
        if(n<0)return NK_NET_BAD_ARG;
        memcpy(mac,t->peers[i].mac,6);
        *port=(uint16_t)(ntohs(source.sin_port)-t->offset);
        *len=(uint32_t)n;
        return NK_NET_OK;
    }
    recvfrom(t->udp[handle],(char *)packet,sizeof packet,0,(struct sockaddr *)&source,&size);
    t->pdp_drops++;
    return NK_NET_AGAIN;
}
static int pdp_close(NkAdhocTransport *base,int handle) {
    (void)base;
    if(handle<0||handle>=(int)SLOTS||transport.udp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    closesocket(transport.udp[handle]);
    transport.udp[handle]=INVALID_SOCKET;
    transport.ports[handle]=0;
    return NK_NET_OK;
}
static uint32_t pdp_dropped(const NkAdhocTransport *base) {
    (void)base;
    return transport.pdp_drops;
}
static const NkAdhocTransportOps ops= {
    "windows-lan",login,logout,join,leave,scan,take_events,events_dropped,pdp_open,pdp_send,pdp_recv,pdp_close,pdp_dropped
}
;
NkAdhocTransport *loa_coop_transport(const char *host,unsigned lobby_port,const char *bind_ip,unsigned offset) {
    if(loa_online_available && loa_online_available()) {
        online_mode=1;return loa_online_transport();
    }
    online_mode=0;
    if(transport.wsa)loa_coop_transport_close();
    memset(&transport,0,sizeof transport);
    transport.lobby=INVALID_SOCKET;
    for(unsigned i=0;i<SLOTS;i++)transport.udp[i]=transport.tcp[i]=INVALID_SOCKET;
    if(lobby_port<1||lobby_port>65535||offset>65535||inet_pton(AF_INET,host,&transport.server)!=1||inet_pton(AF_INET,bind_ip,&transport.local)!=1)return NULL;
    WSADATA data;
    if(WSAStartup(MAKEWORD(2,2),&data))return NULL;
    transport.wsa=1;
    transport.base.ops=&ops;
    transport.lobby_port=lobby_port;
    transport.offset=offset;
    return &transport.base;
}
static uint32_t peer_ip(const uint8_t mac[6]) {
    for(unsigned i=0;i<transport.peer_n;i++)if(!memcmp(mac,transport.peers[i].mac,6))return transport.peers[i].peer_id;
    return 0;
}
int loa_coop_ptp_open(uint16_t local_port,const uint8_t mac[6],uint16_t peer_port,int backlog) {
    if(online_mode)return loa_online_ptp_open(local_port,mac,peer_port,backlog);
    Transport *t=&transport;
    if(t->lobby==INVALID_SOCKET)return NK_NET_NOT_LOGGED_IN;
    for(unsigned i=0;i<SLOTS;i++)if(t->tcp[i]==INVALID_SOCKET) {
        SOCKET s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
        if(s==INVALID_SOCKET)return NK_NET_NO_SLOT;
        struct sockaddr_in address= {
            0
        }
        ;
        address.sin_family=AF_INET;
        address.sin_addr=t->local;
        uint16_t port=local_port?local_port:(uint16_t)(42000u+i);
        address.sin_port=htons((uint16_t)(port+t->offset));
        if(bind(s,(struct sockaddr *)&address,sizeof address)) {
            int error=WSAGetLastError();
            closesocket(s);
            return error==WSAEADDRINUSE?NK_NET_PORT_IN_USE:NK_NET_BAD_ARG;
        }
        if(!nonblock(s) || (backlog && listen(s,backlog))) {
            closesocket(s);
            return NK_NET_BAD_ARG;
        }
        int one=1;
        setsockopt(s,IPPROTO_TCP,TCP_NODELAY,(char *)&one,sizeof one);
        t->tcp[i]=s;
        memset(&t->tcp_stat[i],0,sizeof t->tcp_stat[i]);
        t->tcp_stat[i].local_port=port;
        t->tcp_stat[i].peer_port=peer_port;
        t->tcp_stat[i].state=backlog?1:0;
        if(mac)memcpy(t->tcp_stat[i].peer,mac,6);
        return (int)i;
    }
    return NK_NET_NO_SLOT;
}
int loa_coop_ptp_connect(int handle) {
    if(online_mode)return loa_online_ptp_connect(handle);
    Transport *t=&transport;
    pump();
    if(handle<0||handle>=(int)SLOTS||t->tcp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    LoaPtpStat *info=&t->tcp_stat[handle];
    if(info->state==4)return NK_NET_OK;
    if(info->state==1)return NK_NET_BAD_ARG;
    if(info->state==0) {
        uint32_t ip=peer_ip(info->peer);
        if(!ip)return NK_NET_NOT_IN_GROUP;
        struct sockaddr_in target= {
            0
        }
        ;
        target.sin_family=AF_INET;
        target.sin_addr.s_addr=ip;
        target.sin_port=htons((uint16_t)(info->peer_port+t->offset));
        int r=connect(t->tcp[handle],(struct sockaddr *)&target,sizeof target);
        if(!r) {
            info->state=4;
            return NK_NET_OK;
        }
        if(WSAGetLastError()!=WSAEWOULDBLOCK && WSAGetLastError()!=WSAEINPROGRESS)return NK_NET_BAD_ARG;
        info->state=2;
    }
    WSAPOLLFD fd= {
        t->tcp[handle],POLLWRNORM,0
    }
    ;
    int n=WSAPoll(&fd,1,0);
    if(n<0)return NK_NET_BAD_ARG;
    if(!n)return NK_NET_AGAIN;
    int error=0,size=sizeof error;
    if(getsockopt(t->tcp[handle],SOL_SOCKET,SO_ERROR,(char *)&error,&size)||error)return NK_NET_BAD_ARG;
    info->state=4;
    return NK_NET_OK;
}
int loa_coop_ptp_accept(int handle) {
    if(online_mode)return loa_online_ptp_accept(handle);
    Transport *t=&transport;
    pump();
    if(handle<0||handle>=(int)SLOTS||t->tcp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    if(t->tcp_stat[handle].state!=1)return NK_NET_BAD_ARG;
    struct sockaddr_in source;
    int size=sizeof source;
    SOCKET s=accept(t->tcp[handle],(struct sockaddr *)&source,&size);
    if(s==INVALID_SOCKET)return WSAGetLastError()==WSAEWOULDBLOCK?NK_NET_AGAIN:NK_NET_BAD_ARG;
    unsigned peer;
    for(peer=0;peer<t->peer_n;peer++)if(t->peers[peer].peer_id==source.sin_addr.s_addr)break;
    if(peer==t->peer_n || !nonblock(s)) {
        closesocket(s);
        return NK_NET_BAD_ARG;
    }
    int one=1;
    setsockopt(s,IPPROTO_TCP,TCP_NODELAY,(char *)&one,sizeof one);
    for(unsigned i=0;i<SLOTS;i++)if(t->tcp[i]==INVALID_SOCKET) {
        t->tcp[i]=s;
        t->tcp_stat[i]=t->tcp_stat[handle];
        t->tcp_stat[i].state=4;
        memcpy(t->tcp_stat[i].peer,t->peers[peer].mac,6);
        t->tcp_stat[i].peer_port=(uint16_t)(ntohs(source.sin_port)-t->offset);
        return (int)i;
    }
    closesocket(s);
    return NK_NET_NO_SLOT;
}
int loa_coop_ptp_close(int handle) {
    if(online_mode)return loa_online_ptp_close(handle);
    if(handle<0||handle>=(int)SLOTS||transport.tcp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    closesocket(transport.tcp[handle]);
    transport.tcp[handle]=INVALID_SOCKET;
    memset(&transport.tcp_stat[handle],0,sizeof(LoaPtpStat));
    return NK_NET_OK;
}
int loa_coop_ptp_stat(int handle,LoaPtpStat *out) {
    if(online_mode)return loa_online_ptp_stat(handle,out);
    if(handle<0||handle>=(int)SLOTS||transport.tcp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    *out=transport.tcp_stat[handle];
    u_long bytes=0;
    if(ioctlsocket(transport.tcp[handle],FIONREAD,&bytes))return NK_NET_BAD_ARG;
    out->available=(uint32_t)bytes;
    return NK_NET_OK;
}
int loa_coop_ptp_send(int handle,const void *data,uint32_t *size) {
    if(online_mode)return loa_online_ptp_send(handle,data,size);
    if(handle<0||handle>=(int)SLOTS||transport.tcp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    if(transport.tcp_stat[handle].state!=4)return NK_NET_NOT_IN_GROUP;
    int n=send(transport.tcp[handle],data,(int)*size,0);
    if(n<0)return WSAGetLastError()==WSAEWOULDBLOCK?NK_NET_AGAIN:NK_NET_BAD_ARG;
    *size=(uint32_t)n;
    return NK_NET_OK;
}
int loa_coop_ptp_recv(int handle,void *data,uint32_t *size) {
    if(online_mode)return loa_online_ptp_recv(handle,data,size);
    if(handle<0||handle>=(int)SLOTS||transport.tcp[handle]==INVALID_SOCKET)return NK_NET_NO_SOCKET;
    if(transport.tcp_stat[handle].state!=4)return NK_NET_NOT_IN_GROUP;
    int n=recv(transport.tcp[handle],data,(int)*size,0);
    if(n<0)return WSAGetLastError()==WSAEWOULDBLOCK?NK_NET_AGAIN:NK_NET_BAD_ARG;
    if(!n) {
        transport.tcp_stat[handle].state=0;
        return NK_NET_NOT_IN_GROUP;
    }
    *size=(uint32_t)n;
    return NK_NET_OK;
}
