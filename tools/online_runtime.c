/* SPDX-License-Identifier: GPL-3.0-or-later
 * Local authenticated IPC to the owned room agent. Peer traffic is native WebRTC. */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <wincrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "online_runtime.h"
static SRWLOCK ipc_lock=SRWLOCK_INIT;
static SOCKET ipc=INVALID_SOCKET;
static int wsa;
int loa_online_available(void) {return getenv("LOA_ONLINE_PORT") && getenv("LOA_ONLINE_TOKEN");}
static int integer(const NkJsonNode *node,const char *key,int fallback) {
    int64_t value;
    return nk_json_get_int64(nk_json_obj_get(node,key),&value) && value>=-2147483647 && value<=2147483647?(int)value:fallback;
}
static const char *string(const NkJsonNode *node,const char *key) {
    const char *value=nk_json_get_string(nk_json_obj_get(node,key));return value?value:"";
}
int loa_online_result(const NkJsonNode *node) {return integer(node,"result",NK_NET_NOT_LOGGED_IN);}
NkJsonNode *loa_online_request(const char *fields) {
    if(!loa_online_available())return NULL;
    const char *token=getenv("LOA_ONLINE_TOKEN");
    if(strlen(token)>64 || strspn(token,"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")!=strlen(token))return NULL;
    char *wire=malloc(65536),*reply=malloc(65536);NkJsonNode *result=NULL;
    if(!wire || !reply) {free(wire);free(reply);return NULL;}
    int length=snprintf(wire,65536,"{\"token\":\"%s\",%s}\n",token,fields);
    if(length<=0 || length>=65536)goto done;
    AcquireSRWLockExclusive(&ipc_lock);
    if(!wsa) {WSADATA data;if(WSAStartup(MAKEWORD(2,2),&data))goto unlock;wsa=1;}
    if(ipc==INVALID_SOCKET) {
        unsigned port=(unsigned)strtoul(getenv("LOA_ONLINE_PORT"),NULL,10);
        if(!port || port>65535)goto unlock;
        ipc=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
        if(ipc==INVALID_SOCKET)goto unlock;
        DWORD timeout=250;int one=1;
        setsockopt(ipc,SOL_SOCKET,SO_RCVTIMEO,(char *)&timeout,sizeof timeout);
        setsockopt(ipc,SOL_SOCKET,SO_SNDTIMEO,(char *)&timeout,sizeof timeout);
        setsockopt(ipc,IPPROTO_TCP,TCP_NODELAY,(char *)&one,sizeof one);
        struct sockaddr_in address={0};address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);address.sin_port=htons((u_short)port);
        if(connect(ipc,(struct sockaddr *)&address,sizeof address))goto broken;
    }
    for(int sent=0;sent<length;) {int n=send(ipc,wire+sent,length-sent,0);if(n<=0)goto broken;sent+=n;}
    for(int received=0;received<65535;) {
        int n=recv(ipc,reply+received,65535-received,0);if(n<=0)goto broken;received+=n;
        if(reply[received-1]=='\n') {
            char error[120];result=nk_json_parse(reply,(size_t)received,error,sizeof error);break;
        }
    }
    if(!result)goto broken;
    goto unlock;
broken:
    closesocket(ipc);ipc=INVALID_SOCKET;
unlock:
    ReleaseSRWLockExclusive(&ipc_lock);
