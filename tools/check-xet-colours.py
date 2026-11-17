"""Compare every 16-bit colour with conversion code from the pinned PPSSPP Git object."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import title
from xet_codec import Xet


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(source, name):
    start = source.index('inline u32 '+name+'(')
    opened = source.index('{', start)
    depth = 1
    end = opened+1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT/'private') or output.exists():
        parser.error('Use fresh private output')
    reference = ROOT/'private/tools/ppsspp'
    revision = title.CONFIG['tools']['ppsspp']['commit']
    path = 'Common/Data/Convert/ColorConv.h'
    header = subprocess.check_output(['git', '-c', f'safe.directory={reference.as_posix()}',
        '-C', str(reference), 'show', revision+':'+path])
    names = ('RGB565ToRGBA8888', 'RGBA5551ToRGBA8888', 'RGBA4444ToRGBA8888')
    functions = [function(header.decode('utf-8'), name) for name in names]
    source = '#include <stdint.h>\n#include <stdio.h>\nusing u16=uint16_t;using u32=uint32_t;\n'
    source += '\n'.join(functions)
    source += '\nint main(int argc,char **argv){if(argc!=2)return 1;FILE *out=fopen(argv[1],"wb");if(!out)return 2;'
    source += 'u32(*functions[])(u16)={'+','.join(names)+'};'
    source += 'for(int fmt=0;fmt<3;fmt++)for(int v=0;v<65536;v++){u32 c=functions[fmt]((u16)v);if(fwrite(&c,4,1,out)!=1)return 3;}return fclose(out)!=0;}\n'
    output.mkdir(parents=True)
    cpp, executable, pixels = (output/name for name in ('reference.cpp', 'reference.exe', 'reference.bin'))
    cpp.write_text(source, encoding='utf-8')
    compiler = title.SDK/'bin/g++.exe'
    build = subprocess.run([str(compiler), '-std=c++17', '-O2', '-static', str(cpp), '-o', str(executable)],
        env=title.environment(), capture_output=True, timeout=120)
    (output/'build.log').write_bytes(build.stdout+build.stderr)
    build.check_returncode()
    subprocess.run([str(executable), str(pixels)], check=True, timeout=30)
    raw = pixels.read_bytes()
    if len(raw) != 3*65536*4:
        raise ValueError('Incomplete reference output')
    mismatches, examples = 0, []
    for fmt in range(3):
        for value in range(65536):
            offset = (fmt*65536+value)*4
            actual = Xet.rgba(value.to_bytes(2, 'little'), fmt)
            expected = raw[offset:offset+4]
            if actual != expected:
                mismatches += 1
                if len(examples) < 12:
                    examples.append(dict(format=fmt, value=value, expected=expected.hex(), actual=actual.hex()))
    result = dict(scope='exhaustive-pinned-ppsspp-colour-conversion-check', passed=mismatches == 0,
        reference_revision=revision, reference_path=path, reference_header_sha256=sha(header),
        reference_function_sha256={name:sha(code.encode()) for name,code in zip(names,functions)},
        decoder_sha256=sha((ROOT/'tools/xet_codec.py').read_bytes()), compiler_sha256=sha(compiler.read_bytes()),
        executable_sha256=sha(executable.read_bytes()), reference_pixels_sha256=sha(raw),
        cases=3*65536, mismatches=mismatches, examples=examples, campaign_validated=False)
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
