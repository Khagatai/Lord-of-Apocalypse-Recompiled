"""Local-only decryption; never changes the input or invents missing plaintext."""
import argparse
import ctypes
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    # Outputs must remain in the ignored private tree, regardless of caller cwd.
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private"):
        parser.error("Decrypted output must stay under private/")
    data = args.module.read_bytes()
    input_hash = hashlib.sha256(data).hexdigest()
    offset = 0
    if data[:4] == b"~SCE":
        offset = int.from_bytes(data[4:8], "little")
        if offset < 8 or offset + 0x150 > len(data):
            raise ValueError("Invalid SCE wrapper length")
        data = data[offset:]
    if data[:4] != b"~PSP" or len(data) < 0x150:
        raise ValueError("Expected a PSP encrypted module")
    expected_size = int.from_bytes(data[0x28:0x2c], "little")
    if not 52 <= expected_size <= 64 * 1024 * 1024:
        raise ValueError("Unreasonable plaintext ELF size")
    bridge = ctypes.CDLL(str(ROOT / "private/tools/decrypt-build/prx-decrypt.dll"))
    bridge.decrypt_prx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    bridge.decrypt_prx.restype = ctypes.c_int
    source = ctypes.create_string_buffer(data)
    destination = ctypes.create_string_buffer(max(len(data), expected_size))
    count = bridge.decrypt_prx(source, destination, len(data))
    if count <= 0 or count > len(destination):
        raise RuntimeError(f"PRX decryption failed: {count}")
    result = destination.raw[:count]
    if result[:2] == b"\x1f\x8b":
        result = gzip.decompress(result)
    if result[:4] != b"\x7fELF" or len(result) != expected_size:
        raise ValueError(f"Plaintext ELF/size mismatch: {len(result)} != {expected_size}")
    if output == args.module.resolve():
        raise ValueError("Refusing to overwrite source module")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)
    print(json.dumps({"input_sha256": input_hash, "sce_wrapper_bytes": offset,
                      "elf_size": len(result), "sha1": hashlib.sha1(result).hexdigest(),
                      "sha256": hashlib.sha256(result).hexdigest()}, indent=2))

if __name__ == "__main__":
    main()
