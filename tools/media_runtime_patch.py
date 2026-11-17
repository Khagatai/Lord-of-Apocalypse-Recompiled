"""Correct the pinned runtime's truncated PSMF header clock in a private copy."""
import hashlib
from pathlib import Path

PINNED_MPEG_SHA256='2a8e29fe71fcbe526f2a11f05a582bd3c463811c1b280020288db01f657c0b83'
PINNED_AUDIO_SHA256='08a7325a1dc380840c462534c3a47c1c65d8afa3d30e71bc54839edde87b7b5d'
BEFORE='''    return ((int64_t)MEM_R8(a) << 32) | ((int64_t)MEM_R8(a+1) << 24) | ((int64_t)MEM_R8(a+2) << 16) |
           ((int64_t)MEM_R8(a+3) << 8) | (int64_t)MEM_R8(a+4);'''
# Matches the pinned PPSSPP Core/HW/MediaEngine.h getMpegTimeStamp and
# the framework's own hle_mpeg.c psmf_be_timestamp. No guessed title offset.
AFTER='''    return ((int64_t)MEM_R8(a) << 36) | ((int64_t)MEM_R8(a+1) << 32) | ((int64_t)MEM_R8(a+2) << 24) |
           ((int64_t)MEM_R8(a+3) << 16) | ((int64_t)MEM_R8(a+4) << 8) | (int64_t)MEM_R8(a+5);'''

def render(source,*,experimental_audio_clock=False):
    if hashlib.sha256(source).hexdigest()!=PINNED_MPEG_SHA256:
        raise ValueError('Pinned MPEG source hash mismatch')
    text=source.decode('utf-8')
    if text.count(BEFORE)!=1:raise ValueError('Missing or ambiguous MPEG timestamp anchor')
    text=text.replace(BEFORE,AFTER)
    anchor='#include "atrac3p_bridge.h"'
    if text.count(anchor)!=1:raise ValueError('Movie caption declaration anchor differs')
    text=text.replace(anchor,anchor+'\nextern void loa_movie_caption_picture(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,unsigned);')
    anchor='        if (gotFrame > 0) { ctx->h264Frames++; ctx->picDelivered++; }'
    if text.count(anchor)!=1:raise ValueError('Decoded picture caption anchor differs')
    text=text.replace(anchor,'''        if (gotFrame > 0) {
            ctx->h264Frames++; ctx->picDelivered++;
            loa_movie_caption_picture(ctx->headerAddr, (uint32_t)ctx->h264Frames,
                buffer, width, (uint32_t)info.width, (uint32_t)info.height, ctx->pixelMode);
        }''')
    anchor='            ctx->audioAusOut++;'
    if text.count(anchor)!=1:raise ValueError('Audio provenance anchor differs')
    text=text.replace(anchor,'''            if(getenv("LOA_MOVIE_TIMING") && !ctx->audioAusOut)
                fprintf(stderr,"LOA_AUDIO_ORIGIN: header=%lld pts=%lld raw_pts=%lld valid=%u\\n",
                    (long long)ctx->firstTimestamp,(long long)au.pts,(long long)au.raw_pts,(unsigned)au.has_pts);
'''+anchor)
    # Rejected for normal builds: the source-clock candidate caused >500 ms
    # native audio starvation despite passing isolated clock tests. Keep the
    # explicit diagnostic reproduction; do not equate that unit pass with a
    # successful game fix (private/audio-source-clock-01).
    if not experimental_audio_clock:return text
    # PPSSPP's MediaEngine::getNextAudioFrame follows the PES audio clock;
    # sceMpegAtracDecode writes that decoded clock back into the caller's AU.
    # Preserve each sparse source timestamp through the FIFO, extrapolating
    # missing timestamps from the preceding decoded block as PPSSPP does.
    changes=[
        ('''uint32_t mpeg_atrac_decode(uint32_t mpegAddr, uint32_t auAddr, uint32_t bufferAddr, uint32_t init) {
    (void)auAddr;''',
         '''uint32_t mpeg_atrac_decode(uint32_t mpegAddr, uint32_t auAddr, uint32_t bufferAddr, uint32_t init) {
    if(!auAddr || (auAddr & 3u) || !sr_guest_span_writable(auAddr,24u))
        return mpeg_contract_error("sceMpegAtracDecode","invalid writable AU pointer",(uint32_t)-1);'''),
        ('struct { uint8_t *data; uint32_t bytes; } audioFifo[MPEG_ATRAC_FIFO_DEPTH];',
         'struct { uint8_t *data; uint32_t bytes; int64_t pts; int has_pts; } audioFifo[MPEG_ATRAC_FIFO_DEPTH];'),
        ('    uint32_t audioHeldBytes;', '    uint32_t audioHeldBytes;\n    int64_t loa_audio_held_pts;\n    int loa_audio_held_has_pts;'),
        ('            ctx->audioFifo[tail].bytes = au.size;',
         '            ctx->audioFifo[tail].bytes = au.size;\n            ctx->audioFifo[tail].pts = au.raw_pts;\n            ctx->audioFifo[tail].has_pts = au.has_pts;'),
        ('            ctx->audioHeldBytes = ctx->audioFifo[ctx->audioFifoHead].bytes;',
         '            ctx->audioHeldBytes = ctx->audioFifo[ctx->audioFifoHead].bytes;\n            ctx->loa_audio_held_pts = ctx->audioFifo[ctx->audioFifoHead].pts;\n            ctx->loa_audio_held_has_pts = ctx->audioFifo[ctx->audioFifoHead].has_pts;'),
        ('''    int64_t pts = ctx->audioPts + ctx->firstTimestamp;
    sr_guest_copy_out(bufferAddr, ctx->audioPcm, MPEG_ATRAC_ES_OUTPUT_SIZE);''',
         '''    int64_t pts = ctx->loa_audio_held_has_pts ? ctx->loa_audio_held_pts : ctx->audioPts + ctx->firstTimestamp;
    au_write_pts(auAddr,0,pts);
    ctx->audioPts = pts - ctx->firstTimestamp;
    sr_guest_copy_out(bufferAddr, ctx->audioPcm, MPEG_ATRAC_ES_OUTPUT_SIZE);'''),
    ]
    for before,after in changes:
        if text.count(before)!=1:raise ValueError('Audio clock anchor differs: '+before[:60])
        text=text.replace(before,after)
    start=text.index("    /* PSP/PPSSPP's libmpeg clock uses")
    end=text.index('#if defined(SR_SDL3VK)',start)
    text=text[:start]+'''    /* The clock starts at the header origin; successful AtracDecode follows
     * source PES timestamps and writes the decoded time back to the caller's AU,
     * as the pinned PPSSPP MediaEngine and sceMpegAtracDecode do. */
'''+text[end:]
    return text

