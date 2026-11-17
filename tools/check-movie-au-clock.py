"""Compile the real MPEG ATRAC handler in a synthetic clock/writeback harness."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import media_runtime_patch,title
def main():
    title.verify_inputs();folder=ROOT/'private/movie-au-clock';folder.mkdir(exist_ok=True)
    upstream=(title.FRAMEWORK/'src/rt/mpeg.c').read_bytes()
    header='''#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
typedef struct {uint8_t *audioHeld; uint32_t audioHeldBytes; int64_t firstTimestamp,audioPts,loa_audio_held_pts; int loa_audio_held_has_pts; uint8_t audioPcm[8192]; uint64_t audioDecoded;} Mpeg;
static Mpeg context; static int64_t written_pts,delivered_pts;static int writable=1,copied;
#define MPEG_ATRAC_ES_OUTPUT_SIZE 8192
#define SCE_MPEG_ERROR_NO_DATA 0x80618001u
static const int audioTimestampStep=4180;
static Mpeg *mpeg_find(uint32_t a){return a?&context:NULL;}
static int sr_guest_span_writable(uint32_t a,uint32_t n){return a && n && writable;}
static int sr_guest_span_writable_any_view(uint32_t a,uint32_t n){return a && n;}
static uint32_t mpeg_contract_error(const char *a,const char *b,uint32_t c){(void)a;(void)b;return c;}
static uint32_t mpeg_audio_decode_frame(Mpeg *c,const uint8_t *f,uint32_t b,uint32_t i){(void)c;(void)f;(void)b;(void)i;return 0;}
static void au_write_pts(uint32_t a,int o,int64_t p){(void)a;(void)o;written_pts=p;}
static void sr_guest_copy_out(uint32_t a,const void *b,uint32_t n){(void)a;(void)b;(void)n;copied++;}
static void sr_psmf_av_note_audio_delivery(uint32_t a,uint32_t b,int64_t p,int valid){(void)a;(void)b;(void)valid;delivered_pts=p;}
'''
    tail='''
static void held(int valid,int64_t pts){context.audioHeld=malloc(16);context.audioHeldBytes=16;context.loa_audio_held_has_pts=valid;context.loa_audio_held_pts=pts;}
int main(void){
    context.firstTimestamp=90000;held(1,85069);
    if(mpeg_atrac_decode(1,4,8,1) || written_pts!=85069 || delivered_pts!=85069 || context.audioPts!=-751 || copied!=1)return 10;
    held(0,0);
    if(mpeg_atrac_decode(1,4,8,0) || written_pts!=89249 || delivered_pts!=89249)return 11;
    held(1,93430);
    if(mpeg_atrac_decode(1,4,8,0) || written_pts!=93430)return 12;
    writable=0;held(0,0);
    if(mpeg_atrac_decode(1,4,8,0)!=0xffffffffu || copied!=3)return 13;
    free(context.audioHeld);puts("PASS: source PTS, sparse extrapolation, AU writeback, invalid pointer");return 0;
}
'''
    results={}
    for label,text in [('before',upstream.decode()),('after',media_runtime_patch.render(upstream,experimental_audio_clock=True))]:
        start=text.index('uint32_t mpeg_atrac_decode(');end=text.index('uint32_t mpeg_avc_decode_stop(',start)
        cpp=folder/(label+'.c');exe=folder/(label+'.exe');cpp.write_text(header+text[start:end]+tail)
        subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2',str(cpp),'-o',str(exe)],env=title.environment(),check=True,capture_output=True)
        run=subprocess.run([str(exe)],capture_output=True,text=True);results[label]=dict(returncode=run.returncode,stdout=run.stdout.strip())
    passed=results['before']['returncode']==10 and results['after']['returncode']==0
    (folder/'result.json').write_text(json.dumps(dict(passed=passed,scope='synthetic-real-handler-clock-regression-not-codec-or-gameplay-test',native_candidate_accepted=False,reason='native half-second underruns in audio-source-clock-01; excluded from normal builds',runs=results),indent=2)+'\n')
    print(json.dumps(results));
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
