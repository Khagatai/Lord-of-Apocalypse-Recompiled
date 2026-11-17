"""Reject protected/generated/binary payloads in this title project's Git index."""
from pathlib import Path, PurePosixPath
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
GIT = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]

def main():
    config = tomllib.loads((ROOT / "config/lordofapocalypse.toml").read_text())
    pins = {"external/nakagawa-recomp": config["runtime"]["commit"],
            "external/psp-recomp": config["previous_runtime"]["commit"]}
    entries = subprocess.check_output(GIT + ["ls-files", "--stage", "-z"]).split(b"\0")
    count = 0
    links = set()
    for entry in filter(None, entries):
        metadata, raw_path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.decode().split()
        path = raw_path.decode("utf-8")
        if stage != "0":
            raise ValueError(f"Unmerged index entry: {path}")
        if mode == "160000":
            if pins.get(path) != oid:
                raise ValueError(f"Unexpected submodule identity: {path}")
            links.add(path)
            continue
        name = PurePosixPath(path)
        if name.parts[0] in {"private", "build", "out", "captures", "traces", "saves", "memstick", "cache"}:
            raise ValueError(f"Protected directory staged: {path}")
        if name.suffix.lower() not in {".py", ".md", ".txt", ".toml", ".json", ".ini", ".ps1", ".cpp", ".cs", ".c", ".h", ".manifest", ".mk"} and path not in {"LICENSE", ".gitignore", ".gitmodules", "Start-Game.cmd", "Start-Safe-Graphics.cmd"}:
            raise ValueError(f"Unexpected source file type: {path}")
        if "_recomp" in name.name.lower():
            raise ValueError(f"Generated game source staged: {path}")
        content = subprocess.check_output(GIT + ["show", f":{path}"])
        if b"\0" in content:
            raise ValueError(f"Binary content staged: {path}")
        content.decode("utf-8")
        count += 1
    if links != set(pins) or not count:
        raise ValueError("Incomplete source index or missing pinned submodules")
    print(f"PASS: {count} UTF-8 source files, {len(links)} pinned gitlinks; no protected/binary paths staged")

if __name__ == "__main__":
    main()
