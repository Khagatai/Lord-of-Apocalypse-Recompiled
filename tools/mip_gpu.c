/* SPDX-License-Identifier: GPL-3.0-or-later
 * Diagnostic extension included in a verified PRIVATE copy of pinned ge_gpu.c.
 * Original mip images remain intact. Existing worker generations, whole-chain
 * hashes, cache invalidation and fallback sets still decide whether to bind. */
static int loa_mip_submit(TexEnt *e,uint64_t hash,uint32_t levels,int factor) {
    LoaMipLayout p;
    if(!loa_mip_layout(e->w,e->h,(int)levels,factor,&p)) return 0;
    uint32_t *atlas=malloc((size_t)p.width*p.height*4u);
    if(!atlas) return 0;
    for(uint32_t l=0;l<levels;l++) {
        ge_decode_tex_level_rgba(l,s_texscratch);
        loa_mip_pack(&p,(int)l,s_texscratch,e->xs.clamp_u,e->xs.clamp_v,atlas);
    }
    int queued=nk_tex_scale_submit(e->xs.serial,hash,atlas,p.width,p.height,factor,1,1);
    free(atlas);
    if(queued) s_loa_mip_queued++;
    return queued;
}

static int loa_mip_result_matches(const TexEnt *e,const NkTexScaleResult *r) {
    if(!s_loa_mips || !e->mip.max_level) return e->w==r->w && e->h==r->h;
    LoaMipLayout p;
    return loa_mip_layout(e->w,e->h,(int)e->mip.max_level+1,r->factor,&p) &&
           r->w==p.width && r->h==p.height;
}

static int loa_mip_can_submit(const TexEnt *e) {
    int factor=tex_xs_factor(e);
    LoaMipLayout p;
    if(s_loa_mips && e->mip.max_level) {
        return loa_mip_layout(e->w,e->h,(int)e->mip.max_level+1,factor,&p) &&
               nk_tex_scale_can_submit(p.width,p.height,factor);
    }
    return nk_tex_scale_can_submit(e->w,e->h,factor);
}

