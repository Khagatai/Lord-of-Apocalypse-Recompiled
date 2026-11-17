/* SPDX-License-Identifier: GPL-3.0-or-later
 * Numeric observation only: never rewrite samples, queues, gains or guest time.
 * A long producer gap is not proof of an underrun: stopped streams are valid.
 */
#ifndef LOA_AUDIO_DIAGNOSTICS_H
#define LOA_AUDIO_DIAGNOSTICS_H
#include <stdint.h>
#include <stddef.h>
typedef struct {
    uint64_t first_ns, last_ns, report_ns, pushes, frames, gap_max_us;
    uint64_t input_rails, scaled_clips;
    uint32_t input_peak;
} LoaAudioProbe;
typedef struct {
    uint64_t frames, clipped_samples;
    uint64_t peak;
} LoaAudioMixProbe;
static inline uint64_t loa_audio_abs64(int64_t v) {
    return v < 0 ? (uint64_t)(-(v + 1)) + 1u : (uint64_t)v;
}
static inline void loa_audio_mix_observe(LoaAudioMixProbe *p, int64_t left, int64_t right) {
    uint64_t l=loa_audio_abs64(left),r=loa_audio_abs64(right);
    p->frames++;
    p->clipped_samples+=(left>32767 || left< -32768)+(right>32767 || right< -32768);
    if(l>p->peak)p->peak=l;
    if(r>p->peak)p->peak=r;
}
static inline void loa_audio_push_observe(LoaAudioProbe *p,uint64_t now_ns,
        const int16_t *lr,uint32_t frames,int32_t gain_l,int32_t gain_r) {
    if(!lr || !frames)return;
    if(!p->first_ns)p->first_ns=now_ns;
    if(!p->report_ns)p->report_ns=now_ns;
    if(p->last_ns && now_ns>=p->last_ns) {
        uint64_t gap=(now_ns-p->last_ns)/1000u;
        if(gap>p->gap_max_us)p->gap_max_us=gap;
    }
    p->last_ns=now_ns;p->pushes++;p->frames+=frames;
    for(uint32_t i=0;i<frames;i++)for(unsigned c=0;c<2;c++) {
        int32_t sample=lr[(size_t)i*2u+c];
        uint32_t peak=(uint32_t)(sample<0?-sample:sample);
        if(peak>p->input_peak)p->input_peak=peak;
        p->input_rails+=(sample==32767 || sample== -32768);
        /* Match the backend's signed Q15 scaling, including negative rounding. */
        int64_t scaled=((int64_t)sample*(c?gain_r:gain_l))>>15;
        p->scaled_clips+=(scaled>32767 || scaled< -32768);
    }
}
static inline int loa_audio_probe_due(const LoaAudioProbe *p,uint64_t now_ns) {
    return p->report_ns && now_ns>=p->report_ns && now_ns-p->report_ns>=1000000000ull;
}
static inline void loa_audio_probe_reset_window(LoaAudioProbe *p,uint64_t now_ns) {
    p->report_ns=now_ns;p->pushes=p->frames=p->gap_max_us=p->input_rails=p->scaled_clips=0;
    p->input_peak=0;
}
#endif
