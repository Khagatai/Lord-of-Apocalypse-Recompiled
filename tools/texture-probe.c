/* SPDX-License-Identifier: GPL-3.0-or-later
 * Codex-authored, diagnostic-only texture identity/decoded-image observer.
 * Never linked into the normal release. Every lookup delegates unchanged. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include "texrepl.h"
#include "ge_shared.h"
#include "ge_scene.h"
#include "recomp.h"

/* Separate bounded capture of actually bound single-level 3D art. The normal
 * executable never links this observer. All decoding delegates to the real GE. */
static void art_capture(NkTexRepl *pack,const NkTexReplId *id) {
    static int enabled=-1;
    static char seen[512][64];
    static unsigned count;
    if(enabled<0) enabled=getenv("LOA_ART_CAPTURE") && strcmp(getenv("LOA_ART_CAPTURE"),"1")==0;
    if(!enabled || count>=512) return;
    const GeState *g=ge_state_ptr();
    int through=(g->vtype&0x800000u)!=0;
    int ui=getenv("LOA_ART_CAPTURE_UI") && !strcmp(getenv("LOA_ART_CAPTURE_UI"),"1");
    if(!g->tex_enable || g->tex_max_level || (through && (!ui || g->tex_w<64 || g->tex_h<64)) ||
       g->tex_w<32 || g->tex_h<32 || g->tex_w>512 || g->tex_h>512) return;
    NkTexReplId measured=*id;
    if(getenv("LOA_SAMPLER_PACK") && !strcmp(getenv("LOA_SAMPLER_PACK"),"1")) {
        static const unsigned bits[8]={16,16,16,32,4,8,16,32};
        if(g->tex_fmt>7u || g->tex_bufw<(uint32_t)g->tex_w || g->tex_bufw>512u)return;
        size_t bytes=(size_t)g->tex_bufw*g->tex_h*bits[g->tex_fmt]/8;
        uint8_t *source=malloc(bytes);
        if(!source)return;
        if(!sr_guest_copy_in(source,id->addr,bytes)){free(source);return;}
        measured.hash=nk_texrepl_hash_texture(pack,source,bytes,id->addr,(int)g->tex_bufw,g->tex_w,g->tex_h,g->tex_fmt,0);
        free(source);measured.clut_hash=0;
        if(g->tex_fmt&4u) {
            uint32_t last=0,max=0;ge_clut_load_extent(&last,&max);
            measured.clut_hash=nk_texrepl_clut_identity(g->clutram,(uint32_t)sizeof(g->clutram),g->clut_fmt,g->tex_fmt,last,max);
        }
        id=&measured;
    }
    size_t pixels=(size_t)g->tex_w*g->tex_h;
    uint32_t *rgba=malloc(pixels*4);
    if(!rgba) return;
    int decoded=ge_vram_decode_bound_texture(rgba,pixels);
    uint64_t fingerprint=14695981039346656037ull;
    if(decoded) for(size_t i=0;i<pixels;i++) {
        uint32_t v=rgba[i];
        for(unsigned b=0;b<4;b++) { fingerprint=(fingerprint^(v&255u))*1099511628211ull;v>>=8; }
    }
    char key[25],identity[64],file[100];
    uint64_t cache=nk_texrepl_cache_key(id->addr,id->format,id->dim,id->clut_hash);
    snprintf(key,sizeof key,"%016" PRIx64 "%08" PRIx32,cache,id->hash);
    snprintf(identity,sizeof identity,"%s-%016" PRIx64 "-%03x",key,fingerprint,g->tex_wrap&0x101u);
    for(unsigned i=0;i<count;i++) if(!strcmp(seen[i],identity)) { free(rgba);return; }
    strcpy(seen[count++],identity);
    snprintf(file,sizeof file,"art-%s.rgba",identity);
    int written=0;
    if(decoded) {
        FILE *out=fopen(file,"wb");
        if(out) { written=fwrite(rgba,4,pixels,out)==pixels;if(fclose(out)!=0) written=0; }
    }
    free(rgba);
    FILE *metadata=fopen("art-capture.jsonl","ab");
    if(metadata) {
        fprintf(metadata,"{\"key\":\"%s\",\"content\":\"%016" PRIx64 "\",\"wrap\":%u,\"level\":0,\"levels\":1,\"width\":%d,\"height\":%d,\"format\":%u,\"through\":%s,\"file\":\"%s\",\"decoded\":%s,\"written\":%s}\n",
            key,fingerprint,g->tex_wrap&0x101u,g->tex_w,g->tex_h,id->format,through?"true":"false",file,decoded?"true":"false",written?"true":"false");
        fclose(metadata);
    }
}

