/* SPDX-License-Identifier: GPL-3.0-or-later
 * Synthetic Vulkan cells using the pinned renderer's real sampler, uploads,
 * draws and invalidation. Included only in the private selftest build. */
static int loa_test_draw_size(uint32_t expected,const char *cell,int size) {
    GeVtx a,b;
    wrap_vtx(&a,8,8,0xFFFFFFFFu); a.u=0; a.v=0;
    wrap_vtx(&b,(float)(8+size),(float)(8+size),0xFFFFFFFFu); b.u=16; b.v=16;
    s_tmpl_ok=0;
    if(!hook_sprite(&a,&b,0) || !s_cur || !target_readback(s_cur)) return 0;
    const uint32_t *fb=(const uint32_t *)SR_HOST(XST_BASE);
    for(int y=9;y<7+size;y++) for(int x=9;x<7+size;x++)
        if((fb[y*XST_STRIDE+x]&0xFFFFFFu)!=(expected&0xFFFFFFu)) {
            fprintf(stderr,"LOA mip GPU: FAIL %s at %d,%d got=%06x expected=%06x\n",cell,x,y,
                    fb[y*XST_STRIDE+x]&0xFFFFFFu,expected&0xFFFFFFu);return 0;
        }
    return 1;
}

static int loa_test_draw(uint32_t expected,const char *cell) {
    return loa_test_draw_size(expected,cell,32);
}

static void loa_test_ready(void) {
    nk_tex_scale_wait_idle();
    /* As in the pinned upload-cap selftest, begin a new synthetic present.
     * Large chains legitimately wait behind the per-present upload budget. */
    s_cnt_present_cpu++;
    tex_xs_collect();
}

static void loa_test_fill(uint32_t address,int count,uint32_t value,int indexed) {
    if(indexed) memset(SR_HOST(address),(int)value,(size_t)count);
    else for(int i=0;i<count;i++) memcpy((uint8_t *)SR_HOST(address)+(size_t)i*4,&value,4);
    sr_gpu_vram_dirty(address,(uint32_t)count*(indexed?1u:4u));
}

static int loa_test_chain(int indexed,int root) {
    const uint32_t addresses[3]={XST_TEX,0x04090000u,0x040B0000u};
    uint32_t colors[4]={0,0xFF0000FFu,0xFF00FF00u,0xFFFF0000u};
    xst_reset();
    for(int l=0;l<3;l++) {
        int side=root>>l,stride=indexed?root:side;
        loa_test_fill(addresses[l],stride*side,indexed?(uint32_t)l+1u:colors[l+1],indexed);
    }
    xst_state(XST_BASE,XST_TEX,indexed?5u:3u,0,1);
    s_ge->tex_w=root; s_ge->tex_h=root; s_ge->tex_bufw=(uint32_t)root;
    s_ge->tex_filter=4u; s_ge->tex_max_level=2u;
    s_ge->tex_level_mode=1u;
    for(int l=0;l<2;l++) {
        s_ge->tex_mip_addr[l]=addresses[l+1];
        s_ge->tex_mip_bufw[l]=indexed?(uint32_t)root:(uint32_t)root>>(uint32_t)(l+1);
        s_ge->tex_mip_wlog2[l]=(uint8_t)(log2_exact(root)-l-1);
        s_ge->tex_mip_hlog2[l]=(uint8_t)(log2_exact(root)-l-1);
    }
    if(indexed) {
        memset(s_ge->clutram,0,sizeof(s_ge->clutram));
        memcpy(s_ge->clutram,colors,sizeof(colors));
        s_ge->clut_fmt=3u|(0xFFu<<8); ge_clut_note_load(1024u);
    }
    for(int l=0;l<3;l++) {
        s_ge->tex_lod_bias=(float)l; ge_state_note_external_write();
        if(!loa_test_draw(colors[l+1],"before worker")) return 0;
        loa_test_ready();
        uint64_t before=s_loa_mip_bound;
        if(!loa_test_draw(colors[l+1],"authored level selection") || s_loa_mip_bound==before) {
            fprintf(stderr,"LOA mip GPU: FAIL level %d never bound its scaled chain\n",l);return 0;
        }
    }
    s_ge->tex_lod_bias=1.0f; ge_state_note_external_write();
    nk_tex_scale_set_hold(1);
    uint32_t updated=0xFFFFFF00u;
    if(indexed) { memcpy(s_ge->clutram+8,&updated,4); ge_state_note_external_write(); }
    else loa_test_fill(addresses[1],(root/2)*(root/2),updated,0);
    uint64_t before=s_loa_mip_bound;
    int ok=loa_test_draw(updated,indexed?"palette changed, worker held":"higher mip changed, worker held");
    if(s_loa_mip_bound!=before) ok=0;
    nk_tex_scale_set_hold(0); loa_test_ready();
    if(!ok || !loa_test_draw(updated,"updated chain ready") || s_loa_mip_bound==before) {
        fprintf(stderr,"LOA mip GPU: FAIL stale copy or missing updated chain\n");return 0;
    }
    /* Automatic LOD from a 16-texel span minified into eight guest pixels. */
    s_ge->tex_level_mode=0u; s_ge->tex_lod_bias=0.0f; ge_state_note_external_write();
    if(!loa_test_draw_size(updated,"automatic LOD before worker",8)) return 0;
    loa_test_ready();
    if(!loa_test_draw_size(updated,"automatic LOD scaled chain",8)) return 0;
    s_ge->tex_level_mode=2u; s_ge->tex_lod_slope=1.0f; ge_state_note_external_write();
    if(!loa_test_draw(updated,"slope LOD before worker")) return 0;
    loa_test_ready();
    if(!loa_test_draw(updated,"slope LOD scaled chain")) return 0;
    printf("LOA mip GPU: PASS %s %dx%d: constant/auto/slope LOD, rewrite/palette, fallback and ready copy\n",indexed?"CLUT8":"RGBA8888",root,root);
    return 1;
}

