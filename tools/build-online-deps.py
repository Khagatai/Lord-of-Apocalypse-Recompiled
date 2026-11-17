"""Build pinned native WebRTC/TLS libraries in one ignored working directory."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SDK=ROOT/'private/toolchain/prerequisites/msys64/ucrt64'
PINS=json.loads((ROOT/'config/online-dependencies.json').read_text())
def run(*args,**kwargs):subprocess.run(list(map(str,args)),check=True,**kwargs)
def main():
    env=dict(os.environ);env['PATH']=str(SDK/'bin')+os.pathsep+env['PATH']
    for name,pin in PINS.items():
        folder=ROOT/'private/tools'/name
        if not folder.exists():run('git','clone','--depth','1','--branch',pin['tag'],pin['url'],folder,env=env)
        revision=subprocess.check_output(['git','-c',f'safe.directory={folder.as_posix()}','-C',str(folder),'rev-parse','HEAD'],text=True).strip()
        if revision!=pin['revision']:raise ValueError('Dependency revision changed: '+name)
        paths=['deps/plog','deps/usrsctp','deps/libjuice'] if name=='libdatachannel' else []
        run('git','-c',f'safe.directory={folder.as_posix()}','-C',folder,'submodule','update','--init','--depth','1',*paths,env=env)
    work=ROOT/'private/online-deps';work.mkdir(exist_ok=True)
    (work/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.21)
project(loa_online LANGUAGES C CXX)
add_compile_definitions(MBEDTLS_SSL_DTLS_SRTP)
set(ENABLE_TESTING OFF CACHE BOOL "" FORCE)
set(ENABLE_PROGRAMS OFF CACHE BOOL "" FORCE)
set(DISABLE_PACKAGE_CONFIG_AND_INSTALL ON CACHE BOOL "" FORCE)
add_subdirectory("${LOA_ROOT}/private/tools/mbedtls" mbedtls)
add_library(MbedTLS::MbedTLS INTERFACE IMPORTED)
set_target_properties(MbedTLS::MbedTLS PROPERTIES INTERFACE_LINK_LIBRARIES "mbedtls;mbedx509;mbedcrypto" INTERFACE_INCLUDE_DIRECTORIES "${LOA_ROOT}/private/tools/mbedtls/include")
set(USE_MBEDTLS ON CACHE BOOL "" FORCE)
set(NO_MEDIA ON CACHE BOOL "" FORCE)
set(NO_WEBSOCKET ON CACHE BOOL "" FORCE)
set(NO_EXAMPLES ON CACHE BOOL "" FORCE)
set(NO_TESTS ON CACHE BOOL "" FORCE)
add_subdirectory("${LOA_ROOT}/private/tools/libdatachannel" datachannel)
''')
    cmake=ROOT/'private/tools/cmake-3.31.5-windows-x86_64/bin/cmake.exe'
    run(cmake,'-S',work,'-B',work/'build','-G','MinGW Makefiles',f'-DLOA_ROOT={ROOT.as_posix()}',
        '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
        f'-DCMAKE_C_COMPILER={(SDK/"bin/gcc.exe").as_posix()}',f'-DCMAKE_CXX_COMPILER={(SDK/"bin/g++.exe").as_posix()}',
        '-DCMAKE_SHARED_LINKER_FLAGS=-static-libgcc -static-libstdc++',env=env)
    run(cmake,'--build',work/'build','--target','datachannel','--parallel','6',env=env)
    dll=work/'build/datachannel/libdatachannel.dll'
    if not dll.is_file():raise FileNotFoundError(dll)
    result=dict(pins=PINS,dll_sha256=hashlib.sha256(dll.read_bytes()).hexdigest())
    (work/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Built native libdatachannel:',dll)
if __name__=='__main__':main()
