"""Build the source-only title's native Windows x64 graphics panel locally."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import title


def main():
    title.verify_inputs()
    output = title.ROOT/'private/launcher'
    output.mkdir(parents=True, exist_ok=True)
    source = title.ROOT/'tools/graphics-menu.c'
    executable = output/'LordOfApocalypse-Launcher.exe'
    manifest = (title.ROOT/'config/graphics-menu.manifest').read_bytes()
    padded = manifest + b'\0'*(len(manifest)%2)
    resource = output/'menu.rc'
    resource.write_text('1 24 {\n'+','.join(f'0x{int.from_bytes(padded[i:i+2], "little"):04x}' for i in range(0,len(padded),2))+'\n}\n')
    resource_object = output/'menu-resources.o'
    resource_build = subprocess.run([str(title.SDK/'bin/windres.exe'), '--preprocessor=gcc.exe',
                                    '--preprocessor-arg=-E', '--preprocessor-arg=-xc', '--preprocessor-arg=-DRC_INVOKED',
                                    '-i', str(resource), '-o', str(resource_object)],
                                   env=title.environment(), capture_output=True, text=True)
    (output/'resource-build.log').write_text(resource_build.stdout+resource_build.stderr)
    if resource_build.returncode:
        raise RuntimeError(resource_build.stderr)
    command = [str(title.SDK/'bin/gcc.exe'), '-std=c11', '-O2', '-Wall', '-Wextra',
               '-municode', '-mwindows', '-static-libgcc', str(source), str(resource_object), '-o', str(executable),
               '-lcomctl32', '-lshell32', '-lgdi32', '-luser32']
    result = subprocess.run(command, env=title.environment(), capture_output=True, text=True)
    (output/'build.log').write_text(result.stdout+result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr)
    data = executable.read_bytes()
    pe = int.from_bytes(data[0x3c:0x40], 'little')
    if data[pe:pe+4] != b'PE\0\0' or int.from_bytes(data[pe+4:pe+6], 'little') != 0x8664:
        raise ValueError('Expected a Windows AMD64 menu executable')
    report = {'architecture': 'Windows x64', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'executable_sha256': hashlib.sha256(data).hexdigest(), 'command': command}
    (output/'build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'built': str(executable), 'sha256': report['executable_sha256']}, indent=2))


if __name__ == '__main__':
    main()
