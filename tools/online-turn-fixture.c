/* SPDX-License-Identifier: GPL-3.0-or-later
 * Loopback-only TURN fixture using the pinned libjuice server, synthetic credentials. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "juice/juice.h"
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    juice_set_log_level(JUICE_LOG_LEVEL_ERROR);
    juice_server_credentials_t credential={"loa-test","synthetic-local-test",8};
    juice_server_config_t config={0};config.credentials=&credential;config.credentials_count=1;
    config.max_allocations=8;config.max_peers=16;config.bind_address="127.0.0.1";
    config.external_address="127.0.0.1";config.realm="loa-local-test";
    juice_server_t *server=juice_server_create(&config);
    if(!server)return 3;
    FILE *file=fopen(argv[1],"wb");if(!file){juice_server_destroy(server);return 4;}
    fprintf(file,"{\"port\":%u}",juice_server_get_port(server));fclose(file);
    (void)getchar();juice_server_destroy(server);return 0;
}