/* Observe the RGBA returned to the GPU cache, without changing a texel. Calls
 * inside ge.c's viewer are not link-wrapped, keeping this separate from previews. */
void __real_ge_decode_tex_rgba(uint32_t *out);
void __wrap_ge_decode_tex_rgba(uint32_t *out) {
    __real_ge_decode_tex_rgba(out);
    static int gate=-1;
    static uint32_t addresses[256], hashes[256];
    static unsigned count;
    if(gate<0) gate=getenv("LOA_GPU_FONT_UPLOAD")!=NULL;
    if(!gate || !out || count>=256) return;
    const GeState *g=ge_state_ptr();
    int width=g->tex_w,height=g->tex_h;
    if(width<=0 || height<=0 || width>128 || height>128) return;
    size_t pixels=(size_t)width*(size_t)height;
    uint32_t hash=2166136261u;
    unsigned ink=0;
    for(size_t i=0;i<pixels;i++) { hash=(hash^out[i])*16777619u; ink+=(out[i]>>24)!=0; }
    for(unsigned i=0;i<count;i++) if(addresses[i]==g->tex_addr && hashes[i]==hash) return;
    addresses[count]=g->tex_addr; hashes[count++]=hash;
    char name[100]; snprintf(name,sizeof name,"gpu-font-%08" PRIx32 "-%08" PRIx32 ".rgba",g->tex_addr,hash);
    FILE *image=fopen(name,"wb"); int written=0;
    if(image) { written=fwrite(out,4,pixels,image)==pixels; if(fclose(image)!=0) written=0; }
    FILE *metadata=fopen("gpu-font-upload.jsonl","ab");
    if(metadata) {
        fprintf(metadata,"{\"address\":\"%08" PRIx32 "\",\"fingerprint\":\"%08" PRIx32 "\",\"format\":%u,\"clut_format\":%u,\"width\":%d,\"height\":%d,\"alpha_nonzero\":%u,\"decoded\":%s}\n",
                g->tex_addr,hash,g->tex_fmt,g->clut_fmt,width,height,ink,written?"true":"false");
        fclose(metadata);
    }
}

/* Observe a late, actually drawn frame rather than the cache's first upload.
 * A freshly allocated glyph buffer can be empty during that first upload. */
static void font_scene(const GeSceneRecord *record, void *user) {
    static uint32_t frame;
    static uint32_t addresses[128], hashes[128];
    static unsigned seen;
    (void)user;
    if(record->frame<970 || record->frame>1000 || record->version!=GE_SCENE_RECORD_VERSION) return;
    if(!frame) frame=record->frame;
    if(record->frame!=frame || !record->ge->tex_enable || seen>=128) return;
    const GeState *g=record->ge;
    int width=g->tex_w,height=g->tex_h;
    if(width<=0 || height<=0 || width>512 || height>512) return;
    size_t pixels=(size_t)width*(size_t)height;
    uint32_t *rgba=malloc(pixels*4);
    if(!rgba || !ge_vram_decode_bound_texture(rgba,pixels)) { free(rgba); return; }
    uint32_t fingerprint=2166136261u;
    unsigned ink=0;
    for(size_t i=0;i<pixels;i++) { fingerprint=(fingerprint^rgba[i])*16777619u; ink+=(rgba[i]>>24)!=0; }
    for(unsigned i=0;i<seen;i++) if(addresses[i]==g->tex_addr && hashes[i]==fingerprint) { free(rgba); return; }
    addresses[seen]=g->tex_addr; hashes[seen++]=fingerprint;
    char name[100]; snprintf(name,sizeof name,"font-scene-%08" PRIx32 "-%08" PRIx32 ".rgba",g->tex_addr,fingerprint);
    FILE *image=fopen(name,"wb");
    int decoded=0;
    if(image) { decoded=fwrite(rgba,4,pixels,image)==pixels; if(fclose(image)!=0) decoded=0; }
    free(rgba);
    GeSceneVertex vertex={0};
    int have_vertex=record->count && ge_scene_vertex(record,0,&vertex);
    FILE *metadata=fopen("font-scene.jsonl","ab");
    if(metadata) {
        fprintf(metadata,"{\"frame\":%u,\"address\":\"%08" PRIx32 "\",\"fingerprint\":\"%08" PRIx32 "\",\"format\":%u,\"width\":%d,\"height\":%d,\"alpha_nonzero\":%u,\"type\":%u,\"through\":%u,\"vertex_count\":%u,\"have_vertex\":%s,\"first_xy\":[%.3f,%.3f],\"decoded\":%s}\n",
          frame,g->tex_addr,fingerprint,g->tex_fmt,width,height,ink,record->type,record->through,record->count,
          have_vertex?"true":"false",vertex.pos[0],vertex.pos[1],decoded?"true":"false");
        fclose(metadata);
    }
}

