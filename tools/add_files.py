import os.path
import traceback

from crds import log
from crds.cmdline import Script

import crds.server.interactive.models as models

class AddFilesScript(Script):
    """Command line script for adding files to the CRDS database."""

    description = """
Add files to the CRDS database,  optionally intializing slow fields.
Does not move, rename, or deliver files.
    """
    
    epilog = """    
    * Add files in the current server cache to the CRDS database.
    
    % cd .../CRDS_server
    % source env.csh
    % python -m crds.list --mappings --references --full-paths >file_list
    % python tools/add_files.py @file_list
    """
    
    # ------------------------------------------------------------------------------------------
    
    def add_args(self):    
        self.add_argument('files', metavar='FILE', type=str, nargs='+',
                   help='List of files and/or @-files to add to CRDS database.')
        self.add_argument('-S', '--add-slow-fields', action='store_true', dest="add_slow_fields",
                          help='Initialize DB fields which require significant time,  like sha1sums.')
        self.add_argument('-T', '--state', default='submitted',  help="CRDS server file state.", 
                          choices=models.FILE_STATUS_MAP.keys()) 
        self.add_argument('-D', '--description', default="Initial mass database import")
        self.add_argument('-U', '--deliverer', default="crds")
        self.add_argument('-E', '--deliverer-email', default="support@stsci.edu")

    # ------------------------------------------------------------------------------------------
    
    def main(self):
        """Create FileBlobs and AuditBlobs for the list of `files`.  DB init only.
        This call is used to initialize files which are already positioned in their
        final locations,  suitable for recreating the CRDS database from a CRDS file
        cache.
        """
        
        paths = self.get_files(self.args.files)
        file_map = models.get_fileblob_map()
        
        for path in paths:
            
            file = os.path.basename(path)
            if file in file_map:
                log.info("Skipping existing file", repr(file))
                continue
    
            log.info("Submitting", repr(file), "from", repr(file))
            try:
                blob = models.add_crds_file(
                    observatory=self.observatory, 
                    upload_name=file, 
                    permanent_location=path, 
                    deliverer=self.args.deliverer, 
                    deliverer_email=self.args.deliverer_email, 
                    description=self.args.description,
                    add_slow_fields=self.args.add_slow_fields,
                    state=self.args.state, update_derivation=False)
                details = ""
            except Exception, exc:
                log.error("Submission FAILED for", repr(file), ":", str(exc))
                traceback.print_exc()
                details = "add_files FAILED: " + repr(str(exc))
            models.AuditBlob.new(self.args.deliverer, "mass import", self.args.description, file, 
                details, observatory=self.observatory, instrument=blob.instrument, filekind=blob.filekind)
  
if __name__ == "__main__":
    AddFilesScript()()

