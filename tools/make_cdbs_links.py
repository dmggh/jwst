#! /usr/bin/env python
"""This script makes symbolic links from all the files in HST's locate.locate_server_reference() 
directory dictionary to the CRDS standard location of the file as determined by
config.locate_reference().   locate_server_reference() knows about CDBS file paths.   The
point of this script is to make standard CRDS paths work on the server without copying all
of CDBS.
"""
import os

from crds import config, log, rmap
import crds.hst.locate as locate

def main():
    pmap = rmap.get_cached_mapping("hst.pmap")
    used_references = set(pmap.reference_names())
    for filename in used_references:
        crds_path = config.locate_file(filename, observatory="hst")
        try:
            cdbs_path = locate.locate_server_reference(filename)
        except:
            log.warning("CDBS path",repr(cdbs_path),"does not exist.")
            continue
        if os.path.exists(crds_path):
            log.info("Skipping existing link for", repr(filename))
            continue
        try:
            os.symlink(cdbs_path, crds_path)
            log.info("Linking", repr(crds_path), "-->", repr(cdbs_path))
        except Exception, exc:
            log.error("Error linking",repr(crds_path),"-->",repr(cdbs_path),":",str(exc))
    log.standard_status()

if __name__ == "__main__":
    main()

