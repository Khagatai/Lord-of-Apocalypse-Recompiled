import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import camera_codegen as camera,title

class CameraMotion(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='win32','Windows compiler and SDL')
    def test_runtime_lock_on_leaves_original_pose_and_clears_free_camera_motion(self):
        # Execute the production helper with a bounded synthetic guest arena and
        # a real SDL virtual gamepad; no game binary or save is a test dependency.
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            (p/'recomp.h').write_text('''#include <stdint.h>
#include <string.h>
typedef struct {uint32_t r[32];} CpuState;
extern unsigned char ram[0x1800000];
extern uint32_t vcount;
static uint32_t sr_display_vcount(void){return vcount;}
static int sr_guest_span_readable(uint32_t a,uint32_t n){return a>=0x08800000u && n<=sizeof ram && a-0x08800000u<=sizeof ram-n;}
#define sr_guest_span_writable sr_guest_span_readable
static uint32_t r32(uint32_t a){uint32_t v;memcpy(&v,ram+a-0x08800000u,4);return v;}
static void w32(uint32_t a,uint32_t v){memcpy(ram+a-0x08800000u,&v,4);}
#define MEM_R32 r32
#define MEM_W32 w32
#define MEM_R8(a) ram[(a)-0x08800000u]
''')
            (p/'check.c').write_text('''#include "recomp.h"
#include <SDL3/SDL.h>
#include <assert.h>
#include <stdlib.h>
unsigned char ram[0x1800000];uint32_t vcount=100;
void loa_camera_set_options(int,int);
int loa_camera_free_input(void);
void loa_camera_update(CpuState *,uint32_t,uint32_t);
static const uint32_t manager=0x08d852c8u,camera=0x08900000u,player=0x08901000u,sp=0x09ff0000u;
static void put_float(uint32_t a,float v){uint32_t bits;memcpy(&bits,&v,4);w32(a,bits);}
static void unchanged_update(CpuState *s){
 unsigned char pose[0xbc],eye[12],angle[4];CpuState cpu=*s;
 memcpy(pose,ram+camera-0x08800000u,sizeof pose);memcpy(eye,ram+sp+0xa8-0x08800000u,12);memcpy(angle,ram+player+0x2728-0x08800000u,4);
 loa_camera_update(s,camera,player);
 assert(!memcmp(pose,ram+camera-0x08800000u,sizeof pose));assert(!memcmp(eye,ram+sp+0xa8-0x08800000u,12));assert(!memcmp(angle,ram+player+0x2728-0x08800000u,4));assert(!memcmp(&cpu,s,sizeof cpu));
}
int main(void){
 assert(SDL_Init(SDL_INIT_GAMEPAD));
 SDL_VirtualJoystickDesc desc;SDL_INIT_INTERFACE(&desc);desc.type=SDL_JOYSTICK_TYPE_GAMEPAD;desc.naxes=SDL_GAMEPAD_AXIS_COUNT;desc.nbuttons=SDL_GAMEPAD_BUTTON_COUNT;
 desc.axis_mask=(1u<<SDL_GAMEPAD_AXIS_COUNT)-1;desc.button_mask=(1u<<SDL_GAMEPAD_BUTTON_COUNT)-1;desc.name="LoA lock-on regression fixture";
 SDL_JoystickID id=SDL_AttachVirtualJoystick(&desc);assert(id);SDL_Gamepad *pad=SDL_OpenGamepad(id);assert(pad);SDL_Joystick *joy=SDL_GetGamepadJoystick(pad);
 CpuState s={0};s.r[29]=sp;
 for(int fps=30;fps<=60;fps+=30){
  _putenv_s("LOA_GAMEPLAY_FPS",fps==30?"30":"60");memset(ram,0,sizeof ram);
  w32(manager+16,camera);MEM_R8(manager+0x190)=3;w32(camera+4,0x08cefc5c);
  put_float(sp+0xa8+4,100);put_float(sp+0xa8+8,300);
  loa_camera_set_options(1,2);assert(loa_camera_free_input());
  SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_RIGHTX,32767);SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_RIGHTY,-32768);SDL_UpdateGamepads();
  loa_camera_update(&s,camera,player);assert(r32(sp+0xa8)!=0); /* Smooth motion was active. */
  w32(camera+0xa4,1);assert(!loa_camera_free_input());
  for(int i=0;i<10;i++){vcount+=fps==30?2:1;unchanged_update(&s);}
  SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_RIGHTX,0);SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_RIGHTY,0);SDL_UpdateGamepads();
  w32(camera+0xa4,0);vcount+=fps==30?2:1;assert(loa_camera_free_input());unchanged_update(&s); /* No inherited tilt or velocity on unlock. */
  MEM_R8(camera+0xb8)=1;assert(!loa_camera_free_input());unchanged_update(&s);MEM_R8(camera+0xb8)=0;
  w32(camera+4,0);assert(!loa_camera_free_input());unchanged_update(&s);w32(camera+4,0x08cefc5c);
  MEM_R8(manager+0x190)=0;assert(!loa_camera_free_input());unchanged_update(&s);MEM_R8(manager+0x190)=3;
  w32(manager+16,0xffffffffu);assert(!loa_camera_free_input());unchanged_update(&s);w32(manager+16,camera);
  loa_camera_set_options(0,2);assert(!loa_camera_free_input());unchanged_update(&s);
 }
 SDL_CloseGamepad(pad);SDL_DetachVirtualJoystick(id);SDL_Quit();return 0;
}''')
            exe=p/'check.exe'
            run=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(p),'-I'+str(ROOT/'tools'),'-I'+str(title.SDK/'include'),str(p/'check.c'),str(ROOT/'tools/camera_runtime.c'),'-L'+str(title.SDK/'lib'),'-lSDL3','-lm','-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            result=subprocess.run([str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_codegen_is_bound_to_measured_instruction_and_function(self):
        rows=['void f_08872590(CpuState *s) {',f'    sr_begin(s, 0x{camera.PC:08x}u, 0x{camera.WORD:08x}u); s->fi[20]=MEM_R32(s->r[21]);', '}']
        result='\n'.join(camera.rewrite(rows,camera.START))
        self.assertEqual(result.count('loa_camera_update(s,s->r[16],s->r[19]);'),1)
        self.assertIn(rows[1].strip(),result)
        self.assertEqual(camera.rewrite(rows,camera.START+4),rows)
        with self.assertRaises(ValueError):camera.rewrite([s.replace('c6b40000','c6b40004') for s in rows],camera.START)
    @unittest.skipUnless(sys.platform=='win32','Windows compiler')
    def test_native_motion_timing_deadzone_and_release(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);source=folder/'camera.c';exe=folder/'camera.exe'
            source.write_text('''#include <assert.h>
#include "camera_motion.h"
int main(void){
 assert(loa_camera_axis(0)==0 && loa_camera_axis(7000)==0 && loa_camera_axis(-7000)==0);
 assert(loa_camera_axis(32767)==1 && loa_camera_axis(-32768)==-1);
 assert(loa_camera_axis(16000)>0 && loa_camera_axis(16000)<0.5f);
 LoaCameraMotion a={0},b={0};
 for(int i=0;i<60;i++)loa_camera_integrate(&a,1,1.0f/30,1);
 for(int i=0;i<120;i++)loa_camera_integrate(&b,1,1.0f/60,1);
 assert(fabsf(a.yaw-b.yaw)<0.00001f && fabsf(a.velocity-b.velocity)<0.00001f);
 assert(fabsf(a.yaw-(-2.2402f))<0.001f);
 for(int i=0;i<30;i++)loa_camera_integrate(&a,0,1.0f/30,1);
 for(int i=0;i<60;i++)loa_camera_integrate(&b,0,1.0f/60,1);
 assert(fabsf(a.yaw-b.yaw)<0.00001f && fabsf(a.velocity)<0.00001f);
 LoaCameraMotion slow={0},fast={0};
 for(int i=0;i<60;i++){loa_camera_integrate(&slow,0.25f,1.0f/60,0.5f);loa_camera_integrate(&fast,0.25f,1.0f/60,2);}
 assert(fabsf(fast.yaw-4*slow.yaw)<0.00001f);
 LoaCameraMotion pitch30={0},pitch60={0};
 for(int i=0;i<15;i++)loa_camera_integrate_pitch(&pitch30,-0.6f,1.0f/30,1);
 for(int i=0;i<30;i++)loa_camera_integrate_pitch(&pitch60,-0.6f,1.0f/60,1);
 assert(fabsf(pitch30.yaw-pitch60.yaw)<0.00001f);
 assert(pitch30.yaw<0 && pitch30.yaw>-0.4f);
 for(int i=0;i<300;i++)loa_camera_integrate_pitch(&pitch30,1,1.0f/30,2);
 assert(fabsf(pitch30.yaw-1.3962634f)<0.00001f && pitch30.velocity==0);
 for(int i=0;i<300;i++)loa_camera_integrate_pitch(&pitch30,-1,1.0f/30,2);
 assert(fabsf(pitch30.yaw+1.3962634f)<0.00001f && pitch30.velocity==0);
 float held=pitch30.yaw;
 for(int i=0;i<60;i++)loa_camera_integrate_pitch(&pitch30,0,1.0f/60,1);
 assert(pitch30.yaw==held); /* No return to a discrete PSP position on release. */
 loa_camera_integrate_pitch(&pitch30,1,1.0f/60,1);
 assert(pitch30.yaw>held); /* Reverses immediately from either limit. */
 return 0;
}''')
            build=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(ROOT/'tools'),str(source),'-o',str(exe),'-lm'],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

if __name__=='__main__':unittest.main()
