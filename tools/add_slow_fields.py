"""This script initializes the slow fields of the database blobs for the
specified file basenames.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# from builtins import str
import sys
import traceback

import django

from crds_server import config as sconfig
from crds_server.interactive import (models, submit)

from crds.core import (rmap, log)
from crds.core.config import locate_file

def add_slow_fields(files):
    """Add the slow fields to the fileblobs for the basenames listed in `files`."""
    file_map = models.get_fileblob_map()
    for file in files:
        try:
            blob = file_map[file]
            blob.thaw()
            blob.add_slow_fields()
        except Exception as exc:
            log.info("Skipping non-existent file", repr(file), ":", str(exc))
            continue
                
def hack_sqlite3_performance():
    """These pragmas make a huge difference on Fedora 15.  Mac OS-X seems to
    have good performance (perhaps these are already turned on) by default.
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('PRAGMA temp_store = MEMORY;')
    cursor.execute('PRAGMA synchronous=OFF')

def main(files):   
    django.setup()
    if "sqlite" in sconfig.dbtype:
        hack_sqlite3_performance()
    add_slow_fields(files)
    log.standard_status()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("usage: add_slow_fields.py <files...>", file=sys.stderr)
    main(sys.argv[1:])
