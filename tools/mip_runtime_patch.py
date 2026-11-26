"""Prepare an identity-checked, private mip-scaling prototype; never edit upstream."""
import hashlib
from pathlib import Path

PINNED_GE_SHA256='926bec6a0e7b6622ab70d67c7703c1898c62f1a0fb0f296f065cd65843be80ab'


def render(source):
    if hashlib.sha256(source).hexdigest()!=PINNED_GE_SHA256:
        raise ValueError('Pinned Vulkan source hash mismatch; prototype not generated')
    text=source.decode('utf-8')
    def change(before,after):
        nonlocal text
        if text.count(before)!=1:
            raise ValueError('Prototype anchor is missing or ambiguous: '+before[:60])
        text=text.replace(before,after)
    change('#define FB_W 512', '''#include "mip_chain.c"
static int s_loa_mips;
static int s_loa_original_ui;
static uint64_t s_loa_ui_original_binds;
#include "sampler_pack.c"
static uint64_t s_loa_mip_queued, s_loa_mip_uploaded, s_loa_mip_levels_uploaded;
static uint64_t s_loa_mip_bound, s_loa_mip_failed;
static uint64_t s_loa_repl_queued, s_loa_repl_rejected;
#define FB_W 512''')
    change('return (uint64_t)e->w * (uint64_t)e->h * f * f * 4u;', '''LoaMipLayout p;
    if(s_loa_mips && e->mip.max_level && loa_mip_layout(e->w,e->h,(int)e->mip.max_level+1,(int)f,&p)) return p.gpu_bytes;
    return (uint64_t)e->w * (uint64_t)e->h * f * f * 4u;''')
    change('if (!xs_enabled() || s_tex_noscale || levels != 1u) return 0;', '''if (!xs_enabled() || s_tex_noscale) return 0;
    if(levels!=1u) {
        LoaMipLayout p;
        if(!s_loa_mips || !loa_mip_layout(e->w,e->h,(int)levels,tex_xs_factor(e),&p)) return 0;
        for(uint32_t l=0;l<e->mip.max_level;l++)
            if(tex_vram_meets_target(e->mip.addr[l],e->mip_bytes[l])) return 0;
    }''')
    change('static int tex_repl_find(const TexEnt *e, NkTexReplHit *hit, int *factor) {',
           'static int tex_repl_find_id(const TexEnt *e, NkTexReplHit *hit, int *factor, NkTexReplId *identity) {')
    change('const int found = nk_texrepl_lookup(s_repl, &id, hit);',
           'const int found = loa_sampler_lookup(s_repl, &id, hit, s_ge->tex_wrap);\n    if(identity) *identity=id;')
    change('/* Texture replacement (#1880), read once when the renderer starts.', '''static int tex_repl_find(const TexEnt *e, NkTexReplHit *hit, int *factor) {
    return tex_repl_find_id(e,hit,factor,NULL);
}

/* Texture replacement (#1880), read once when the renderer starts.''')
    change('static void tex_xs_offer(TexEnt *e, uint64_t hash, uint32_t levels) {', '''static void loa_mip_offer(TexEnt *,uint64_t,uint32_t);
static void tex_xs_offer(TexEnt *e, uint64_t hash, uint32_t levels) {
    if(s_loa_mips && levels>1u) { loa_mip_offer(e,hash,levels); return; }''')
    change('static int tex_xs_store(TexEnt *e, const NkTexScaleResult *r) {', '''#include "mip_gpu.c"
static int tex_xs_store(TexEnt *e, const NkTexScaleResult *r) {
    if(s_loa_mips && e->mip.max_level) return loa_mip_store(e,r);''')
    change('e && e->w == r.w && e->h == r.h && e->hash == r.hash', 'e && loa_mip_result_matches(e,&r) && e->hash == r.hash')
    change('!nk_tex_scale_can_submit(e->w, e->h, tex_xs_factor(e)))','!loa_mip_can_submit(e))')
    change('s_cnt_xs_bound++;', 's_cnt_xs_bound++;\n    if(s_loa_mips && levels>1u) s_loa_mip_bound++;')
    # Choose per draw: the same cached atlas can serve both UI and a 3D model.
    # Do not purge shared pack entries or alter the translated guest artwork.
    change('    s_tex_cur = e;\n    if (!xs_enabled()', '''    s_tex_cur = e;
    if(s_loa_original_ui && (s_ge->vtype & (1u << 23))) {
        s_loa_ui_original_binds++;
        s_tex_plain_set=VK_NULL_HANDLE;
        return tex_entry_set(e);
    }
    if (!xs_enabled()''')
    change('#include "tex_scale_gpu_selftest.inc"', '''#define gegpu_texscale_selftest loa_upstream_texscale_selftest
#include "tex_scale_gpu_selftest.inc"
#undef gegpu_texscale_selftest
#include "mip_gpu_selftest.c"''')
    change('static VkDescriptorSet tex_get(void) {', '''#include "texture_lookup.h"
static int loa_texture_report_registered,loa_texture_reported;
static void loa_texture_lookup_report(void) {
    if(loa_texture_reported)return;
    loa_texture_reported=1;
    fprintf(stderr,"LOA_TEXTURE_LOOKUP: enabled=%d hits=%llu searches=%llu comparisons=%llu verified=%d\\n",
        loa_texture_lookup_enabled,(unsigned long long)loa_texture_hint_hits,(unsigned long long)loa_texture_searches,
        (unsigned long long)loa_texture_comparisons,loa_texture_lookup_verify);
    if(s_cpu_profile)for(int phase=0;phase<GEGPU_CPU_PHASE_COUNT;phase++)
        fprintf(stderr,"LOA_GE_CPU: phase=%d calls=%llu ns=%llu\\n",phase,
            s_cpu_profile_stats.phase[phase].calls,s_cpu_profile_stats.phase[phase].ns);
}

static VkDescriptorSet tex_get(void) {''')
    change('''    for (int i = 0; i < s_tex_n; i++) {
        TexEnt *e = &s_tex[i];
        if (e->key != key || memcmp(&e->mip, &mip, sizeof(mip)) != 0) continue;''', '''    int loa_texture_index=loa_texture_find(key,&mip);
    if (loa_texture_index>=0) {
        TexEnt *e = &s_tex[loa_texture_index];''')
    change('        s_cpu_profile = cpu_profile && cpu_profile[0] && strcmp(cpu_profile, "0") != 0;',
           '''        s_cpu_profile = cpu_profile && cpu_profile[0] && strcmp(cpu_profile, "0") != 0;
        loa_texture_lookup_reset();loa_texture_reported=0;
        if(!loa_texture_report_registered){loa_texture_report_registered=1;atexit(loa_texture_lookup_report);}''')
    change('s_xs_factor = xs->factor;', '''s_xs_factor = xs->factor;
        const char *original_ui=getenv("LOA_ORIGINAL_UI");
        s_loa_original_ui=original_ui && !strcmp(original_ui,"1");
        fprintf(stderr,"LOA_ORIGINAL_UI: %s (guest artwork on through-mode draws)\\n",s_loa_original_ui?"on":"off");
        const char *loa=getenv("LOA_MIP_TEXTURES");
        const char *sampler=getenv("LOA_SAMPLER_PACK");
        s_loa_sampler_pack=sampler && strcmp(sampler,"1")==0;
        fprintf(stderr,"LOA_SAMPLER_PACK: %s\\n",s_loa_sampler_pack?"on":"off");
        if(loa && strcmp(loa,"0") && strcmp(loa,"1"))
            fprintf(stderr,"LOA_MIPS: refused invalid LOA_MIP_TEXTURES (use 0 or 1)\\n");
        s_loa_mips=g_ace_on && loa && strcmp(loa,"1")==0;
        fprintf(stderr,"LOA_MIPS: %s (experimental authored-level scaling; private renderer copy)\\n",s_loa_mips?"on":"off");''')
    change('tex_repl_shutdown();   /* the exit line,', '''loa_texture_lookup_report();
    fprintf(stderr,"LOA_ORIGINAL_UI: exit (original_binds=%llu)\\n",(unsigned long long)s_loa_ui_original_binds);
    fprintf(stderr,"LOA_MIPS: exit (queued=%llu, uploaded=%llu, levels=%llu, bound=%llu, failed=%llu, replacement_queued=%llu, replacement_rejected=%llu)\\n",
            (unsigned long long)s_loa_mip_queued,(unsigned long long)s_loa_mip_uploaded,
            (unsigned long long)s_loa_mip_levels_uploaded,(unsigned long long)s_loa_mip_bound,
            (unsigned long long)s_loa_mip_failed,(unsigned long long)s_loa_repl_queued,(unsigned long long)s_loa_repl_rejected);
    tex_repl_shutdown();   /* the exit line,''')
    return text


def prepare(framework,output):
    source=Path(framework)/'src/rt/gpu_sdl3vk/ge_gpu.c'
    data=render(source.read_bytes())
    output=Path(output)
    helpers=Path(__file__).resolve().parent
    fingerprints={}
    for name in ('mip_chain.c','mip_gpu.c','mip_gpu_selftest.c','mip_runtime_patch.py','sampler_pack.c','texture_lookup.h'):
        content=(helpers/name).read_bytes()
        fingerprints[name]=hashlib.sha256(content).hexdigest()
        target=output.parent/name
        if not target.exists() or target.read_bytes()!=content:target.write_bytes(content)
    encoded=data.encode('utf-8')
    if not output.exists() or output.read_bytes()!=encoded:output.write_bytes(encoded)
    return {'upstream_sha256':PINNED_GE_SHA256,'generated_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'sampler_namespace_version':1,
            'extension_sha256':fingerprints}
