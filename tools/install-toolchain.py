"""Install upstream hash-pinned compiler dependencies under private/, without game inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def verify_framework(root=ROOT):
    """Check public build sources before downloads; no decrypted game inputs needed."""
    root = Path(root).resolve()
    config = __import__('tomllib').loads((root / 'config/lordofapocalypse.toml').read_text())
    framework = (root / config['runtime']['path']).resolve()
    if not framework.is_relative_to(root):
        raise ValueError('Framework path escapes the project')
    if not (framework / '.git').exists():
        import source_identity
        revision = source_identity.verify(root, 'framework')
    else:
        revision = subprocess.check_output(
            ['git', '-c', f'safe.directory={framework.as_posix()}',
             '-C', str(framework), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != config['runtime']['commit']:
        raise ValueError('Framework dependency pins changed')
    return framework, revision

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirror", choices=("primary", "accum"), default="primary")
    args = parser.parse_args()
    if sys.version_info < (3, 14):
        parser.error("Use supported Python 3.14+ for zstd package extraction")
    framework, revision = verify_framework()
    data = (framework / "assets/prereq_manifest.json").read_bytes()
    manifest = json.loads(data)
    # Python is supplied separately from python.org; preserve every compiler,
    # SDL and Vulkan artifact's upstream size/hash exactly.
    manifest["artifacts"] = [x for x in manifest["artifacts"] if x["id"] != "cpython-embed-amd64"]
    manifest["total_download_bytes"] = sum(x["size_bytes"] for x in manifest["artifacts"])
    if args.mirror == "accum":
        for item in manifest["artifacts"]:
            if item["url"].startswith("https://repo.msys2.org/"):
                item["url"] = item["url"].replace("https://repo.msys2.org/", "https://mirror.accum.se/mirror/msys2.org/")
                item["allowed_hosts"] = ["mirror.accum.se", "saimei.ftp.acc.umu.se", "laotzu.ftp.acc.umu.se"]
    private = ROOT / "private"
    private.mkdir(exist_ok=True)
    path = private / "toolchain-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    (private / "toolchain-manifest-origin.json").write_text(json.dumps({
        "framework_commit": revision, "upstream_manifest_sha256": hashlib.sha256(data).hexdigest(),
        "mirror": args.mirror, "compiler_artifact_pins_modified": False}, indent=2) + "\n")
    subprocess.run([sys.executable, str(framework / "tools/nk_core/prereq_fetcher.py"),
                    "--manifest", str(path), "--data-root", str(private / "toolchain")], check=True)

if __name__ == "__main__":
    main()
