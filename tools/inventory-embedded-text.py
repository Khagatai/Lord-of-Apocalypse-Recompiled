"""Read-only candidate scan of non-executable ELF data; not a visibility claim."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def readable(data, encoding):
    try:
        text = data.decode(encoding)
    except UnicodeError:
        return None
    if any(ord(c) < 32 and c not in "\r\n\t" for c in text):
        return None
    count = len(JAPANESE.findall(text))
    return text if count >= 4 and count / max(1, len(text)) >= 0.25 else None


def scan_elf(data):
    if data[:6] != b"\x7fELF\x01\x01":
        raise ValueError("Expected little-endian ELF32")
    offset = struct.unpack_from("<I", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 46)
    if count == 0 and offset == 0:
        return  # A sectionless module is reported as unscanned, not a zero-text pass.
    if size != 40 or offset + size*count > len(data):
        raise ValueError("Invalid ELF section table")
    for index in range(count):
        _, kind, flags, address, start, length, *_ = struct.unpack_from("<10I", data, offset+size*index)
        if kind != 1 or not flags & 2 or flags & 4:
            continue
        if start + length > len(data):
            raise ValueError("Section exceeds file")
        section = data[start:start+length]
        cursor = 0
        for raw in section.split(b"\0"):
            if 4 <= len(raw) <= 2048:
                for encoding in ("utf-8", "cp932"):
                    text = readable(raw, encoding)
                    if text:
                        yield {"section": index, "encoding": encoding, "file_offset": start+cursor,
                               "virtual_address": address+cursor, "text": text,
                               "raw_sha256": hashlib.sha256(raw).hexdigest(), "status": "candidate-unclassified"}
            cursor += len(raw)+1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private") or output.exists():
        parser.error("Use a fresh private output directory")
    output.mkdir(parents=True)
    report = {"scope": "null-terminated-UTF8-CP932-in-ELF-allocated-noncode-sections",
              "limitations": "Heuristic candidates; does not scan UTF16, textures, movies or prove strings are displayed", "modules": {}}
    with (output / "candidates.jsonl").open("w", encoding="utf-8") as destination:
        for name in ("EBOOT.elf", "LIBFONT.elf"):
            data = (ROOT / "private/modules" / name).read_bytes()
            rows = list(scan_elf(data))
            for row in rows:
                destination.write(json.dumps({"module": name, **row}, ensure_ascii=True)+"\n")
            count = struct.unpack_from("<H", data, 48)[0]
            report["modules"][name] = {"sha256": hashlib.sha256(data).hexdigest(), "candidates": len(rows),
                                      "section_count": count,
                                      "scan_status": "candidate-scan-complete" if count else "sectionless-not-scanned"}
    (output / "summary.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