static int loa_test_replacement(int mode) {
    const uint32_t addresses[3]={XST_TEX,0x04090000u,0x040B0000u};
    const uint32_t original[3]={0xFF0000FFu,0xFF00FF00u,0xFFFF0000u};
    const uint32_t replacement[3]={0xFF10B0F0u,0xFF50C010u,0xFFDD0088u};
    const int factor=3;
    xst_reset();
    for(int l=0;l<3;l++) loa_test_fill(addresses[l],(16>>l)*(16>>l),original[l],0);
    xst_state(XST_BASE,XST_TEX,3u,0,1);
    s_ge->tex_filter=4u;s_ge->tex_max_level=2u;s_ge->tex_level_mode=1u;
    for(int l=0;l<2;l++) {
        s_ge->tex_mip_addr[l]=addresses[l+1];s_ge->tex_mip_bufw[l]=8u>>(uint32_t)l;
        s_ge->tex_mip_wlog2[l]=(uint8_t)(3-l);s_ge->tex_mip_hlog2[l]=(uint8_t)(3-l);
    }
    ge_state_note_external_write();
    uint32_t hash=nk_texrepl_quick_hash(SR_HOST(XST_TEX),16u*16u*4u,XST_TEX);
    uint64_t key=nk_texrepl_cache_key(XST_TEX,3u,0x0404u,0u);
    char folder[512],path[600],err[160];
    snprintf(folder,sizeof folder,"%s/loa_mip_pack_%d_scale_%d",SR_SELFTEST_BUILD_ROOT,mode,s_scale);
    if(!nk_platform_mkdir_p(folder)) return 0;
    snprintf(path,sizeof path,"%s/textures.ini",folder);
    FILE *ini=fopen(path,"wb");if(!ini) return 0;
    fprintf(ini,"[options]\nhash = quick\n[hashes]\n");
    for(int l=0;l<3;l++) {
        if(mode==1 && l==2) continue;
        fprintf(ini,"%016llx%08x_%d = %s%d.png\n",(unsigned long long)key,hash,l,mode==2 && l==2?"absent-":"level-",l);
    }
    fclose(ini);
    for(int l=0;l<3;l++) {
        if(mode==2 && l==2) continue;
        int side=(16*factor)>>l,w=side+(mode==3 && l==1?1:0);
        uint32_t *pixels=malloc((size_t)w*side*4);if(!pixels) return 0;
        for(int i=0;i<w*side;i++) pixels[i]=replacement[l];
        snprintf(path,sizeof path,"%s/level-%d.png",folder,l);
        int ok=synpng_write(path,w,side,pixels);free(pixels);if(!ok) return 0;
        if(mode==4 && l==2) { FILE *bad=fopen(path,"wb");if(!bad)return 0;fputs("corrupt PNG test",bad);fclose(bad); }
    }
    NkTexRepl *saved=s_repl;
    s_repl=nk_texrepl_open(folder,0,err,sizeof err);
    if(!s_repl) { s_repl=saved;fprintf(stderr,"LOA mip GPU: FAIL cannot open synthetic pack: %s\n",err);return 0; }
    int old_factor=s_xs_factor;if(mode==5)s_xs_factor=0;
    uint64_t rejected=s_loa_repl_rejected,bound=s_cnt_repl_bound;
    const int complete=mode==0 || mode==5;
    int ok=1;
    for(int l=0;l<3 && ok;l++) {
        s_ge->tex_lod_bias=(float)l;ge_state_note_external_write();
        uint32_t expected=complete?replacement[l]:original[l];
        ok=loa_test_draw(expected,complete?"replacement mip selection":"incomplete chain fallback");
        loa_test_ready();
        ok=ok && loa_test_draw(expected,"replacement/fallback after ready");
        if(complete && s_tex_bound_scale!=factor) ok=0;
    }
    if(complete) ok=ok && s_cnt_repl_bound>bound && s_loa_repl_rejected==rejected;
    else ok=ok && s_cnt_repl_bound==bound && s_loa_repl_rejected>rejected;
    xst_reset();nk_texrepl_close(s_repl);s_repl=saved;s_xs_factor=old_factor;
    if(!ok) { fprintf(stderr,"LOA mip GPU: FAIL replacement case %d\n",mode);return 0; }
    printf("LOA mip GPU: PASS replacement-%d: %s\n",mode,complete?"complete authored PNG chain at factor 3":"whole-chain rejection keeps authored art at all LODs");
    return 1;
}

