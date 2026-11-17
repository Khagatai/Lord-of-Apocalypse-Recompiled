"""Build and run a synthetic camera mapping check against pinned native input code."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import title

def main():
    title.verify_inputs()
    output = ROOT / "private/tests"
    output.mkdir(parents=True, exist_ok=True)
    core = title.FRAMEWORK / "src/core"
    exe = output / "camera-profile.exe"
    command = [str(title.SDK / "bin/gcc.exe"), "-O2", "-ffunction-sections", "-fdata-sections",
               "-I" + str(core), str(ROOT / "tests/test_camera_profile.c"),
               str(core / "nk_input_profile.c"), str(core / "nk_json.c"), str(core / "nk_shared_helpers.c"),
               str(core / "nk_platform_win32.c"), "-lshell32", "-lole32", "-luuid", "-luser32", "-ladvapi32", "-lshlwapi",
               "-Wl,--gc-sections", "-o", str(exe)]
    subprocess.run(command, env=title.environment(), check=True)
    subprocess.run([str(exe), str(ROOT / "config/controller-camera.json")], env=title.environment(), check=True)

if __name__ == "__main__":
    main()
