/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded local RGBA file adapter for the pinned, border-aware xBRZ scaler. */
#include <stdio.h>
#include <stdlib.h>
#include "tex_scale.h"
int main(int argc,char **argv) {
    if(argc!=8) { fprintf(stderr,"input.rgba output.rgba width height factor clamp_u clamp_v\n");return 2; }
    int values[5];
    for(int i=0;i<5;i++) {
        char *end=NULL;long value=strtol(argv[i+3],&end,10);
        if(!end || end==argv[i+3] || *end || value<0 || value>2048) return 2;
        values[i]=(int)value;
    }
    int w=values[0],h=values[1],f=values[2];
    if(w<1 || h<1 || w>512 || h>512 || f<2 || f>6 || w*f>2048 || h*f>2048 || values[3]>1 || values[4]>1) return 2;
    size_t n=(size_t)w*h;
    uint32_t *source=malloc(n*4),*scaled=malloc(n*f*f*4);
    if(!source || !scaled) { free(source);free(scaled);return 3; }
    FILE *in=fopen(argv[1],"rb");
    if(!in) { free(source);free(scaled);return 4; }
    int ok=fread(source,4,n,in)==n && fgetc(in)==EOF;fclose(in);
    if(ok) ok=nk_tex_scale_image(source,w,h,f,values[3],values[4],scaled);
    FILE *out=ok?fopen(argv[2],"wb"):NULL;
    if(out) { ok=fwrite(scaled,4,n*f*f,out)==n*f*f;if(fclose(out)!=0)ok=0; }
    else ok=0;
    free(source);free(scaled);
    return ok?0:5;
}
