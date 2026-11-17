"""Capture a bounded PPSSPP interpreter debugger sample into private storage.

This is raw debugger evidence, not a native-vs-oracle comparison or a pass.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]

class Debugger:
    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.buffer = bytearray()
        self.ticket = 0
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET /debugger HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                           "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                           "Sec-WebSocket-Protocol: debugger.ppsspp.org\r\n\r\n").encode())
        while b"\r\n\r\n" not in self.buffer:
            block = self.sock.recv(4096)
            if not block:
                raise EOFError("Debugger closed during websocket handshake")
            self.buffer.extend(block)
            if len(self.buffer) > 65536:
                raise ValueError("Oversized websocket handshake")
        header, self.buffer = bytes(self.buffer).split(b"\r\n\r\n", 1)
        self.buffer = bytearray(self.buffer)
        expected = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest())
        if not header.startswith(b"HTTP/1.1 101") or expected.lower() not in header.lower():
            raise ValueError("Websocket upgrade rejected")

    def read(self, count):
        while len(self.buffer) < count:
            block = self.sock.recv(max(4096, count - len(self.buffer)))
            if not block:
                raise EOFError("Debugger disconnected")
            self.buffer.extend(block)
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result

    def send_frame(self, payload, opcode=1):
        mask = os.urandom(4)
        size = len(payload)
        header = bytes([0x80 | opcode])
        if size < 126:
            header += bytes([0x80 | size])
        elif size < 65536:
            header += bytes([0xfe]) + struct.pack(">H", size)
        else:
            header += bytes([0xff]) + struct.pack(">Q", size)
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def receive(self):
        fragments = bytearray()
        while True:
            first, second = self.read(2)
            length = second & 0x7f
            if second & 0x80:
                raise ValueError("Unexpected masked server frame")
            if length == 126:
                length = struct.unpack(">H", self.read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self.read(8))[0]
            if length > 128 * 1024 * 1024:
                raise ValueError("Oversized debugger frame")
            payload = self.read(length)
            opcode = first & 15
            if opcode == 8:
                raise EOFError("Debugger closed websocket")
            if opcode == 9:
                self.send_frame(payload, 10)
                continue
            if opcode == 10:
                continue
            if opcode not in (0, 1):
                raise ValueError("Unexpected debugger frame opcode")
            fragments.extend(payload)
            if first & 0x80:
                return json.loads(fragments)

    def request(self, event, **parameters):
        self.ticket += 1
        self.send_frame(json.dumps({"event": event, "ticket": self.ticket, **parameters}).encode())
        while True:
            response = self.receive()
            if response.get("ticket") == self.ticket:
                if response["event"] == "error":
                    raise RuntimeError(response)
                return response

    def step(self):
        self.send_frame(b'{"event":"cpu.stepInto"}')
        while True:
            result = self.receive()
            if result["event"] == "error":
                raise RuntimeError(result)
            if result["event"] == "cpu.stepping":
                return result

    def memory(self, address, size):
        value = self.request("memory.read", address=address, size=size)
        result = base64.b64decode(value["base64"], validate=True)
        if len(result) != size:
            raise ValueError("Debugger memory size mismatch")
        return result

def registers(response):
    return {category["name"]: dict(zip(category["registerNames"], category["uintValues"]))
            for category in response["categories"]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--output", type=Path, default=ROOT / "private/oracle")
    parser.add_argument("--dump-main-image", action="store_true")
    parser.add_argument("--record-prefix-stores", action="store_true",
                        help="Capture observed scalar SW writes for the bounded integer entry prefix")
    args = parser.parse_args()
    if not 1 <= args.steps <= 256:
        parser.error("Use a bounded sample of 1..256 debugger steps")
    config = tomllib.loads((ROOT / "config/lordofapocalypse.toml").read_text())
    with args.image.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != config["disc"]["iso_sha256"]:
        raise ValueError("Input hash mismatch")
    source_root = ROOT / "private/tools/ppsspp"
    revision = subprocess.check_output(["git", "-c", f"safe.directory={source_root.as_posix()}",
                                        "-C", str(source_root), "rev-parse", "HEAD"], text=True).strip()
    if revision != config["tools"]["ppsspp"]["commit"]:
        raise ValueError("PPSSPP source revision mismatch")
    executable = source_root / "Windows/x64/Release/PPSSPPHeadless.exe"
    if not executable.is_file():
        raise FileNotFoundError("Build pinned PPSSPPHeadless first")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "private"):
        parser.error("Oracle output must stay under private/")
    output.mkdir(parents=True, exist_ok=True)
    memstick = output / "memstick"
    if memstick.exists():
        raise ValueError("Oracle memstick already exists; archive the prior run before repeating")
    memstick.mkdir()
    command = [str(executable), str(args.image.resolve()), "--cpu=interpreter", "--graphics=software",
               "--debugger=0", "--timeout-wall=60", "--log", "-d",
               f"--memstick={memstick}", f"--appendconfig={ROOT / 'config/oracle.ini'}"]
    log_path = output / "ppsspp.log"
    debugger = None
    try:
        with log_path.open("wb") as log:
            process = subprocess.Popen(command, cwd=source_root, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 30
                while True:
                    text = log_path.read_text(errors="replace")
                    match = re.search(r"Listening on port (\d+)", text)
                    if match:
                        break
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError(f"PPSSPP debugger unavailable; see {log_path}")
                    time.sleep(0.1)
                debugger = Debugger(int(match[1]))
                snapshot = {"command": command, "image_sha256": actual, "ppsspp_revision": revision,
                            "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                            "cpu": debugger.request("cpu.status"),
                            "registers": debugger.request("cpu.getAllRegs"),
                            "threads": debugger.request("hle.thread.list"),
                            "modules": debugger.request("hle.module.list"),
                            "objects": debugger.request("hle.object.list")}
                gpr = next(category for category in snapshot["registers"]["categories"] if category["id"] == 0)
                values = dict(zip(gpr["registerNames"], gpr["uintValues"]))
                if args.dump_main_image:
                    matches = [module for module in snapshot["modules"]["modules"]
                               if module["name"] == config["module"]["name"] and module["isActive"]]
                    if len(matches) != 1:
                        raise ValueError("Expected one active measured main module")
                    module = matches[0]
                    if module["address"] != config["module"]["base"]:
                        raise ValueError("Oracle module base changed")
                    image_size = config["module"]["image_size"]
                    image = debugger.memory(module["address"], image_size)
                    (output / "main-image.bin").write_bytes(image)
                    snapshot["main_image_sha256"] = hashlib.sha256(image).hexdigest()
                length, address = values["a0"], values["a1"]
                if 0 < length <= 4096:
                    snapshot["argument_hex"] = debugger.memory(address, length).hex()
                (output / "initial-state.json").write_text(json.dumps(snapshot, indent=2) + "\n")
                steps = []
                before = snapshot["registers"]
                for index in range(args.steps):
                    gpr = next(category for category in before["categories"] if category["id"] == 0)
                    values = dict(zip(gpr["registerNames"], gpr["uintValues"]))
                    pc = values["pc"]
                    opcode = int.from_bytes(debugger.memory(pc, 4), "little")
                    stopped = debugger.step()
                    after = debugger.request("cpu.getAllRegs")
                    writes = []
                    if args.record_prefix_stores and opcode >> 26 == 0x2b:
                        register_values = gpr["uintValues"]
                        immediate = opcode & 0xffff
                        if immediate & 0x8000:
                            immediate -= 0x10000
                        address = (register_values[(opcode >> 21) & 31] + immediate) & 0xffffffff
                        observed = int.from_bytes(debugger.memory(address, 4), "little")
                        writes.append({"address": address, "size": 4, "value": observed})
                    steps.append({"index": index, "pc": pc, "opcode": opcode,
                                  "before": before, "after": after, "stop": stopped,
                                  "observed_memory_writes": writes,
                                  "prefix_store_capture_enabled": args.record_prefix_stores})
                    before = after
                (output / "debugger-steps.json").write_text(json.dumps(steps, indent=2) + "\n")
                print(json.dumps({"status": "raw-oracle-evidence-only", "debugger_steps": len(steps),
                                  "modules": snapshot["modules"], "threads": snapshot["threads"],
                                  "initial_gpr": registers(snapshot["registers"])[gpr["name"]]}, indent=2))
            finally:
                if debugger:
                    debugger.sock.close()
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)
    finally:
        print(f"Oracle log: {log_path}")

if __name__ == "__main__":
    main()
