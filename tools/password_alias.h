/* SPDX-License-Identifier: GPL-3.0-or-later
 * English aliases refer to message indices; no retail password bytes here. */
#ifndef LOA_PASSWORD_ALIAS_H
#define LOA_PASSWORD_ALIAS_H
#include <stdint.h>
#include <string.h>
typedef struct {const char *text; unsigned message;} LoaPasswordAlias;
static const LoaPasswordAlias loa_password_aliases[]={
    {"4gamer",0},{"vjump",1},{"gamewatch",2},{"magazine",3},
    {"gpara",4},{"squareenixchan",5},{"baki",6},{"gamespot",7},
    {"gangan",8},{"onlineplayerex",9},{"apocalypse",20},
    {"famitsu",21},{"dengekips",22}
};
static int loa_password_alias_index(const uint16_t *input,unsigned count){
    char ascii[33];
    if(!count||count>32)return -1;
    for(unsigned i=0;i<count;i++){
        unsigned c=input[i];
        if(c>=0xff01&&c<=0xff5e)c-=0xfee0; /* Game keyboard's full-width Latin. */
        if(c>='A'&&c<='Z')c+='a'-'A';
        if(!((c>='a'&&c<='z')||(c>='0'&&c<='9')))return -1;
        ascii[i]=(char)c;
    }
    ascii[count]=0;
    for(unsigned i=0;i<sizeof loa_password_aliases/sizeof *loa_password_aliases;i++)
        if(!strcmp(ascii,loa_password_aliases[i].text))return (int)loa_password_aliases[i].message;
    return -1;
}
#endif
