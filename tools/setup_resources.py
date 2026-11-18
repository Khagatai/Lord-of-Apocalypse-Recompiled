"""Select setup concurrency and measure or cap each Windows build process tree."""
import contextlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import runpy
import subprocess
import sys

MIB = 1024**2
GIB = 1024**3
MAX_COMPILER_WORKERS = 16
OPTIONS = {'compiler_jobs': tuple(range(MAX_COMPILER_WORKERS+1)),
           'memory_gib': (0, 4, 6, 8, 12, 16, 24, 32),
           'hd_profile': ('standard', 'low-memory', 'fast')}
DEFAULTS = {name: choices[0] for name, choices in OPTIONS.items()}
HD_PROFILES = {'standard': (64,256,64,'1:2:2'),
               'low-memory': (24,96,24,'1:1:1'),
               'fast': (128,512,64,'1:2:2')}


def validate(value):
    if not isinstance(value, dict) or value.keys() != OPTIONS.keys():
        raise ValueError('Unrecognized build settings')
    for name, choices in OPTIONS.items():
        if type(value[name]) is not type(choices[0]) or value[name] not in choices:
            raise ValueError('Unsupported build setting: '+name)
    return value


def codes(value):
    return [choices.index(value[name]) for name,choices in OPTIONS.items()]


def from_codes(values):
    if len(values)!=len(OPTIONS) or any(not 0<=i<len(choices) for i,choices in zip(values,OPTIONS.values())):
        raise ValueError('Unrecognized build setting choices')
    return {name:choices[i] for i,(name,choices) in zip(values,OPTIONS.items())}

def available_memory():
    if os.name!='nt':return 4*1024**3
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
            ('total_physical','available_physical','total_page','available_page','total_virtual','available_virtual','available_extended')]
    value=Memory();value.length=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):return 4*1024**3
    return value.available_physical

def compiler_workers(cpus=None,memory=None, *, requested=0,memory_gib=0):
    cpus=cpus if cpus is not None else (os.process_cpu_count() or 1)
    memory=memory if memory is not None else available_memory()
    if not 0<=requested<=MAX_COMPILER_WORKERS or memory_gib not in OPTIONS['memory_gib']:
        raise ValueError('Unsupported compiler job count or memory limit')
    # Automatic keeps one logical CPU and 2 GiB available. Manual jobs are a
    # ceiling and can use all CPUs, subject to the same memory calculation.
    budget = memory-2*GIB
    if memory_gib:budget = min(budget, memory_gib*GIB-512*MIB)
    return max(1,min(requested or 8, cpus if requested else cpus-1, budget//(1536*MIB)))


class BasicLimits(ctypes.Structure):
    _fields_ = [('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',wintypes.DWORD),
                ('min_working_set',ctypes.c_size_t),('max_working_set',ctypes.c_size_t),('active_processes',wintypes.DWORD),
                ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [('basic',BasicLimits),('io',ctypes.c_uint64*6),('process_memory',ctypes.c_size_t),
                ('job_memory',ctypes.c_size_t),('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]


class Job:
    def __init__(self, limit_bytes):
        k = self.kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        signatures = {'CreateJobObjectW':(wintypes.HANDLE,(ctypes.c_void_p,wintypes.LPCWSTR)),
                      'OpenProcess':(wintypes.HANDLE,(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)),
                      'AssignProcessToJobObject':(wintypes.BOOL,(wintypes.HANDLE,wintypes.HANDLE)),
                      'SetInformationJobObject':(wintypes.BOOL,(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD)),
                      'QueryInformationJobObject':(wintypes.BOOL,(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p)),
                      'CloseHandle':(wintypes.BOOL,(wintypes.HANDLE,))}
        for name,(result,args) in signatures.items():
            api=getattr(k,name);api.restype=result;api.argtypes=args
        self.handle = k.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        limits=ExtendedLimits()
        limits.basic.flags=0x2000 | (0x0200 if limit_bytes else 0)  # KILL_ON_JOB_CLOSE | JOB_MEMORY
        limits.job_memory=limit_bytes
        if not k.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
            error=ctypes.WinError(ctypes.get_last_error());self.close();raise error

    def attach(self,pid):
        process=self.kernel.OpenProcess(0x0101,False,pid)  # SET_QUOTA | TERMINATE
        if not process:raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.kernel.AssignProcessToJobObject(self.handle,process):raise ctypes.WinError(ctypes.get_last_error())
        finally:self.kernel.CloseHandle(process)

    def peak(self):
        limits=ExtendedLimits()
        if not self.kernel.QueryInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits),None):
            return None
        return limits.peak_job_memory

    def close(self):
        self.kernel.CloseHandle(self.handle)


@contextlib.contextmanager
def run_stage(script, args, limit_bytes=0, **kwargs):
    """Wait for job assignment before the Python stage can start any workers."""
    job=process=None
    try:
        if os.name=='nt':
            try:job=Job(limit_bytes)
            except OSError:
                if limit_bytes:raise
                print('Windows build memory tracking is unavailable.',flush=True)
        elif limit_bytes:
            raise OSError('The build memory limit requires Windows')
        prefix=[str(Path(__file__).resolve()),'--stage-gate'] if job else []
        process=subprocess.Popen([sys.executable,'-u',*prefix,str(script),*map(str,args)],
                                 stdin=subprocess.PIPE if job else None,**kwargs)
        if job:
            try:job.attach(process.pid)
            except OSError:
                job.close();job=None
                if limit_bytes:raise
                print('Windows build memory tracking is unavailable for this stage.',flush=True)
            process.stdin.write('start\n' if getattr(process.stdin,'encoding',None) else b'start\n')
            process.stdin.close()
        yield process,job
    finally:
        if job:job.close()
        if process and process.poll() is None:
            if process.stdin is not None and not process.stdin.closed:process.stdin.close()
            process.kill();process.wait()


if __name__=='__main__':
    if sys.argv[1:2]==['--stage-gate']:
        if sys.stdin.buffer.readline().rstrip(b'\r\n')!=b'start':raise SystemExit(1)
        sys.argv=sys.argv[2:]
        runpy.run_path(sys.argv[0],run_name='__main__')
    else:
        # The launcher can schedule more compiler jobs without changing title.py
        # or causing a cached native build to be recompiled on upgrade.
        import argparse
        import title
        p=argparse.ArgumentParser(description='Run a native stage from local player setup')
        p.add_argument('stage',choices=('generate','build'))
        p.add_argument('--jobs',type=int,choices=range(1,MAX_COMPILER_WORKERS+1),required=True)
        p.add_argument('--force',action='store_true')
        a=p.parse_args()
        title.build(a.stage,a.jobs,'release',force=a.force)
