#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "audio_diagnostics.h"
int main(void) {
    LoaAudioProbe p={0};
    int16_t samples[]={32767,-32768,16000,-16000,0,0};
    int16_t original[6];memcpy(original,samples,sizeof samples);
    loa_audio_push_observe(&p,1000000000ull,samples,3,32768,32768);
    assert(p.pushes==1 && p.frames==3 && p.input_peak==32768 && p.input_rails==2 && !p.scaled_clips);
    assert(!memcmp(original,samples,sizeof samples));
    loa_audio_push_observe(&p,1250000000ull,samples,3,65536,65536);
    assert(p.gap_max_us==250000 && p.scaled_clips==2);
    assert(!loa_audio_probe_due(&p,1999999999ull) && loa_audio_probe_due(&p,2000000000ull));
    loa_audio_probe_reset_window(&p,2000000000ull);
    assert(!p.frames && !p.input_rails && !p.scaled_clips && p.first_ns==1000000000ull);
    loa_audio_push_observe(&p,2001000000ull,samples,3,0,0);
    assert(p.gap_max_us==751000 && !p.scaled_clips); /* keep the cross-window gap */
    loa_audio_push_observe(&p,1900000000ull,NULL,3,0,0);assert(p.pushes==1);
    LoaAudioProbe negative={0};int16_t edge[]={0,-32767};
    loa_audio_push_observe(&negative,1,edge,1,0,32770);
    assert(negative.scaled_clips==1); /* arithmetic shift clips; truncation misses it */
    LoaAudioMixProbe mix={0};
    loa_audio_mix_observe(&mix,32767,-32768);assert(!mix.clipped_samples);
    loa_audio_mix_observe(&mix,40000,-40000);assert(mix.clipped_samples==2 && mix.peak==40000);
    assert(loa_audio_abs64(INT64_MIN)==(UINT64_C(1)<<63));
    puts("PASS: input rails, gain clipping, mix saturation and producer gaps measured without changing PCM");
}
