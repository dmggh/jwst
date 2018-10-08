"""Baseline mappings are installed as a CRDS package.  Print out where."""
import sys
import os.path

import crds
from crds import utils

def get_mapping_dir(observatory):
    dir = os.path.dirname(crds.__file__)
    dir = os.path.join(dir, "cache", "mappings", observatory)
    return dir

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: " + sys.argv[0] + " [hst|jwst]", file=sys.stderr)
        sys.exit(-1)
    print(get_mapping_dir(sys.argv[1]))
