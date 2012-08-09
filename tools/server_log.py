"""This script dumps (--dump) or clears (--wipe) the CRDS server log
from the database.
"""

import sys

import crds.server.stats.models as smodels

def dump_log():
    for entry in smodels.LogModel.objects.all():
        print entry
        
def main():
    if "--dump" in sys.argv:
        dump_log()
    
    if "--wipe" in sys.argv:
        smodels.LogModel.wipe()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "usage: python server_log.py [--dump] [--wipe]"
    main()
