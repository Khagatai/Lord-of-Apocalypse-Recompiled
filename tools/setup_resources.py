"""Choose bounded setup concurrency from available CPUs and physical memory."""
import ctypes,os

def available_memory():
    if os.name!='nt':return 4*1024**3
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
            ('total_physical','available_physical','total_page','available_page','total_virtual','available_virtual','available_extended')]
    value=Memory();value.length=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):return 4*1024**3
    return value.available_physical

def compiler_workers(cpus=None,memory=None):
    cpus=cpus if cpus is not None else (os.process_cpu_count() or 1)
    memory=memory if memory is not None else available_memory()
    # Leave one CPU and 2 GiB for the desktop; budget 1.5 GiB per compiler.
    return max(1,min(8,max(1,cpus-1),max(1,(memory-2*1024**3)//(1536*1024**2))))
