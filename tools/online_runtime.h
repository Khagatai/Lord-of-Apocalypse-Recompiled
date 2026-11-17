/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef LOA_ONLINE_RUNTIME_H
#define LOA_ONLINE_RUNTIME_H
#include "coop_transport.h"
#include "nk_json.h"
int loa_online_available(void);
NkJsonNode *loa_online_request(const char *fields);
int loa_online_result(const NkJsonNode *node);
NkAdhocTransport *loa_online_transport(void);
int loa_online_alive(void);
void loa_online_close(void);
uint16_t loa_online_port(int handle);
uint32_t loa_online_pending(int handle);
int loa_online_ptp_open(uint16_t local,const uint8_t peer[6],uint16_t remote,int backlog);
int loa_online_ptp_connect(int handle);
int loa_online_ptp_accept(int handle);
int loa_online_ptp_close(int handle);
int loa_online_ptp_stat(int handle,LoaPtpStat *out);
int loa_online_ptp_send(int handle,const void *data,uint32_t *size);
int loa_online_ptp_recv(int handle,void *data,uint32_t *size);
#endif
