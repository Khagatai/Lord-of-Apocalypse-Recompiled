/* SPDX-License-Identifier: GPL-3.0-or-later; exact integer/alpha detail kernel. */
static void detail(const unsigned char *src,unsigned char *out,int w,int h){
    const int kernel[5]={1,4,6,4,1};
    for(int y=0;y<h;y++)for(int x=0;x<w;x++){
        size_t at=((size_t)y*w+x)*4u;
        for(int c=0;c<3;c++){
            int sum=0,weight=0;
            for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++){
                int sx=x+dx,sy=y+dy;
                if(sx<0)sx=0;if(sx>=w)sx=w-1;if(sy<0)sy=0;if(sy>=h)sy=h-1;
                size_t from=((size_t)sy*w+sx)*4u;
                int k=kernel[dx+2]*kernel[dy+2]*src[from+3];
                sum+=k*src[from+c];weight+=k;
            }
            int delta=weight?(src[at+c]-(sum+weight/2)/weight):0;
            /* 25% detail, capped at 6/255; avoid sharpening invisible RGB. */
            delta=src[at+3]?delta/4:0;
            if(delta>6)delta=6;if(delta< -6)delta= -6;
            int value=src[at+c]+delta;out[at+c]=value<0?0:value>255?255:value;
        }
        out[at+3]=src[at+3];
    }
}
