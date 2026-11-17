"""Compatibility entry point for the active identity-pinned title generator."""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    sys.argv = ["title.py", "generate", *sys.argv[1:]]
    runpy.run_path(str(Path(__file__).with_name("title.py")), run_name="__main__")
