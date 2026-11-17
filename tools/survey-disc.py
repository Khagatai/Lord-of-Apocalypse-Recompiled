"""Read-only ISO9660 intake, rejecting any image other than the pinned dump."""
import argparse
import hashlib
import json
import struct
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTOR = 2048

def digest_file(path, algorithm):
    with path.open("rb") as source:
        return hashlib.file_digest(source, algorithm).hexdigest()

def sfo(data):
    magic, version, keys, values, count = struct.unpack_from("<5I", data)
    if magic != 0x46535000:
        raise ValueError("Invalid PARAM.SFO")
    result = {}
    for i in range(count):
        key, fmt, length, capacity, offset = struct.unpack_from("<HHIII", data, 20 + i * 16)
        key = data[keys + key:].split(b"\0", 1)[0].decode("utf8")
        value = data[values + offset:values + offset + length]
        if len(value) != length or length > capacity:
            raise ValueError("Invalid SFO entry bounds")
        result[key] = int.from_bytes(value, "little") if fmt == 0x404 else value.rstrip(b"\0").decode("utf8")
    return result

class ISO:
    def __init__(self, source):
        self.source = source
        self.size = source.seek(0, 2)
        primary = self.read(16 * SECTOR, SECTOR)
        if primary[:7] != b"\x01CD001\x01":
            raise ValueError("Expected primary ISO9660 descriptor at sector 16")
        if struct.unpack_from("<H", primary, 128)[0] != SECTOR:
            raise ValueError("Unsupported sector size")
        self.root = self.record(primary[156:])

    def read(self, offset, length):
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError("ISO extent outside source image")
        self.source.seek(offset)
        value = self.source.read(length)
        if len(value) != length:
            raise ValueError("Truncated ISO read")
        return value

    @staticmethod
    def record(data):
        length = data[0]
        if length < 34 or length > len(data):
            raise ValueError("Invalid directory record length")
        lba = struct.unpack_from("<I", data, 2)[0]
        size = struct.unpack_from("<I", data, 10)[0]
        if lba != struct.unpack_from(">I", data, 6)[0] or size != struct.unpack_from(">I", data, 14)[0]:
            raise ValueError("ISO endian copies disagree")
        if data[25] & 0x80 or data[1] or data[26] or data[27]:
            raise ValueError("Unsupported multi-extent, extended attribute or interleaved file")
        name = data[33:33 + data[32]]
        if len(name) != data[32]:
            raise ValueError("Invalid directory filename")
        return {"lba": lba, "size": size, "directory": bool(data[25] & 2), "name": name}

    def files(self):
        pending = [("", self.root)]
        visited = set()
        result = {}
        while pending:
            prefix, parent = pending.pop()
            identity = (parent["lba"], parent["size"])
            if identity in visited:
                raise ValueError("Cyclic or aliased directory")
            visited.add(identity)
            data = self.read(parent["lba"] * SECTOR, parent["size"])
            offset = 0
            while offset < len(data):
                if not data[offset]:
                    offset = (offset // SECTOR + 1) * SECTOR
                    continue
                record = self.record(data[offset:offset + data[offset]])
                record["record_offset"] = parent["lba"] * SECTOR + offset
                offset += data[offset]
                if record["name"] in (b"\0", b"\x01"):
                    continue
                name = record.pop("name").decode("ascii").split(";", 1)[0]
                if name in ("", ".", "..") or "/" in name or "\\" in name:
                    raise ValueError("Unsafe ISO filename")
                path = prefix + name
                if record["directory"]:
                    pending.append((path + "/", record))
                else:
                    if path in result:
                        raise ValueError("Duplicate ISO path; physical record policy needed")
                    result[path] = record
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    config = tomllib.loads((ROOT / "config/lordofapocalypse.toml").read_text())
    expected = config["disc"]
    # Reject before extracting content, allocating guest memory or generating code.
    if args.image.stat().st_size != expected["iso_size"]:
        raise ValueError("Disc size mismatch")
    hashes = {name: digest_file(args.image, name) for name in ("sha1", "sha256")}
    if any(hashes[name] != expected["iso_" + name] for name in hashes):
        raise ValueError("Disc hash mismatch")
    with args.image.open("rb") as source:
        iso = ISO(source)
        files = iso.files()
        metadata = sfo(iso.read(files["PSP_GAME/PARAM.SFO"]["lba"] * SECTOR,
                                files["PSP_GAME/PARAM.SFO"]["size"]))
        if (metadata["DISC_ID"], metadata["DISC_VERSION"], metadata["APP_VER"]) != (
                expected["id"], expected["version"], expected["app_version"]):
            raise ValueError("Disc metadata mismatch")
        modules = []
        for path, extent in sorted(files.items()):
            if not (path in config["disc"]["files"] or path.lower().endswith((".prx", ".elf"))
                    or (path.startswith("PSP_GAME/SYSDIR/") and path.endswith(".BIN"))):
                continue
            data = iso.read(extent["lba"] * SECTOR, extent["size"])
            sha1 = hashlib.sha1(data).hexdigest()
            if path in config["disc"]["files"] and sha1 != config["disc"]["files"][path]:
                raise ValueError(f"Module hash mismatch: {path}")
            magic = data[:4]
            status = {b"~PSP": "encrypted-PSP", b"~SCE": "SCE-wrapper",
                      b"\x7fELF": "plaintext-ELF"}.get(magic, "unrecognized")
            if not any(data):
                status = "zero-filled-placeholder"
            output = ROOT / "private/disc" / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
            modules.append({"path": path, **extent, "sha1": sha1,
                            "sha256": hashlib.sha256(data).hexdigest(), "format": status})
        report = {"disc": metadata, "size": args.image.stat().st_size, **hashes,
                  "files": files, "modules": modules,
                  "runtime_modules_and_overlays": "unknown-requires-PPSSPP-load-trace-and-archive-survey"}
    report_path = ROOT / "private/disc-survey.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"disc": metadata, "file_count": len(files), "modules": modules}, indent=2))

if __name__ == "__main__":
    main()