static int loa_test_sampler_namespace(int indexed) {
    const uint32_t wraps[4]={0,1,256,257},order[7]={0,1,2,3,0,3,1};
    const uint32_t addresses[3]={XST_TEX,0x04090000u,0x040B0000u};
    const uint32_t colours[4]={0xFF0000FFu,0xFF00FF00u,0xFFFF0000u,0xFF00FFFFu};
    xst_reset();
    for(int l=0;l<3;l++) loa_test_fill(addresses[l],(indexed?16:(16>>l))*(16>>l),indexed?1u:0xFFFFFFFFu,indexed);
    uint32_t legacy_hash=nk_texrepl_quick_hash(SR_HOST(XST_TEX),indexed?256u:1024u,XST_TEX);
    for(int l=0;l<3;l++) loa_test_fill(addresses[l],(indexed?16:(16>>l))*(16>>l),indexed?2u:0xFF111111u,indexed);
    uint32_t hash=nk_texrepl_quick_hash(SR_HOST(XST_TEX),indexed?256u:1024u,XST_TEX);
    xst_state(XST_BASE,XST_TEX,indexed?5u:3u,0,1);
    uint32_t clut_hash=0;
    if(indexed) {
        uint32_t palette[3]={0,0xFFFFFFFFu,0xFF111111u};
        memset(s_ge->clutram,0,sizeof(s_ge->clutram));memcpy(s_ge->clutram,palette,sizeof(palette));
        s_ge->clut_fmt=3u|(0xFFu<<8);ge_clut_note_load(1024u);
        clut_hash=nk_texrepl_clut_identity(s_ge->clutram,(uint32_t)sizeof(s_ge->clutram),s_ge->clut_fmt,5u,1024u,1024u);
    }
    for(int l=0;l<2;l++) {
        s_ge->tex_mip_addr[l]=addresses[l+1];s_ge->tex_mip_bufw[l]=indexed?16u:(8u>>(uint32_t)l);
        s_ge->tex_mip_wlog2[l]=(uint8_t)(3-l);s_ge->tex_mip_hlog2[l]=(uint8_t)(3-l);
    }
    char folder[512],path[600],err[160];
    snprintf(folder,sizeof folder,"%s/loa_sampler_pack_%d_scale_%d",SR_SELFTEST_BUILD_ROOT,indexed,s_scale);
    if(!nk_platform_mkdir_p(folder))return 0;
    snprintf(path,sizeof path,"%s/textures.ini",folder);FILE *ini=fopen(path,"wb");if(!ini)return 0;
    fputs("[options]\nhash = quick\n[hashes]\n",ini);
    for(int mode=0;mode<5;mode++)for(int l=0;l<3;l++) {
        uint64_t key=nk_texrepl_cache_key(XST_TEX,indexed?5u:3u,0x0404u,clut_hash);
        uint32_t data_hash=mode==4?legacy_hash:hash^loa_sampler_tag(wraps[mode]);
        fprintf(ini,"%016llx%08x_%d = variant-%d-%d.png\n",(unsigned long long)key,data_hash,l,mode,l);
    }
    fclose(ini);
    for(int mode=0;mode<5;mode++)for(int l=0;l<3;l++) {
        int side=48>>l;uint32_t *pixels=malloc((size_t)side*side*4);if(!pixels)return 0;
        for(int i=0;i<side*side;i++)pixels[i]=mode==4?0xFFFF00FFu:colours[mode];
        snprintf(path,sizeof path,"%s/variant-%d-%d.png",folder,mode,l);
        int ok=synpng_write(path,side,side,pixels);free(pixels);if(!ok)return 0;
    }
    NkTexRepl *saved=s_repl;int sampler=s_loa_sampler_pack;
    s_repl=nk_texrepl_open(folder,0,err,sizeof err);
    if(!s_repl){s_repl=saved;return 0;}
    s_loa_sampler_pack=1;int ok=1;
    for(int mips=0;mips<2 && ok;mips++) {
        s_ge->tex_max_level=mips?2u:0u;s_ge->tex_filter=mips?4u:0u;s_ge->tex_level_mode=1u;
        for(int n=0;n<7 && ok;n++) {
            unsigned variant=order[n];s_ge->tex_wrap=wraps[variant];
            for(int l=0;l<(mips?3:1) && ok;l++) {
                s_ge->tex_lod_bias=(float)l;ge_state_note_external_write();
                ok=loa_test_draw(colours[variant],"sampler namespace selection");loa_test_ready();
                ok=ok && loa_test_draw(colours[variant],"sampler namespace resident cache") && s_tex_bound_scale==3;
            }
        }
    }
    /* A changed source with no tagged entry must retain legacy pack support. */
    for(int l=0;l<3;l++)loa_test_fill(addresses[l],(indexed?16:(16>>l))*(16>>l),indexed?1u:0xFFFFFFFFu,indexed);
    s_ge->tex_wrap=257u;
    for(int l=0;l<3 && ok;l++) {
        s_ge->tex_lod_bias=(float)l;ge_state_note_external_write();
        ok=loa_test_draw(0xFFFF00FFu,"sampler namespace legacy fallback");loa_test_ready();
        ok=ok && loa_test_draw(0xFFFF00FFu,"sampler namespace legacy ready");
    }
    xst_reset();nk_texrepl_close(s_repl);s_repl=saved;s_loa_sampler_pack=sampler;
    if(!ok){fprintf(stderr,"LOA mip GPU: FAIL sampler namespace\n");return 0;}
    printf("LOA mip GPU: PASS sampler namespace %s: four wraps, single/multiple levels, cache switches and legacy fallback\n",indexed?"CLUT8":"RGBA8888");
    return 1;
}

int gegpu_texscale_selftest(void) {
    if(!s_loa_mips) return loa_upstream_texscale_selftest();
    if(!loa_test_chain(0,16) || !loa_test_chain(1,16) || !loa_test_chain(0,256)) return 0;
    for(int mode=0;mode<6;mode++) if(!loa_test_replacement(mode)) return 0;
    if(!loa_test_sampler_namespace(0) || !loa_test_sampler_namespace(1))return 0;
    return 1;
}