static int loa_mip_upload(VkImage image,const LoaMipLayout *p,const uint32_t *pixels,int w,int h) {
    VkImageLayout layout=VK_IMAGE_LAYOUT_UNDEFINED;
    for(int l=0;l<p->levels;l++) {
        uint32_t sw=(uint32_t)(w*p->factor)>>l,sh=(uint32_t)(h*p->factor)>>l;
        if(!sw) sw=1;
        if(!sh) sh=1;
        uint32_t rows=TEX_XS_BAND_BYTES/(sw*4u);
        if(!rows) rows=1;
        for(uint32_t y=0;y<sh;y+=rows) {
            uint32_t n=sh-y<rows?sh-y:rows;
            UploadReservation upload;
            if(!upload_reserve((VkDeviceSize)sw*n*4u,&upload)) return 0;
            to_layout(s_cmd,image,VK_IMAGE_ASPECT_COLOR_BIT,&layout,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
            /* Reservation can submit/reopen the command buffer. Its predecessor's
             * barrier and copies remain ordered on the same GE queue. */
            for(uint32_t row=0;row<n;row++)
                loa_mip_row(p,l,pixels,(int)sw,(int)sh,(int)(y+row),(uint32_t *)upload.map+(size_t)row*sw);
            VkBufferImageCopy bic={0};
            bic.imageSubresource.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
            bic.imageSubresource.mipLevel=(uint32_t)l;
            bic.imageSubresource.layerCount=1;
            bic.imageOffset.y=(int32_t)y;
            bic.imageExtent.width=sw; bic.imageExtent.height=n; bic.imageExtent.depth=1;
            bic.bufferOffset=upload.offset;
            vkCmdCopyBufferToImage(s_cmd,upload.buffer,image,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&bic);
            if(l==p->levels-1 && y+n==sh)
                to_layout(s_cmd,image,VK_IMAGE_ASPECT_COLOR_BIT,&layout,VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
            if(!upload_finish(&upload,SR_PERF_GE_TEXTURE_UPLOAD)) return 0;
        }
    }
    return 1;
}

static int loa_mip_store(TexEnt *e,const NkTexScaleResult *r) {
    LoaMipLayout p;
    if(!loa_mip_layout(e->w,e->h,(int)e->mip.max_level+1,r->factor,&p)) return 0;
    if(e->xs.factor && e->xs.factor!=r->factor) return 0;
    if(!e->xs.factor) {
        if(!tex_xs_reclaim(e,p.gpu_bytes) || !nk_tex_scale_budget_take(p.gpu_bytes)) {
            tex_xs_budget_wait(e); return 0;
        }
        e->xs.bytes=p.gpu_bytes;
        VkSamplerCreateInfo sampler;
        tex_sampler_info(e->xs.min_linear,e->xs.mag_linear,e->xs.clamp_u,e->xs.clamp_v,&e->mip,&sampler);
#if defined(SR_GPU_COHERENCE_SELFTEST) && defined(LOA_MIP_MUTANT_BASE_ONLY)
        sampler.minLod=0.0f; sampler.maxLod=0.0f;
#endif
        if(!make_image_levels((uint32_t)e->w*r->factor,(uint32_t)e->h*r->factor,(uint32_t)p.levels,
                             VK_FORMAT_R8G8B8A8_UNORM,VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_SAMPLED_BIT,
                             &e->xs.img,&e->xs.mem) ||
           !make_view_levels(e->xs.img,VK_FORMAT_R8G8B8A8_UNORM,VK_IMAGE_ASPECT_COLOR_BIT,(uint32_t)p.levels,&e->xs.view) ||
           vkCreateSampler(s_dev,&sampler,NULL,&e->xs.smp)!=VK_SUCCESS ||
           !(e->xs.set=make_descriptor(e->xs.view,e->xs.smp,s_dpool_tex))) {
            tex_xs_free(e); return 0;
        }
        e->xs.factor=r->factor;
    }
    if(e->pending && !submit_pending()) return 0;
    if(!loa_mip_upload(e->xs.img,&p,r->rgba,e->w,e->h)) {
        e->xs.state=XS_NONE; s_loa_mip_failed++; return 0;
    }
    e->xs.made_serial=r->serial; e->xs.made_hash=r->hash;
    e->xs.state=XS_READY; e->xs.last_bound=xs_now();
    s_cnt_xs_uploads++; s_loa_mip_uploaded++; s_loa_mip_levels_uploaded+=(uint64_t)p.levels;
    return 1;
}

static void loa_mip_capture(const TexEnt *e,const NkTexReplId *id,uint32_t levels) {
    static int enabled=-1;
    static char seen[96][64]; static unsigned count;
    if(enabled<0) enabled=getenv("LOA_MIP_CAPTURE") && strcmp(getenv("LOA_MIP_CAPTURE"),"1")==0;
    if(!enabled || !id->addr || count>=96) return;
    /* Captures record the real PSP identity, independently of host namespaces. */
    NkTexReplId measured=*id;measured.clut_hash=0;
    uint32_t source_bytes=tex_source_size();const uint8_t *source=tex_source_ptr(e->addr,source_bytes);
    if(!source)return;
    measured.hash=nk_texrepl_hash_texture(s_repl,source,source_bytes,e->addr,(int)s_ge->tex_bufw,e->w,e->h,s_ge->tex_fmt,0);
    if(measured.format&4u) {
        uint32_t last=0,max=0;ge_clut_load_extent(&last,&max);
        measured.clut_hash=nk_texrepl_clut_identity(s_ge->clutram,(uint32_t)sizeof(s_ge->clutram),s_ge->clut_fmt,measured.format,last,max);
    }
    id=&measured;
    char key[25],identity[64];
    uint64_t cache=nk_texrepl_cache_key(id->addr,id->format,id->dim,id->clut_hash);
    snprintf(key,sizeof key,"%016llx%08x",(unsigned long long)cache,id->hash);
    snprintf(identity,sizeof identity,"%s-%016llx-%03x",key,(unsigned long long)e->hash,s_ge->tex_wrap&0x101u);
    for(unsigned i=0;i<count;i++) if(strcmp(seen[i],identity)==0) return;
    strcpy(seen[count++],identity);
    FILE *metadata=fopen("mip-capture.jsonl","ab");
    if(!metadata) return;
    for(uint32_t l=0;l<levels;l++) {
        int w=e->w>>(int)l,h=e->h>>(int)l;
        if(w<1) w=1;
        if(h<1) h=1;
        ge_decode_tex_level_rgba(l,s_texscratch);
        char file[96]; snprintf(file,sizeof file,"mip-%s-%u.rgba",identity,l);
        FILE *out=fopen(file,"wb"); int ok=0;
        if(out) { ok=fwrite(s_texscratch,4,(size_t)w*h,out)==(size_t)w*h; if(fclose(out)!=0) ok=0; }
        fprintf(metadata,"{\"key\":\"%s\",\"content\":\"%016llx\",\"wrap\":%u,\"level\":%u,\"levels\":%u,\"width\":%d,\"height\":%d,\"file\":\"%s\",\"written\":%s}\n",
                key,(unsigned long long)e->hash,s_ge->tex_wrap&0x101u,l,levels,w,h,file,ok?"true":"false");
    }
    fclose(metadata);
}

/* 1 complete chain, 0 unmatched/invalid (use authored art), -1 temporarily
 * unavailable. Never combine replacement level 0 with original lower levels. */
static int loa_mip_replacement(const TexEnt *e,uint32_t levels,uint32_t **rgba,int *factor,LoaMipLayout *layout) {
    NkTexReplHit hits[8]={{0}}; NkTexReplId id={0};
    int found=tex_repl_find_id(e,&hits[0],factor,&id);
    loa_mip_capture(e,&id,levels);
    if(!found) return 0;
    int held=1,result=0;
    if(!loa_mip_layout(e->w,e->h,(int)levels,*factor,layout) || nk_texrepl_level_count(s_repl,&id)<(int)levels) goto reject;
    for(uint32_t l=1;l<levels;l++) {
        if(!nk_texrepl_lookup_level(s_repl,&id,(int)l,&hits[l])) goto reject;
        held++;
        int w=hits[0].w>>(int)l,h=hits[0].h>>(int)l;
        if(w<1) w=1;
        if(h<1) h=1;
        if(hits[l].w!=w || hits[l].h!=h) goto reject;
    }
    if(!nk_tex_scale_can_submit(layout->width,layout->height,*factor)) { result=-1; goto done; }
    *rgba=calloc((size_t)layout->width*layout->height*(*factor)*(*factor),4);
    if(!*rgba) { result=-1; goto done; }
    for(uint32_t l=0;l<levels;l++)
        loa_mip_pack_ready(layout,(int)l,hits[l].rgba,hits[l].w,hits[l].h,*rgba);
    result=1; goto done;
reject:
    s_loa_repl_rejected++;
    if(s_loa_repl_rejected<=16)
        fprintf(stderr,"LOA_MIPS: replacement chain rejected (address=%08x, required_levels=%u); authored art retained\n",e->addr,levels);
done:
    for(int l=0;l<held;l++) nk_texrepl_unpin(s_repl,&hits[l]);
    tex_repl_flush_notes();
    return result;
}

static void loa_mip_offer(TexEnt *e,uint64_t hash,uint32_t levels) {
    e->xs.retry=XS_RETRY_NONE;
    if(s_tex_noscale || tex_vram_meets_target(e->addr,e->bytes)) return;
    for(uint32_t l=0;l<e->mip.max_level;l++)
        if(tex_vram_meets_target(e->mip.addr[l],e->mip_bytes[l])) return;
    uint32_t *ready=NULL; int replacement_factor=0,result=0;
    LoaMipLayout layout;
    if(s_repl) result=loa_mip_replacement(e,levels,&ready,&replacement_factor,&layout);
    if(result==0) replacement_factor=0;
    if(e->xs.repl_factor!=replacement_factor && e->xs.factor) {
        if(!submit_pending() || !cmd_drain(GEGPU_BOUNDARY_LIFETIME)) {
            free(ready);e->xs.retry=XS_RETRY_BUDGET; e->xs.retry_present=xs_now();return;
        }
        uint64_t serial=e->xs.serial;
        tex_xs_free(e); e->xs.serial=serial;
    }
    e->xs.repl_factor=replacement_factor;
    if(result<0) { e->xs.retry=XS_RETRY_QUEUE;return; }
    if(!tex_xs_eligible(e,levels)) { free(ready);return; }
    int f=tex_xs_factor(e);
    if(!e->xs.factor && !tex_xs_reclaim(e,tex_xs_need(e))) {
        free(ready);tex_xs_budget_wait(e);return;
    }
    unsigned filter=tex_filter_variant(s_ge->tex_filter);
    e->xs.min_linear=(filter&2u)!=0; e->xs.mag_linear=(filter&1u)!=0;
    e->xs.clamp_u=s_ge->tex_wrap&1; e->xs.clamp_v=(s_ge->tex_wrap>>8)&1;
    int queued;
    if(ready) {
        queued=nk_tex_scale_submit_ready(e->xs.serial,hash,ready,layout.width,layout.height,f);
        free(ready);
        if(queued) { s_loa_repl_queued++;s_cnt_repl_queued++;s_loa_mip_queued++; }
    } else queued=loa_mip_submit(e,hash,levels,f);
    if(!queued) { e->xs.retry=XS_RETRY_QUEUE;return; }
    e->xs.state=XS_QUEUED;
    if(result==1) tex_xs_collect();
}
