"""This script updates database entries for the existing reference files of a 
project without "delivering" them through the interactive web form or uploading files
to the server.   It assumes that basic FileBlob's are present in the database
for known files and updates them to include
"""
import sys
import traceback

import crds.server.config

from crds import (rmap, utils, log)
from crds.server.interactive import (views, models)
                
def hack_sqlite3_performance():
    """These pragmas make a huge difference on Fedora 15.  Mac OS-X seems to
    have good performance (perhaps these are already turned on) by default.
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('PRAGMA temp_store = MEMORY;')
    cursor.execute('PRAGMA synchronous=OFF')

def main(args):
    
    if "sqlite" in crds.server.config.dbtype:
        hack_sqlite3_performance()
    
    for blob in models.FileBlob.objects.all():
        try:
            log.info("Adding slow fields for: ", repr(blob.name))
            blob.thaw()
            blob.add_slow_fields()
            blob.sha1sum  # property computes and caches if not cached already.
        except Exception, exc:
            log.error("Failed", repr(blob.name), "with:", str(exc))
        else:
            blob.save()
    
    log.standard_status()

if __name__ == "__main__":
    import cProfile
    cProfile.runctx("main(sys.argv[1:])", globals(), globals(), "init_slow_fields.stats")

 
