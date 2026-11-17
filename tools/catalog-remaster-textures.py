"""Private archive coverage inventory using the pinned runtime's hash algorithms.

Predicted identities are candidates, not evidence that an asset was rendered.
Both host alignment branches are catalogued; no guest allocation address is assumed.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import title
from rgf_archive import parse_index, resources
from xet_codec import Xet, extent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(ROOT/'private'):
        raise ValueError('Game-derived inputs and outputs must stay private')
    return path


def adapter(output):
    """Compile actual upstream implementations; never substitute hash approximations."""
    framework = ROOT/'external/nakagawa-recomp'
    runtime = framework/'src/rt'
    core = framework/'src/core'
    source = ROOT/'tools/xet-runtime-identity.c'
    sources = [source, runtime/'texrepl.c', core/'nk_zip.c', core/'nk_psp_inflate.c',
               core/'nk_platform_win32.c', core/'nk_shared_helpers.c']
    dll = output/'xet-runtime-identity.dll'
    command = [str(title.SDK/'bin/gcc.exe'), '-O2', '-shared', '-ffunction-sections',
               '-fdata-sections', '-Wl,--gc-sections,--exclude-all-symbols',
               '-I'+str(runtime), '-I'+str(core), *map(str, sources),
               '-lshell32', '-lole32', '-luuid', '-luser32', '-ladvapi32', '-lshlwapi',
               '-o', str(dll)]
    with (output/'adapter-build.log').open('w') as log:
        subprocess.run(command, env=title.environment(), stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=120)
    lib = ctypes.CDLL(str(dll))
    lib.loa_quick.argtypes = (ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32)
    lib.loa_quick.restype = ctypes.c_uint32
    lib.loa_clut.argtypes = (ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32)
    lib.loa_clut.restype = ctypes.c_uint32
    lib.loa_key.argtypes = (ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32)
    lib.loa_key.restype = ctypes.c_uint64
    return lib, dict(dll_sha256=sha(dll.read_bytes()),
                     source_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sources})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=private_path, required=True)
    parser.add_argument('--output', type=private_path, required=True)
    parser.add_argument('--capture', type=private_path, help='Compare every captured authored mip')
    parser.add_argument('--decode', action='store_true', help='Hash every decodable authored mip')
    parser.add_argument('--export-rgba', action='store_true', help='Export deduplicated private decoded mip data; implies --decode')
    args = parser.parse_args()
    title.verify_inputs()
    if args.output.exists():
        raise ValueError('Use a fresh output directory')
    args.output.mkdir(parents=True)
    if args.export_rgba:
        args.decode = True
        (args.output/'rgba').mkdir()
    lib, build = adapter(args.output)
    observed = {}
    capture_hash = None
    if args.capture:
        capture_file = args.capture/'mip-capture.jsonl'
        capture_hash = sha(capture_file.read_bytes())
        for line in capture_file.read_text().splitlines():
            row = json.loads(line)
            if row.get('written') is not True:
                raise ValueError('Incomplete native capture')
            file = (args.capture/row['file']).resolve()
            if not file.is_relative_to(args.capture):
                raise ValueError('Captured data path escapes capture folder')
            key = '00000000'+row['key'][8:]
            observed.setdefault((key, row['level']), set()).add(sha(file.read_bytes()))
    rzl, rzp = (args.archives/name for name in ('REGFILE.RZL', 'REGFILE.RZP'))
    groups = parse_index(rzl.read_bytes(), rzp.stat().st_size)
    seen = set()
    catalog, skipped, comparisons = [], [], []
    decoded_cache = {}
    with rzp.open('rb') as stream:
        for group, identity, raw in resources(stream, groups):
            if identity >> 16 != 2:
                continue
            source_hash = sha(raw)
            if (identity, source_hash) in seen:
                continue
            seen.add((identity, source_hash))
            xet = Xet.parse(raw)
            for index, texture in enumerate(xet.textures):
                mip = texture.mips[0]
                fmt = texture.format
                entry = dict(resource_id=f'{identity:08x}', source_sha256=source_hash,
                             texture_index=index, name=texture.name, width=mip.width,
                             height=mip.height, format=fmt, mip_levels=len(texture.mips))
                if (fmt not in range(8) or mip.width != mip.stride or
                    mip.width & (mip.width-1) or mip.height & (mip.height-1) or
                    max(mip.width, mip.height) > 512):
                    skipped.append(dict(**entry, reason='Unmeasured identity geometry/format'))
                    continue
                bits = (16,16,16,32,4,8,16,32)[fmt]
                # texrepl.c::nk_texrepl_hash_texture hashes the logical byte
                # count for contiguous rows, even when the sampler reads a
                # larger padded swizzle extent. Do not conflate these spans.
                data = extent(raw, mip.offset, mip.stride*mip.height*bits//8)
                clut_hash = 0
                if fmt >= 4:
                    colour, shift, mask, blocks, offset = xet.palettes[texture.palette_index]
                    # Match GE LOADCLUT's byte extent, independent of colour size.
                    palette = extent(raw, offset, blocks*32)
                    cf = colour | (shift << 2) | (mask << 8)
                    clut_hash = lib.loa_clut(palette, len(palette), cf, fmt)
                dim = (mip.width.bit_length()-1) | ((mip.height.bit_length()-1) << 8)
                cache = lib.loa_key(fmt, dim, clut_hash)
                keys = sorted(set(f'{cache:016x}{lib.loa_quick(data,len(data),address):08x}'
                                  for address in (0,1)))
                entry['candidate_keys'] = keys
                levels = []
                for level, authored in enumerate(texture.mips):
                    item = dict(level=level, width=authored.width, height=authored.height)
                    relevant = [key for key in keys if (key,level) in observed]
                    if args.decode or relevant:
                        cache_id = source_hash, index, level
                        if cache_id not in decoded_cache:
                            try:
                                w,h,pixels = xet.preview_mip(index,level,limit=512)
                                pixel_hash = sha(pixels)
                                decoded_cache[cache_id] = dict(rgba_sha256=pixel_hash,
                                    opaque=all(a==255 for a in pixels[3::4]))
                                if args.export_rgba:
                                    target = args.output/'rgba'/(pixel_hash+'.rgba')
                                    if not target.exists():
                                        target.write_bytes(pixels)
                            except ValueError as error:
                                decoded_cache[cache_id] = dict(decode_error=str(error))
                        item.update(decoded_cache[cache_id])
                        for key in relevant:
                            comparisons.append(dict(key=key,level=level,
                                resource_id=entry['resource_id'],texture_index=index,
                                match=item.get('rgba_sha256') in observed[key,level],
                                **decoded_cache[cache_id]))
                    levels.append(item)
                entry['authored_levels'] = levels
                catalog.append(entry)
                if len(catalog) % 1000 == 0:
                    print(json.dumps(dict(descriptors=len(catalog))),flush=True)
    matched = {(r['key'],r['level']) for r in comparisons if r['match']}
    signatures = {}
    for entry in catalog:
        levels = entry['authored_levels']
        if not all('rgba_sha256' in row for row in levels):
            continue
        signature = (entry['width'],entry['height'],tuple(row['rgba_sha256'] for row in levels))
        for key in entry['candidate_keys']:
            signatures.setdefault(key,set()).add(signature)
    conflicts = sorted(k for k,v in signatures.items() if len(v)>1)
    pixel_mismatches = [r for r in comparisons if not r['match'] and 'rgba_sha256' in r]
    with rzp.open('rb') as stream:
        archive_hash = hashlib.file_digest(stream,'sha256').hexdigest()
    report = dict(scope='archive-identity-candidates-not-full-game-validation',
                  descriptors=len(catalog),source_variants=len(seen),skipped=len(skipped),
                  unique_candidate_keys=len({k for r in catalog for k in r['candidate_keys']}),
                  decoded_levels=len(decoded_cache),observed_key_levels=len(observed),
                  matched_key_levels=len(matched),unmatched_key_levels=sorted(set(observed)-matched),
                  decoded_pixel_mismatches=len(pixel_mismatches),ambiguous_decoded_keys=conflicts,
                  total_authored_levels=sum(len(r['authored_levels']) for r in catalog),
                  refused_level_instances=sum('decode_error' in l for r in catalog for l in r['authored_levels']),
                  complete_decoded_descriptors=sum(all('rgba_sha256' in l for l in r['authored_levels']) for r in catalog),
                  exported_rgba=args.export_rgba,archive_sha256=archive_hash,
                  capture_sha256=capture_hash,build=build,runtime_address_assumed=False,
                  unseen_keys_runtime_validated=False,complete_hd_pack=False,
                  index_sha256=sha(rzl.read_bytes()))
    for name,value in (('catalog',catalog),('skipped',skipped),('comparisons',comparisons),('result',report)):
        (args.output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__ == '__main__':
    main()
