"""Build a private, hash-verified multi-atlas UI sample pack."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from ui_pack import merge


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples',nargs='+',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(merge(args.samples,args.output),indent=2))


if __name__=='__main__':
    main()
