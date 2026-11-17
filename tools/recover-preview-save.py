"""Copy a prior preview memstick into persistent storage, preserving a verified backup."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import save_storage

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--language", choices=("japanese", "english-v16"), default="japanese")
    args = parser.parse_args()
    print(json.dumps(save_storage.recover(ROOT, args.source, args.language), indent=2))

if __name__ == "__main__":
    main()
