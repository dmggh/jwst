"""This script handles basic database initialization and file delivery for
filepaths listed on the command line.   It is distinct from file submission
because it has no support for file generation, file certification, or user
coordination via locking.   It's a primitive script intended to reinitialize
a CRDS database,  including fileblobs, filename counters, audit trail, and 
deliveries from files already assumed good and in the CRDS cache.

File delivery is included because that's a normal part of bootstrapping CRDS
from generated files.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# from builtins import str

import os.path
import traceback

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crds_server.settings")
django.setup()

from crds import log, rmap, pysh
from crds.cmdline import Script

from crds_server import config as sconfig
from crds_server.interactive import models, submit

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
        self.add_argument('--reinit-slow-fields', action='store_true', dest="reinit_slow_fields",
                          help='Initialize DB fields which require significant time,  like sha1sums.')
        self.add_argument('-T', '--state', default='operational',  help="CRDS server file state.", 
                          choices=list(models.FILE_STATUS_MAP.keys())) 
        self.add_argument('-D', '--description', default="Initial mass file import")
        self.add_argument('-U', '--deliverer', default="crds",  help="Username of person adding these files.")
        self.add_argument('-E', '--deliverer-email', default="support@stsci.edu")
        self.add_argument('--deliver', action='store_true',
                          help="Generate file delivery lists and links for OPUS pickup of the added files.")
        self.add_argument('-P', '--replace', action='store_true',
                          help="Destroy and re-create existing FileBlobs for added files.")
        self.add_argument('-A', '--allow-duplicates', action='store_true',
                          help="Don't abort file submission when sha1sum indicates a duplicate file.")
        self.add_argument('-C', '--copy-to-cache', action='store_true',
                          help="Copy the listed file to the CRDS cache prior to adding.")
        self.add_argument('-X', '--set-contexts', action='store_true',
                          help="Set the operational and edit contexts.")
        self.add_argument("-O", '--submission-action', default="add_files tool", choices=models.AUDITED_ACTIONS,
                          help="Kind of submission you want this to look like,  mass imports don't show up as recent activity.")

    # ------------------------------------------------------------------------------------------
    
    def main(self):
        """Create FileBlobs and AuditBlobs for the list of `files`.  DB init only.
        This call is used to initialize files which are already positioned in their
        final locations,  suitable for recreating the CRDS database from a CRDS file
        cache.
        """
        django.setup()

        if "sqlite" in sconfig.dbtype:
            hack_sqlite3_performance()
        if self.args.deliver:
            self.args.state = "delivered"
        added = self.add_files(self.files)
        if self.args.deliver and added:
            self.deliver_files(added)
        if self.args.set_contexts:
            self.set_default_contexts()
        log.standard_status()

    def add_files(self, paths):
        """Add the files specified in list `paths` to the CRDS database.
        Return list of files added, omitting any already in the db.
        """
        file_map = models.get_fileblob_map()
        added = []
        for path in paths:

            if self.args.copy_to_cache:
                cache_location = rmap.locate_file(os.path.basename(path), self.observatory)
                if os.path.exists(cache_location) and not self.args.replace:
                    log.warning("Skipping existing file", repr(path))
                else:
                    log.info("Installing", path, "in CRDS cache.")
                    pysh.sh("cp ${path} ${cache_location}", 
                            trace_commands=True, trace_exceptions=True, raise_on_error=True)
            
            file = os.path.basename(path)
            if file in file_map:
                if self.args.replace:
                    log.info("Replacing", repr(file))
                    file_map[file].delete()
                    del file_map[file]
                else:
                    log.info("Skipping existing file", repr(file))
                    if self.args.reinit_slow_fields:
                        with log.error_on_exception("Failed adding slow fields for", repr(file)):
                            file_map[file].add_slow_fields(allow_duplicates=self.args.allow_duplicates)
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
                    allow_duplicates=self.args.allow_duplicates,
                    state=self.args.state, update_derivation=False)
                models.mirror_filename_counters(self.observatory, path)
                added.append(path)
                file_map[file] = blob
            except Exception as exc:
                log.error("Add FAILED for", repr(path), ":", str(exc))
                traceback.print_exc()
                continue
        return added

    def deliver_files(self, paths):
        """Generate a delivery .cat and links so that OPUS can pick files in `paths`."""
        files = [os.path.basename(file) for file in paths]
        log.info("Delivering:", paths)
        d = submit.Delivery(user=self.args.deliverer, delivered_files=files, 
                            description=self.args.description, action=self.args.submission_action, observatory=self.observatory)
        with log.error_on_exception("File delivery failed."):
            d.deliver()
    
    def set_default_contexts(self, context=None):
        """Set the default contexts in the CRDS database."""
        if context is None:
            context = self.choose_default_context()
        log.info("Setting default context to", repr(context))
        models.set_default_context(context, description=self.args.description)
        models.set_default_context(context, state="operational", description=self.args.description)
    
    def choose_default_context(self):
        contexts = sorted(rmap.list_mappings("*.pmap", observatory=self.observatory))
        return contexts[-1]
 
if __name__ == "__main__":
    AddFilesScript()()