done:
    free(wire);free(reply);return result;
}
static int simple(const char *fields) {NkJsonNode *r=loa_online_request(fields);int v=loa_online_result(r);nk_json_free(r);return v;}
static void mac_string(const uint8_t *mac,char out[13]) {
    for(unsigned i=0;i<6;i++)sprintf(out+2*i,"%02x",mac?mac[i]:0);
    out[12]=0;
}
static int mac_read(const char *value,uint8_t out[6]) {
    if(strlen(value)!=12 || strspn(value,"0123456789abcdefABCDEF")!=12)return 0;
    for(unsigned i=0;i<6;i++){unsigned v;if(sscanf(value+2*i,"%2x",&v)!=1)return 0;out[i]=(uint8_t)v;}return 1;
}
static int encode(const void *data,uint32_t size,char *out,DWORD capacity) {
    return CryptBinaryToStringA(data,size,CRYPT_STRING_BASE64|CRYPT_STRING_NOCRLF,out,&capacity)!=0;
}
static int decode(const char *text,void *out,uint32_t capacity,uint32_t *size) {
    DWORD n=capacity;
    if(!CryptStringToBinaryA(text,0,CRYPT_STRING_BASE64,out,&n,NULL,NULL))return 0;
    *size=n;return 1;
}
static int login(NkAdhocTransport *base,const uint8_t mac[6],const char *nickname,const char *product) {
    (void)base;(void)nickname;char hex[13],request[160];mac_string(mac,hex);
    if(strcmp(product,"NPJH50503"))return NK_NET_BAD_ARG;
    snprintf(request,sizeof request,"\"op\":\"login\",\"mac\":\"%s\",\"product\":\"NPJH50503\"",hex);return simple(request);
}
static int logout(NkAdhocTransport *base) {(void)base;return simple("\"op\":\"logout\"");}
static int group(NkAdhocTransport *base,const uint8_t name[8]) {
    (void)base;char request[100],text[9]={0};memcpy(text,name,8);
    if(strspn(text,"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")!=strlen(text))return NK_NET_BAD_ARG;
    snprintf(request,sizeof request,"\"op\":\"group\",\"group\":\"%s\"",text);return simple(request);
}
static int leave(NkAdhocTransport *base) {(void)base;return simple("\"op\":\"disconnect\"");}
static int scan(NkAdhocTransport *base) {(void)base;return simple("\"op\":\"scan\"");}
static size_t events(NkAdhocTransport *base,NkLobbyEvent *out,size_t max) {
    (void)base;char request[80];if(max>8)max=8;
    snprintf(request,sizeof request,"\"op\":\"events\",\"max\":%u",(unsigned)max);
    NkJsonNode *r=loa_online_request(request);size_t count=0;
    if(loa_online_result(r)==0) {
        NkJsonNode *list=nk_json_obj_get(r,"events");size_t n=nk_json_array_count(list);if(n>max)n=max;
        for(size_t i=0;i<n;i++) {
            NkJsonNode *v=nk_json_array_get(list,i);NkLobbyEvent e={0};int kind=integer(v,"kind",0);
            if(kind<2 || kind>6)break;
            e.kind=(NkLobbyOpcode)kind;e.peer_id=(uint32_t)integer(v,"peer_id",0);
            if(kind==2 && !mac_read(string(v,"mac"),e.mac))break;
            if((kind==4 || kind==6) && !mac_read(string(v,"mac"),e.bssid))break;
            snprintf(e.nickname,sizeof e.nickname,"%s",string(v,"nickname"));
            const char *g=string(v,"group");memcpy(e.group,g,strlen(g)<8?strlen(g):8);out[count++]=e;
        }
    }
    nk_json_free(r);return count;
}
static uint32_t dropped(const NkAdhocTransport *base) {(void)base;return 0;}
static uint32_t pdp_dropped(const NkAdhocTransport *base) {
    (void)base;NkJsonNode *r=loa_online_request("\"op\":\"drops\"");
    uint32_t count=(uint32_t)integer(r,"pdp",0);nk_json_free(r);return count;
}
static int open_pdp(NkAdhocTransport *base,uint16_t port) {
    (void)base;char request[80];snprintf(request,sizeof request,"\"op\":\"pdp_open\",\"port\":%u",port);return simple(request);
}
static int close_pdp(NkAdhocTransport *base,int handle) {
    (void)base;char request[80];snprintf(request,sizeof request,"\"op\":\"pdp_close\",\"handle\":%d",handle);return simple(request);
}
static int send_pdp(NkAdhocTransport *base,int handle,const uint8_t mac[6],uint16_t port,const void *data,uint32_t size) {
    (void)base;if(size>10240)return NK_NET_TOO_BIG;char hex[13],encoded[14000],request[14300];mac_string(mac,hex);
    if(!encode(data,size,encoded,sizeof encoded))return NK_NET_BAD_ARG;
    snprintf(request,sizeof request,"\"op\":\"pdp_send\",\"handle\":%d,\"mac\":\"%s\",\"port\":%u,\"data\":\"%s\"",handle,hex,port,encoded);return simple(request);
}
static int recv_pdp(NkAdhocTransport *base,int handle,uint8_t mac[6],uint16_t *port,void *data,uint32_t capacity,uint32_t *size) {
    (void)base;char request[100];snprintf(request,sizeof request,"\"op\":\"pdp_recv\",\"handle\":%d,\"capacity\":%u",handle,capacity);
    NkJsonNode *r=loa_online_request(request);int result=loa_online_result(r);
    if(result==NK_NET_SHORT_BUFFER)*size=(uint32_t)integer(r,"size",0);
    if(result==0) {
        if(!mac_read(string(r,"mac"),mac) || !decode(string(r,"data"),data,capacity,size))result=NK_NET_BAD_ARG;
        else *port=(uint16_t)integer(r,"port",0);
    }
    nk_json_free(r);return result;
}
static const NkAdhocTransportOps ops={"native-webrtc",login,logout,group,leave,scan,events,dropped,open_pdp,send_pdp,recv_pdp,close_pdp,pdp_dropped};
static NkAdhocTransport transport={&ops};
NkAdhocTransport *loa_online_transport(void) {return loa_online_available()?&transport:NULL;}
int loa_online_alive(void) {
    NkJsonNode *r=loa_online_request("\"op\":\"status\"");int alive=loa_online_result(r)==0 && !strcmp(string(r,"state"),"in-room");nk_json_free(r);return alive;
}
void loa_online_close(void) {simple("\"op\":\"logout\"");}
static NkJsonNode *socket_stat(int handle,const char *kind) {
    char request[100];snprintf(request,sizeof request,"\"op\":\"%s_stat\",\"handle\":%d",kind,handle);return loa_online_request(request);
}
uint16_t loa_online_port(int handle) {NkJsonNode *r=socket_stat(handle,"pdp");uint16_t p=(uint16_t)integer(r,"port",0);nk_json_free(r);return p;}
uint32_t loa_online_pending(int handle) {NkJsonNode *r=socket_stat(handle,"pdp");uint32_t p=(uint32_t)integer(r,"pending",0);nk_json_free(r);return p;}
int loa_online_ptp_open(uint16_t local,const uint8_t peer[6],uint16_t remote,int backlog) {
    char hex[13],request[200];mac_string(peer,hex);snprintf(request,sizeof request,"\"op\":\"ptp_open\",\"port\":%u,\"remote\":%u,\"backlog\":%d,\"mac\":\"%s\"",local,remote,backlog,hex);return simple(request);
}
static int ptp_action(int handle,const char *operation) {char request[100];snprintf(request,sizeof request,"\"op\":\"ptp_%s\",\"handle\":%d",operation,handle);return simple(request);}
int loa_online_ptp_connect(int handle) {return ptp_action(handle,"connect");}
int loa_online_ptp_accept(int handle) {return ptp_action(handle,"accept");}
int loa_online_ptp_close(int handle) {return ptp_action(handle,"close");}
int loa_online_ptp_stat(int handle,LoaPtpStat *out) {
    NkJsonNode *r=socket_stat(handle,"ptp");int result=loa_online_result(r);
    if(result==0) {
        memset(out,0,sizeof *out);out->local_port=(uint16_t)integer(r,"port",0);out->peer_port=(uint16_t)integer(r,"remote",0);
        out->available=(uint32_t)integer(r,"pending",0);out->state=(uint32_t)integer(r,"state",0);mac_read(string(r,"mac"),out->peer);
    }
    nk_json_free(r);return result;
}
int loa_online_ptp_send(int handle,const void *data,uint32_t *size) {
    uint32_t n=*size>16384?16384:*size;char encoded[22000],request[22300];if(!encode(data,n,encoded,sizeof encoded))return NK_NET_BAD_ARG;
    snprintf(request,sizeof request,"\"op\":\"ptp_send\",\"handle\":%d,\"data\":\"%s\"",handle,encoded);
    NkJsonNode *r=loa_online_request(request);int result=loa_online_result(r);if(result==0)*size=(uint32_t)integer(r,"size",0);nk_json_free(r);return result;
}
int loa_online_ptp_recv(int handle,void *data,uint32_t *size) {
    uint32_t cap=*size>16384?16384:*size;char request[120];snprintf(request,sizeof request,"\"op\":\"ptp_recv\",\"handle\":%d,\"capacity\":%u",handle,cap);
    NkJsonNode *r=loa_online_request(request);int result=loa_online_result(r);if(result==0 && !decode(string(r,"data"),data,cap,size))result=NK_NET_BAD_ARG;nk_json_free(r);return result;
}
