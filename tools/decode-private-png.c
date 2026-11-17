/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded local PNG decoder using the pinned framework's separate stb dependency. */
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_MAX_DIMENSIONS 4096
#include "stb_image.h"
#include <stdio.h>
#include <stdlib.h>

static int number(const char *s) {
    char *end; long n = strtol(s, &end, 10);
    return !*s || *end || n < 0 || n > 4096 ? -1 : (int)n;
}
int main(int argc, char **argv) {
    if (argc != 9) return 2;
    int ew=number(argv[3]),eh=number(argv[4]),x=number(argv[5]),y=number(argv[6]);
    int cw=number(argv[7]),ch=number(argv[8]);
    if (ew<=0 || eh<=0 || x<0 || y<0 || cw<=0 || ch<=0 || x+cw>ew || y+ch>eh) return 2;
    FILE *input=fopen(argv[1],"rb");
    if (!input || fseek(input,0,SEEK_END)) { if(input)fclose(input);return 3; }
    long size=ftell(input); fclose(input);
    if (size<8 || size>128L*1024L*1024L) return 3;
    int w,h,n; unsigned char *pixels=stbi_load(argv[1],&w,&h,&n,4);
    if (!pixels || w!=ew || h!=eh) { stbi_image_free(pixels);return 4; }
    FILE *output=fopen(argv[2],"wb");
    if (!output) { stbi_image_free(pixels);return 5; }
    int ok=1;
    for(int row=0;row<ch;row++) {
        const unsigned char *p=pixels+((size_t)(y+row)*w+x)*4u;
        if(fwrite(p,4u,(size_t)cw,output)!=(size_t)cw){ok=0;break;}
    }
    if(fclose(output))ok=0;
    stbi_image_free(pixels);
    return ok?0:6;
}
