#! /usr/bin/env python
"""This script makes symbolic links from all the files in HST's locate.locate_server_reference() 
directory dictionary to the CRDS standard location of the file as determined by
config.locate_reference().   locate_server_reference() knows about CDBS file paths.   The
point of this script is to make standard CRDS paths work on the server without copying all
of CDBS.
"""
import sys, os, shutil, re

from crds.core import config, log, rmap, utils
from crds.hst import locate

def main(used_references):
    if not used_references:
        pmap = rmap.get_cached_mapping("hst.pmap")
        used_references = set(pmap.reference_names())

    for filename in used_references:
        crds_path = config.locate_file(filename, observatory="hst")
        try:
            cdbs_path = locate.locate_server_reference(filename)
        except:
            log.warning("CDBS path",repr(cdbs_path),"does not exist.")
            continue
        copy_or_link(filename, cdbs_path, crds_path)
        if re.match(".*\.r[0-9]h$", filename): # also handle GEIS data
            copy_or_link(filename[:-1]+"d", cdbs_path[:-1]+"d", crds_path[:-1]+"d")

    log.standard_status()

def copy_or_link(filename, cdbs_path, crds_path):
        if os.path.exists(crds_path):
            log.info("Skipping existing", repr(filename))
            return
        try:
            utils.ensure_dir_exists(crds_path, mode=0o755)
            if "--copy" in sys.argv:
                log.info("Copying", repr(cdbs_path), "-->", repr(crds_path))
                shutil.copyfile(cdbs_path, crds_path)
            else:
                log.info("Linking", repr(cdbs_path), "-->", repr(crds_path))
                os.symlink(cdbs_path, crds_path)
        except Exception as exc:
            log.error("Error for",repr(crds_path),"-->",repr(cdbs_path),":",str(exc))

if __name__ == "__main__":
    files = sys.argv[1:]
    if "--copy" in files:
        files.remove("--copy")
    main(files)

