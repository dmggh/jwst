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

"""
def create_delivery_blob(observatory, upload_name, permanent_location, 
    deliverer_user, deliverer_email, modifier_name, description):
"""

def submit_mappings(context, 
                    deliverer_user,
                    deliverer_email="support@stsci.edu", 
                    modifier_name="Unknown", 
                    description="Initial mass database import",
                    add_slow_fields=False):
    ctx = rmap.get_cached_mapping(context)
    for mapping in ctx.mapping_names():
        existing_location = rmap.locate_file(
            ctx.observatory, mapping, mode="server")
        if models.MappingBlob.exists(mapping):
            log.info("Skipping existing mapping", repr(mapping))
        else:
            log.info("Submitting", repr(mapping), "from", repr(existing_location))
            blob = models.add_crds_file(
                observatory=ctx.observatory, 
                upload_name=mapping, 
                permanent_location=existing_location, 
                deliverer_user=deliverer_user, 
                deliverer_email=deliverer_email, 
                modifier_name=modifier_name, 
                description=description,
                creation_method="mass import",
                add_slow_fields=add_slow_fields)

def submit_references(context, 
                    deliverer_user,
                    deliverer_email="support@stsci.edu", 
                    modifier_name="Unknown", 
                    description="Initial mass database import",
                    add_slow_fields=False):
    ctx = rmap.get_cached_mapping(context)
    for reference in ctx.reference_names():
        try:
            existing_location = rmap.locate_file(
                    ctx.observatory, reference, mode="server")
        except Exception:
            log.error("Can't locate", repr(reference))
            existing_location = "unknown_location_for_" + reference
        if models.ReferenceBlob.exists(reference):
            log.info("Skipping existing reference", repr(reference))
        else:
            log.info("Submitting", repr(reference), "from", repr(existing_location))
            try:
                blob = models.add_crds_file(
                    observatory=ctx.observatory, 
                    upload_name=reference, 
                    permanent_location=existing_location, 
                    deliverer_user=deliverer_user, 
                    deliverer_email=deliverer_email, 
                    modifier_name=modifier_name, 
                    description=description,
                    creation_method="mass import",
                    add_slow_fields=add_slow_fields)
            except Exception:
                log.error("Submission FAILED for", repr(reference))
    
def main(args):
    submit_mappings(args[0], deliverer_user=args[1], deliverer_email=args[2],
                    modifier_name=args[3], description=args[4], add_slow_fields=int(args[5]))
    submit_references(args[0], deliverer_user=args[1], deliverer_email=args[2],
                    modifier_name=args[3], description=args[4],add_slow_fields=int(args[5]))
    log.standard_status()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print >>sys.stderr, "usage: import_files.py <context> <deliverer> <email> <modifier> <description> <add_slow_fields>"
    else:
        import cProfile
        cProfile.runctx("main(sys.argv[1:])", globals(), globals())

 
