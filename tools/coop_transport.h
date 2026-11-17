/* SPDX-License-Identifier: GPL-3.0-or-later
 * Title-owned Windows transport, written with Codex. */
#ifndef LOA_COOP_TRANSPORT_H
#define LOA_COOP_TRANSPORT_H
#include "nk_adhoc_net.h"
NkAdhocTransport *loa_coop_transport(const char *host,unsigned lobby_port,const char *bind_ip,unsigned offset);
void loa_coop_transport_close(void);
int loa_coop_transport_alive(void);
uint16_t loa_coop_socket_port(int handle);
uint32_t loa_coop_socket_pending(int handle);
typedef struct LoaPtpStat {uint8_t peer[6];uint16_t local_port,peer_port;uint32_t available,state;} LoaPtpStat;
int loa_coop_ptp_open(uint16_t local,const uint8_t peer[6],uint16_t remote,int backlog);
int loa_coop_ptp_connect(int handle);
int loa_coop_ptp_accept(int handle);
int loa_coop_ptp_close(int handle);
int loa_coop_ptp_stat(int handle,LoaPtpStat *out);
int loa_coop_ptp_send(int handle,const void *data,uint32_t *size);
int loa_coop_ptp_recv(int handle,void *data,uint32_t *size);
#endif
