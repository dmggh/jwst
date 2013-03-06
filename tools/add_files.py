import os.path
import traceback

from crds import log, rmap
from crds.cmdline import Script

import crds.server.config
import crds.server.interactive.models as models

def hack_sqlite3_performance():
    """These pragmas make a huge difference on Fedora 15.  Mac OS-X seems to
    have good performance (perhaps these are already turned on) by default.
    """
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute('PRAGMA temp_store = MEMORY;')
    cursor.execute('PRAGMA synchronous=OFF')

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
        if "sqlite" in crds.server.config.dbtype:
            hack_sqlite3_performance()
        paths = self.get_files(self.args.files)
        self.add_files(paths)
        self.set_default_contexts()
        
    def add_files(self, paths):
        """Add the files specified in list `paths` to the CRDS database."""
        file_map = models.get_fileblob_map()
        for path in paths:
            
            file = os.path.basename(path)
            if file in file_map:
                if self.args.add_slow_fields:
                    with log.error_on_exception("Failed adding slow fields for", repr(file)):
                        file_map[file].add_slow_fields()
                log.info("Skipping existing file", repr(file))
                continue
    
            log.info("Adding", repr(file), "from", repr(path))
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
                models.mirror_filename_counters(self.observatory, path)
                details = ""
            except Exception, exc:
                log.error("Add FAILED for", repr(path), ":", str(exc))
                traceback.print_exc()
                details = "add_files FAILED for %s: " %  path + repr(str(exc))
            models.AuditBlob.new(user=self.args.deliverer, action="mass import", affected_file=file, why=self.args.description, 
                details=details, observatory=self.observatory, instrument=blob.instrument, filekind=blob.filekind)
            
    
    def set_default_contexts(self, context=None):
        """Set the default contexts in the CRDS database."""
        if context is None:
            context = self.choose_default_context()
        log.info("Setting default context to", repr(context))
        models.set_default_context(context)    
        models.set_default_context(context, state="operational")
    
    def choose_default_context(self):
        contexts = sorted(rmap.list_mappings("*.pmap", observatory=self.observatory))
        return contexts[-1]
 
if __name__ == "__main__":
    AddFilesScript()()

