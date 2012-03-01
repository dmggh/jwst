"""This script creates database entries for the existing reference files of HST
without "delivering" them through the interactive web form or uploading files
to the server.   This script is intended to be run on the CRDS server to
initialize the CRDS database.   The script assumes that the mappings are already
in an operational form and can be loaded and utilized to help define references
and nested mappings;  this means the mappings must already be located in their
operational directories.
"""
import sys

import crds.server.config
import crds.server.interactive.models

from crds import (rmap, utils, log)
from crds.server.interactive import (views, models)
import crds.hst.locate as hst_locate

def locate_file(fname):
    if rmap.is_mapping(fname):
        return rmap.locate_file(fname, "hst")
    else:
        return hst_locate.locate_server_reference(fname)

def submit_files(files, observatory, deliverer, 
    deliverer_email="support@stsci.edu", 
    description="Initial mass database import", 
    add_slow_fields=False, state="submitted"):
    
    for file in files:
        
        if models.file_exists(file):
            log.info("Skipping existing file", repr(file))
            continue

        try:
            existing_location = locate_file(file)
        except Exception:
            log.error("Can't locate", repr(file))
            continue

        log.info("Submitting", repr(file), "from", repr(existing_location))
        try:
            blob = models.add_crds_file(
                observatory=observatory, 
                upload_name=file, 
                permanent_location=existing_location, 
                deliverer=deliverer, 
                deliverer_email=deliverer_email, 
                description=description,
                creation_method="mass import",
                add_slow_fields=add_slow_fields,
                state=state)
        except Exception:
            log.error("Submission FAILED for", repr(file))
                
def hack_sqlite3_performance():
    """These pragmas make a huge difference on Fedora 15.  Mac OS-X seems to
    have good performance (perhaps these are already turned on) by default.
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('PRAGMA temp_store = MEMORY;')
    cursor.execute('PRAGMA synchronous=OFF')

def main(args):
    
    hack_sqlite3_performance()
    
    ctx = rmap.get_cached_mapping(args[0])

    submit_files(ctx.mapping_names(), ctx.observatory, 
                 deliverer=args[1], deliverer_email=args[2], 
                 description=args[3], add_slow_fields=int(args[4]), 
                 state="submitted")
    
    submit_files(ctx.reference_names(), ctx.observatory, 
                 deliverer=args[1], deliverer_email=args[2], 
                 description=args[3], add_slow_fields=int(args[4]), 
                 state="operational")
    
    models.set_default_context(args[0])
    
    log.standard_status()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print >>sys.stderr, "usage: import_files.py <context> <deliverer> <email> <modifier> <description> <add_slow_fields>"
    else:
        import cProfile
        cProfile.runctx("main(sys.argv[1:])", globals(), globals())

 
