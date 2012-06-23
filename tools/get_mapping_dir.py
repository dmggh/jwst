"""Baseline mappings are installed as a CRDS package.  Print out where.
"""

import sys
import os.path

import crds.utils as utils

def get_mapping_dir(observatory):
    module = utils.get_object("crds.mappings."+observatory)
    dir = os.path.dirname(module.__file__)
    return dir

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print >>sys.stderr, "usage: " + sys.argv[0] + " [hst|jwst]"
    print get_mapping_dir(sys.argv[1])