def prepare(framework,output):
    source=Path(framework)/'src/rt/mpeg.c';output=Path(output)
    data=render(source.read_bytes()).encode('utf-8')
    if not output.exists() or output.read_bytes()!=data:output.write_bytes(data)
    return dict(upstream_sha256=PINNED_MPEG_SHA256,generated_sha256=hashlib.sha256(data).hexdigest(),
        adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        correction='six-byte-PSMF-header-timestamps',experimental_audio_clock=False)

def render_audio(source):
    if hashlib.sha256(source).hexdigest()!=PINNED_AUDIO_SHA256:
        raise ValueError('Pinned audio source hash mismatch')
    text=source.decode('utf-8')
    # PSP-HLE-AUDIO-REST-001: return with F or F-64 frames, not 2F.
    # Retain the host's measured pull + one late-wake period as a separate
    # hold; short game buffers still have exactly the same physical headroom.
    before='const uint64_t seen = 2u * (uint64_t)n;'
    if text.count(before)!=1:raise ValueError('Audio hold anchor differs')
    text=text.replace(before,'const uint64_t seen = (uint64_t)n;')
    before='''    while ((q = hle_audio_queued((int)ch)) >= 0 && (uint32_t)q > 2u * n)
        audio_wait(audio_frames_to_us(ch, (uint32_t)q - 2u * n));'''
    if text.count(before)!=1:raise ValueError('Audio release anchor differs')
    text=text.replace(before,'''    /* LOA private correction: one guest period, with the separate host hold
     * above covering measured device pulls and late scheduler wakes. */
    while ((q = hle_audio_queued((int)ch)) >= 0 && (uint32_t)q > n)
        audio_wait(audio_frames_to_us(ch, (uint32_t)q - n));''')
    anchor='#include "sas_resample.h"'
    if text.count(anchor)!=1:raise ValueError('Audio diagnostic include anchor differs')
    # Only observe accepted PCM handoffs and the pre-clamp SAS sum. The gate is
    # explicit and disabled unless requested; no sample or PSP result changes.
    text=text.replace(anchor,'''#include "audio_diagnostics.h"
static LoaAudioProbe loa_audio_probes[9];
static LoaAudioMixProbe loa_audio_mix;
static int loa_audio_probe_enabled(void) {
    static int enabled=-1;
    if(enabled<0) {const char *v=getenv("LOA_AUDIO_DIAGNOSTICS");enabled=v && !strcmp(v,"1");}
    return enabled;
}
static void loa_audio_probe_output(int ch,uint32_t n,const int16_t *lr,int voll,int volr,int queued) {
    if(!loa_audio_probe_enabled() || ch<0 || ch>=9)return;
    uint64_t now=sr_perf_now_ns();
    if(!now)return;
    LoaAudioProbe *p=&loa_audio_probes[ch];
    loa_audio_push_observe(p,now,lr,n,voll,volr);
    if(!loa_audio_probe_due(p,now))return;
    char line[384];
    int count=snprintf(line,sizeof line,"LOA_AUDIO_PUSH: elapsed_ms=%llu vblank=%u ch=%d frames=%llu pushes=%llu "
        "block_frames=%u gap_max_us=%llu input_peak=%u input_rails=%llu scaled_clips=%llu queued=%d\\n",
        (unsigned long long)((now-p->first_ns)/1000000u),(unsigned)sr_audio_vbl(),ch,
        (unsigned long long)p->frames,(unsigned long long)p->pushes,n,
        (unsigned long long)p->gap_max_us,p->input_peak,(unsigned long long)p->input_rails,
        (unsigned long long)p->scaled_clips,queued);
    if(count>0 && (size_t)count<sizeof line)fwrite(line,1,(size_t)count,stderr);
    if(loa_audio_mix.frames) {
        count=snprintf(line,sizeof line,"LOA_AUDIO_MIX: elapsed_ms=%llu vblank=%u frames=%llu clipped_samples=%llu mix_peak=%llu\\n",
            (unsigned long long)((now-p->first_ns)/1000000u),(unsigned)sr_audio_vbl(),
            (unsigned long long)loa_audio_mix.frames,(unsigned long long)loa_audio_mix.clipped_samples,
            (unsigned long long)loa_audio_mix.peak);
        if(count>0 && (size_t)count<sizeof line)fwrite(line,1,(size_t)count,stderr);
        memset(&loa_audio_mix,0,sizeof loa_audio_mix);
    }
    loa_audio_probe_reset_window(p,now);
}
'''+anchor)
    anchor='        if (out_started) sr_perf_audio_output(out_started, n);'
    if text.count(anchor)!=1:raise ValueError('Audio diagnostic output anchor differs')
    text=text.replace(anchor,anchor+'''
        loa_audio_probe_output((int)ch,n,lr,voll,volr,hle_audio_queued((int)ch));''')
    # C evaluates arguments even when the diagnostic function exits early.
    # Gate the extra queue observation as well, leaving disabled calls inert.
    text=text.replace('        loa_audio_probe_output((int)ch,n,lr,voll,volr,hle_audio_queued((int)ch));',
        '        if(loa_audio_probe_enabled())loa_audio_probe_output((int)ch,n,lr,voll,volr,hle_audio_queued((int)ch));')
    anchor='''        int sl = mixsl[i], sr = mixsr[i];'''
    if text.count(anchor)!=1:raise ValueError('Audio diagnostic SAS anchor differs')
    text=text.replace(anchor,anchor+'''
        if(loa_audio_probe_enabled()) {
            int64_t dl=l,dr=r;
            if(add) {
                dl+=((int64_t)sas_output_read(out,(uint32_t)i,0)*in_gain_l)>>12;
                dr+=((int64_t)sas_output_read(out,(uint32_t)i,1)*in_gain_r)>>12;
            }
            loa_audio_mix_observe(&loa_audio_mix,dl,dr);
        }''')
    return text

def prepare_audio(framework,output):
    source=Path(framework)/'src/rt/hle_audio.c';output=Path(output)
    data=render_audio(source.read_bytes()).encode('utf-8')
    if not output.exists() or output.read_bytes()!=data:output.write_bytes(data)
    return dict(upstream_sha256=PINNED_AUDIO_SHA256,generated_sha256=hashlib.sha256(data).hexdigest(),
        adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        correction='one-guest-audio-period-with-host-late-wake-hold')