int __real_nk_texrepl_lookup(NkTexRepl *, const NkTexReplId *, NkTexReplHit *);
int __wrap_nk_texrepl_lookup(NkTexRepl *pack, const NkTexReplId *id, NkTexReplHit *hit) {
    art_capture(pack,id);
    /* Title-specific, read-only ASCII atlas inspection. Anchor this diagnostic to
     * an actually observed R/S page, not a presumed PSP memory base. */
    static int atlas_saved;
    if(!atlas_saved && getenv("LOA_GPU_FONT_UPLOAD") && id->format==4 &&
       id->dim==0x405 && id->hash==0x39c4625cu) {
        uint32_t start=id->addr-25u*256u;
        unsigned char atlas[48*256];
        if(sr_guest_copy_in(atlas,start,sizeof atlas)) {
            FILE *f=fopen("ascii-atlas.raw","wb");
            if(f) { fwrite(atlas,1,sizeof atlas,f); fclose(f); }
            f=fopen("ascii-atlas.jsonl","wb");
            if(f) {
                for(unsigned i=0;i<48;i++) {
                    uint32_t addr=start+i*256u;
                    uint64_t cache=nk_texrepl_cache_key(addr,id->format,id->dim,id->clut_hash);
                    uint32_t hash=nk_texrepl_hash_texture(pack,atlas+i*256u,256,addr,32,32,16,4,0);
                    fprintf(f,"{\"first_code\":%u,\"key\":\"%016" PRIx64 "%08" PRIx32 "\"}\n",32+i*2,cache,hash);
                }
                fclose(f);
            }
            atlas_saved=1;
        }
    }
    static int scene_checked;
    if(!scene_checked) {
        scene_checked=1;
        if(getenv("LOA_FONT_SCENE") && !getenv("SR_GESCENE")) ge_scene_set_consumer(font_scene,NULL);
    }
    static char seen[128][25];
    static unsigned count;
    char key[25];
    uint64_t cache=nk_texrepl_cache_key(id->addr,id->format,id->dim,id->clut_hash);
    snprintf(key,sizeof key,"%016" PRIx64 "%08" PRIx32,cache,id->hash);
    int known=0;
    for(unsigned i=0;i<count;i++) if(!strcmp(seen[i],key)) known=1;
    if(!known && count<128) {
        strcpy(seen[count++],key);
        GeState *state=ge_state_ptr();
        int width=state->tex_w, height=state->tex_h, decoded=0;
        if(width>0 && height>0 && width<=512 && height<=512) {
            size_t pixels=(size_t)width*(size_t)height;
            uint32_t *rgba=malloc(pixels*4);
            if(rgba && ge_vram_decode_bound_texture(rgba,pixels)) {
                char name[80]; snprintf(name,sizeof name,"texture-%s.rgba",key);
                FILE *image=fopen(name,"wb");
                if(image) { decoded=fwrite(rgba,4,pixels,image)==pixels; if(fclose(image)!=0) decoded=0; }
            }
            free(rgba);
        }
        FILE *metadata=fopen("texture-probe.jsonl","ab");
        if(metadata) {
            fprintf(metadata,"{\"key\":\"%s\",\"address\":\"%08" PRIx32 "\",\"format\":%u,\"width\":%d,\"height\":%d,\"stride\":%u,\"decoded\":%s}\n",
              key,id->addr,id->format,width,height,state->tex_bufw,decoded?"true":"false");
            fclose(metadata);
        }
    }
    return __real_nk_texrepl_lookup(pack,id,hit);
}
