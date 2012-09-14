"""This script creates database entries for the existing reference files of HST
without "delivering" them through the interactive web form or uploading files
to the server.   This script is intended to be run on the CRDS server to
initialize the CRDS database.   The script assumes that the mappings are already
in an operational form and can be loaded and utilized to help define references
and nested mappings;  this means the mappings must already be located in their
operational directories.
"""
import sys
import traceback

import crds.server.config
import crds.server.interactive.models

from crds import (rmap, utils, log)
from crds.server.interactive import (views, models)

def locate_file(fname, observatory):
    if observatory == "hst":
        if rmap.is_mapping(fname):
            return rmap.locate_file(fname, observatory)
        else:
            import crds.hst.locate
            return crds.hst.locate.locate_server_reference(fname)
    else:
        return rmap.locate_file(fname, observatory)

def submit_files(files, observatory, deliverer, 
    deliverer_email="support@stsci.edu", 
    description="Initial mass database import", 
    add_slow_fields=False, state="submitted"):
    
    for file in files:
        
        if models.file_exists(file):
            log.info("Skipping existing file", repr(file))
            continue

        try:
            existing_location = locate_file(file, observatory)
        except Exception:
            log.warning("Can't locate", repr(file), "submitting as", repr(file))
            existing_location = file

        log.info("Submitting", repr(file), "from", repr(existing_location))
        try:
            blob = models.add_crds_file(
                observatory=observatory, 
                upload_name=file, 
                permanent_location=existing_location, 
                deliverer=deliverer, 
                deliverer_email=deliverer_email, 
                description=description,
                add_slow_fields=add_slow_fields,
                state=state, update_derivation=False)
        except Exception, exc:
            log.error("Submission FAILED for", repr(file), ":", str(exc))
            traceback.print_exc()
        else:
            models.AuditBlob.new(deliverer, "mass import", file, 
                "system initialization", "", observatory=observatory, 
                instrument=blob.instrument, filekind=blob.filekind, date=None)
                
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
    
    ctx = rmap.get_cached_mapping(args[0])

    # Initial set of mappings must be delivered to the archive.
    submit_files(ctx.mapping_names(), ctx.observatory, 
                 deliverer=args[1], deliverer_email=args[2], 
                 description=args[3], add_slow_fields=int(args[4]), 
                 state="submitted")

    models.set_default_context(args[0])    
    models.set_default_context(args[0], state="operational")
    
    try:
        views.deliver_file_list(args[1], ctx.observatory, ctx.mapping_names(), 
                                "system initialization", "mass import")
    except Exception, exc:
        log.warning("File deliveries for", args[1], "failed:", str(exc))
        
    # Initial set of reference files assumed to be already operational.
    submit_files(ctx.reference_names(), ctx.observatory, 
                 deliverer=args[1], deliverer_email=args[2], 
                 description=args[3], add_slow_fields=int(args[4]), 
                 state="operational")
    
    log.standard_status()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print >>sys.stderr, "usage: import_files.py <context> <deliverer> <email> <modifier> <description> <add_slow_fields>"
    else:
        import cProfile
        cProfile.runctx("main(sys.argv[1:])", globals(), globals(), "init.stats")

 
