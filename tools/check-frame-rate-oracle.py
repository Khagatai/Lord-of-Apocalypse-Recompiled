"""Check the original NOP and optional timestep DIV in pinned PPSSPP's interpreter.

Synthetic register states at the measured instruction; not a gameplay trace.
All writes are to the oracle process's temporary memory, never the game dump.
"""
import argparse,hashlib,importlib.util,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve()
    if not out.is_relative_to(ROOT/'private') or out.exists():p.error('Use fresh private output')
    title.verify_inputs();image=title.disc_image();digest=title.verify_disc_image(image)
    source=ROOT/'private/tools/ppsspp'
    pin=subprocess.check_output(['git','-c',f'safe.directory={source.as_posix()}','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if pin!=title.CONFIG['tools']['ppsspp']['commit']:raise ValueError('Oracle pin differs')
    executable=source/'Windows/x64/Release/PPSSPPHeadless.exe'
    spec=importlib.util.spec_from_file_location('oracle',ROOT/'tools/capture-oracle.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    out.mkdir(parents=True);(out/'memstick').mkdir()
    command=[str(executable),str(image),'--cpu=interpreter','--graphics=software','--debugger=0',
        '--timeout-wall=60','--log','-d',f'--memstick={out/"memstick"}',f'--appendconfig={ROOT/"config/oracle.ini"}']
    client=None;process=None
    try:
        with (out/'ppsspp.log').open('wb') as log:
            process=subprocess.Popen(command,cwd=source,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+30
            while True:
                match=re.search(r'Listening on port (\d+)',(out/'ppsspp.log').read_text(errors='replace'))
                if match:break
                if process.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Oracle debugger unavailable')
                time.sleep(.1)
            client=module.Debugger(int(match[1]));pc=0x08cb3ddc
            modules=client.request('hle.module.list')
            active=[m for m in modules['modules'] if m['name']==title.CONFIG['module']['name'] and m['isActive']]
            if len(active)!=1 or active[0]['address']!=title.CONFIG['module']['base']:raise ValueError('Measured oracle load base differs')
            original=int.from_bytes(client.memory(pc,4),'little')
            if original!=0:raise ValueError('Original timestep instruction differs')
            cases=[]
            for name,opcode,initial,expected in [('original',0,0x40000000,0x40000000),
                    ('enhanced',0x4616b583,0x40000000,0x3f800000),('enhanced-steady',0x4616b583,0x3f800000,0x3f800000)]:
                client.request('memory.write_u32',address=pc,value=opcode)
                client.request('cpu.setReg',name='pc',value=pc)
                client.request('cpu.setReg',category=1,register=22,value=initial)
                before=client.request('cpu.getAllRegs');client.step();after=client.request('cpu.getAllRegs')
                fpu=next(c for c in after['categories'] if c['id']==1)
                actual=fpu['uintValues'][22]
                cases.append(dict(name=name,opcode=opcode,initial=initial,expected=expected,actual=actual,passed=actual==expected,before=before,after=after))
            client.request('memory.write_u32',address=pc,value=original)
            passed=all(c['passed'] for c in cases)
            report=dict(scope='synthetic-timestep-instruction-oracle-not-gameplay',passed=passed,
                iso_sha256=digest,ppsspp_revision=pin,executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                pc=pc,original_opcode=original,guest_image_on_disk_modified=False,cases=cases,gameplay_trace_matched=False)
            (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
            print('PASS: original 2.0, enhanced 1.0, enhanced steady 1.0' if passed else 'FAIL: instruction results differ')
            if not passed:raise ValueError('Oracle instruction mismatch')
    finally:
        if client:client.sock.close()
        if process:
            if process.poll() is None:process.terminate()
            process.wait(timeout=10)

if __name__=='__main__':main()
