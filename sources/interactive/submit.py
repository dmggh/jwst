"""This module defines the functions used to submit references and mappings to CRDS.  

Functions performed:

0. Authentication and multiple login prevention?
* Verify username and password against CRDS database.

1. Input sanity checking and security screening.
* Ensure no submitted file is a copy of an existing file.
* Ensure inputs aren't trojaned.

2. File certification, dependency existence and blacklist checking.
* Optional file comparisons to prior references.

3. Optional file renaming to official CRDS names.
* If not renamed,  ensure not existing.

4. Optional generation of supporting mappings, including limited updates to multiple rmaps.
* Warn if any submitted or generated file, other than the .pmap,  is not mentioned 
  in a difference as an addition or replacement.

5. Entry into the CRDS database,  audit trail.

6. Presentation of preliminary persistent results, including an emphatic summary 
of errors and/or warnings.
* possibly present results as text or HTML by virtue of template expanded.

7. Delivery confirmation or rejection.  audit trail,  accept/reject reason?
* accept comments about what were fatal problems or why warnings were ignored.

8. Final acceptance processing.   (potentially long running)
* Data transfer from ingest to storage directories.  Ownership transfer.
* Sha1sum generation for future verification of file integrity.
* File delivery for archive pickup.

9. Final rejection processing
* Possible recovery of official CRDS file serial numbers.
* Removal or sealing of database traces.

10. Removal of delivered files from ingest area.
11. Presentation of final result,  including an emphatic summary of errors and/or warnings.
"""
import os
import tempfile
import shutil
import glob

from crds import log, rmap, utils, refactor, newcontext, CrdsError, config, naming

from . import models, web_certify, web_difference, locks
from .common import srepr

from crds.server import config as sconfig

from django.contrib.auth.models import User

# ----------------------------------------------------------------------------------------------------

def file_exists_somehow(filename):
    """Return True IFF `filepath` really exists or CRDS thinks it does."""
    try:
        filepath = rmap.locate_file(filename, sconfig.observatory)
    except IOError:
        raise CrdsError("Cannot locate file", srepr(filename), 
                        "in cache.  Must identify instrument in name.   Consider Auto-Rename.")
    return os.path.exists(filepath) or \
        models.FileBlob.exists(os.path.basename(filepath))

# ----------------------------------------------------------------------------------------------------

'''
from crds import cmdline

class SubmitFilesScript(cmdline.Script):
    """Command line version of CRDS file submissions."""
    
    description = """Submit files to CRDS relative to the specified context.
    
    There are two broad scenarios which have several use cases.
    
    I.  Submit primitive files.   
    
        Other than basic certification,  CRDS will accept the files as is.
        CRDS does not attempt to interrelate these files.  The given context is
        used to locate existing files which correspond to the submitted files
        for differencing and certification,  particularly for references.
    
        a. Submit references, of any known instruments or types.

        b. Submit .rmap's, .imap's, or .pmap's,  in any relation
    
    II. Submit files and generate mappings.
    
        CRDS accepts related primitive files, but then automatically generates
        related higher level mapping files.
        
        a. Submit references for one instrument but possibly several types,  
                and generate .rmap's, .imap, and .pmap.
                
        b. Submit .rmap's,  generate .imap's and .pmap's. 
    """
    
    def add_args(self):
        self.add_argument("files", nargs="+", help="Paths of references and mappings to add to CRDS.""")
        self.add_argument("--derive-from-context", store_in="derive_from_context",
                          help=".pmap used for certification or basis for new mappings/.pmap")
        self.add_argument("--change-level", choices=["trivial", "medium", "severe"], store_in="change_level", 
                          default="severe", help="Degree to which submitted files impact science results.")
        self.add_argument("--description", help="Free text description of file submission.")
        self.add_argument("--auto-rename", action="store_true", default=True,
                          help="If specified,  automatically rename files to CRDS-style versioned names.")
        self.add_argument("--compare-old-references", action="store_true", default=False,
                          help="Check references against replaced files in derive-from-context, where applicable.")
        self.add_argument("--generate-rules", action="store_true", default=False,
                          help="Generate mappings as required to add the submitted files to the derived-from-context.")
        self.add_argument("--creator", default="(unknown)",
                          help="Name of the person who originally authored the file.")
        
    def main(self):
        submit_files(self.args.derive_from_context, self.args.files)
        
    def batch_submission(self):
        self.user = None
        self.bsr = BatchReferenceSubmission(args.derive_from_context, args.files, args.description, 
                        user=self.user, creator=self.args.creator, change_level=self.args.change_level, 
                        auto_rename=self.args.auto_rename, compare_old_reference=self.args.compare_old_reference)
        self.bsr.submit()
        
    def confirm_or_cancel(self):
        pass

def submit_files(_context, _files):
    "placeholder"
    raise NotImplementedError("command line interface not finished yet.")
'''

# ------------------------------------------------------------------------------------------------

class FileSubmission(object):
    """Baseclass for file submissions,  carrier object for submission metadata and files."""
    
    def __init__(self, pmap_name, uploaded_files, description, user, creator="UNKNOWN",
                 change_level="SEVERE", auto_rename=True, compare_old_reference=False,
                 locked_instrument=None, status_channel=None, pmap_mode=None):
        self.pmap_name = pmap_name
        self.pmap_mode = pmap_mode
        self.final_pmap = None   # pmap_mode/pmap_name evaluated at confirmation time.
        try:
            self.observatory = self.pmap.observatory
        except:
            self.observatory = models.OBSERVATORY
        self.uploaded_files = uploaded_files
        self.description = description
        self.user_name = str(user) if isinstance(user, User) else user
        self.user = User.objects.get(username=self.user_name)
        self._user = None
        self.creator = creator
        self.change_level = change_level
        self.auto_rename = auto_rename
        self.compare_old_reference = compare_old_reference
        self.locked_instrument = locked_instrument
        self.status_channel = status_channel
        self.added_files = []
        
    @property
    def pmap(self):
        return rmap.get_cached_mapping(self.pmap_name)
        
    @property
    def upload_names(self):
        return self.uploaded_files.keys()

    @property
    def obs_locate(self):
        return utils.get_locator_module(self.observatory)

    def __repr__(self):
        fields = [a + "=" + repr(getattr(self, a)) for a in ["pmap_name", "user_name", "upload_names", "description"]]
        return self.__class__.__name__ + "(" + ", ".join(fields) + ")"

    def submit(self, *args, **keys):
        """Validate the submitted files and add them to the database."""
        try:
            result = self._submit(*args, **keys)
            # raise RuntimeError("Unforseen event!!!")
            return result
        except Exception as exc:
            self.cleanup_failed_submission()
            raise
        
    def _submit(self, *args, **keys):
        """FileSubmission is abstract,  _submit must be overridden."""
        raise NotImplementedError("abstract class")
        
    def cleanup_failed_submission(self):
        """Cleanup loose ends from a failed file submission,  particularly those files which have been
        added already when something fails.
        """
        log.info("Cleanup failed submission", repr(self))
        with log.error_on_exception("cleanup_failed_submission() failed removing added files"):
            for uploaded_name, _path in self.added_files:
                blobs = models.FileBlob.filter(uploaded_as=uploaded_name, include_uploaded=True)
                for blob in blobs:      
                    with log.error_on_exception("File cleanup for '%s' failed." % uploaded_name):
                        if blob.state == "uploaded":
                            blob.destroy()
                        else:
                            log.info("Skipping blob", blob.moniker, "with state", blob.state)

    def ensure_unique_uploaded_names(self):
        """Make sure there are no duplicate names in the submitted file list."""
        # This is a sensible check for files originating on the command line.
        uploaded_as, paths = zip(*self.uploaded_files)
        pathmap = dict(*zip(paths, uploaded_as))
        for name in uploaded_as:
            assert uploaded_as.count(name) == 1, "File '%s' appears more than once." % name
        for path in paths:
            assert paths.count(path) == 1, "File path for '%s' appears more than once." %  pathmap[path]

    def push_status(self, message):
        """Push status messages to the user's client,  nominally a browser which
        picks up the messages from Django via AJAX polling in the jpoll app.
        """
        if self.status_channel is not None:
            log.info("push_status: " + repr(message))
            self.status_channel.write(message)
            self.status_channel.flush()
            
    def ordered_files(self):
        """Organize uploaded file tuples in dependency order,  starting with references and ending with .pmaps."""
        rmaps, imaps, pmaps, other = [], [], [], []
        for original_name, uploaded_path in self.uploaded_files.items():
            if original_name.endswith(".rmap"):
                rmaps.append((original_name, uploaded_path))
            elif original_name.endswith(".imap"):
                imaps.append((original_name, uploaded_path))
            elif original_name.endswith(".pmap"):
                pmaps.append((original_name, uploaded_path))
            else:
                other.append((original_name, uploaded_path))
        return sorted(other) + sorted(rmaps) + sorted(imaps) + sorted(pmaps)

    def submit_file_list(self, creation_method):
        """Ingest a list of `uploaded_files` tuples into CRDS."""
        return { original_name: self.do_submit_file(original_name, uploaded_path, creation_method=creation_method)
                for (original_name, uploaded_path) in self.ordered_files() }

    def do_submit_file(self, original_name, upload_location, creation_method):
        """Do the core processing of a file submission,  including file certification 
        and blacklist checking, naming, upload, and record keeping.
        """
        self.push_status("Processing '{}'".format(original_name))
        # Automatically 
        if self.auto_rename:
            permanent_name = self.auto_rename_file(original_name, upload_location)
        else:
            try:
                if file_exists_somehow(original_name):
                    raise CrdsError("File named " + srepr(original_name) + " already exists.") 
                else:
                    permanent_name = os.path.basename(original_name)   
            except IOError:
                raise CrdsError("File", srepr(original_name), 
                                "cannot be located in cache. Name must identify instrument.")
    
        # CRDS keeps all new files in a standard layout.  Existing files in /grp/cdbs
        # are currently referenced by standard symlinks in the CRDS server file tree.
        permanent_location = rmap.locate_file(permanent_name, self.observatory)
    
        # Make sure none of the dependencies are blacklisted,  else fail w/o state.
        blacklisted_by = web_certify.get_blacklists(original_name, upload_location)
        if blacklisted_by:
            raise CrdsError("File " + srepr(original_name) + " is blacklisted by " + srepr(blacklisted_by))
        
        utils.ensure_dir_exists(permanent_location)
        # Move or copy the temporary file to its permanent location,  assert ownership of CRDS copy now
        owner = os.stat(upload_location).st_uid
        if owner == os.getuid() and not rmap.is_mapping(permanent_location):
            log.info("Linking", upload_location, "-->", permanent_location)
            os.link(upload_location, permanent_location)
        else:
            log.info("Copying", upload_location, "-->", permanent_location)
            self.push_status("Copying '{}'".format(original_name))
            shutil.copyfile(upload_location, permanent_location)
        
#        data_file.setval("COMMENT", "Header parameters of this file only reflect the original CRDS assignment rules.")
#        data_file.setval("COMMENT", "The CRDS rules,  which can change independently, define how this file is assigned now.")
    
        # Make a database record for this file.
        self.add_crds_file(original_name, permanent_location)
        
        return os.path.basename(permanent_location)

    def do_create_contexts(self, updated_rmaps):
        """Create new contexts based on `pmap_name` which refer to `updated_rmaps`
        instead of the corresponding old rmaps.  Add the new contexts to the
        CRDS database and return a list of new context mapping names.
        """
        self.push_status("Creating contexts '{}' for '{}'.".format(repr(updated_rmaps), str(self.user)))
        context_lock = locks.acquire(user=str(self.user), type="context", name="all")
        try:
            return self.do_create_contexts_unlocked(updated_rmaps)
        finally:
            context_lock.release()

    def do_create_contexts_unlocked(self, updated_rmaps):
        """Create new contexts from `updated_rmaps` with no concern for locking."""
        
        # Evaluate implicit pmap names *now*,  while locked!
        if self.pmap_mode == "pmap_edit":
            self.final_pmap = models.get_default_context(models.OBSERVATORY, state="edit")
        elif self.pmap_mode == "pmap_operational":
            self.final_pmap = models.get_default_context(models.OBSERVATORY, state="operational")
        else:
            self.final_pmap = self.pmap_name
        
        log.info("Resolved final derivation pmap from pmap_mode = ", repr(self.pmap_mode), "as", repr(self.final_pmap))
            
        # Get the mapping from old imap to new rmap, basically the imaps that
        # must be updated onto the list of rmap updates to do.
        updates_by_instrument = newcontext.get_update_map(self.final_pmap, updated_rmaps)
        
        # For each imap being edited,  and the pipeline context,  reserve new
        # official names and return the dictionary { old_mapping : new_mapping }.
        new_name_map = self.generate_new_names(updates_by_instrument)
        
        # Actually generate the new mappings,  by first copying the old mappings 
        # and then substituting old names with their updated equivalents.
        new_contexts = newcontext.generate_new_contexts(self.final_pmap, updates_by_instrument, new_name_map)
     
        for new_loc in new_contexts:
            web_certify.do_certify_file(new_loc, new_loc, context=self.final_pmap)
    
        # Create delivery records for each of the new files
        for old_ctx, new_ctx in new_name_map.items():
            self.add_crds_file(old_ctx, rmap.locate_mapping(new_ctx), update_derivation=True)
        
        # Update the edit context for the next person so they won't miss these changes,  while locked!
        new_pmap = [ mapping for mapping in new_name_map.values() if mapping.endswith(".pmap")][0]
        models.set_default_context(os.path.basename(new_pmap))
        
        return self.final_pmap, new_name_map
    
    def generate_new_names(self, updates):
        """Generate a map from old pipeline and instrument context names to the
        names for their replacements.
        """
        return { old:self.new_name(old) for old in [self.pmap_name] + updates.keys() }

    def add_crds_file(self, original_name, filepath, state="uploaded", update_derivation=None):
        """Create a FileBlob model instance using properties of this FileSubmission.
        
        These files will be deleted/destroyed if the submission fails or is cancelled when
        cleanup_failed_submission() is called.
        """
        if update_derivation is None:   # undefined
            update_derivation = self.auto_rename
        self.added_files.append((original_name, filepath))
        return models.add_crds_file(self.observatory, original_name, filepath,  str(self.user), self.user.email, 
            self.description, change_level=self.change_level, creator_name=self.creator, state=state,
            update_derivation=update_derivation)
    
    def verify_instrument_lock(self):
        """Ensure that all the submitted files correspond to the locked instrument."""
        paths = dict(self.uploaded_files).values()
        locks.verify_instrument_locked_files(self.user, self.locked_instrument, paths, self.observatory)
        
    def get_collision_list(self, newfiles):
        """Return the collision list associated with newfiles and push a status message."""
        self.push_status("Checking for derivation collisions.")
        return get_collision_list(newfiles)

    def mass_differences(self, new_file_map):
        """Compute differences html for `new_file_map` and push a status message."""
        self.push_status("Computing file differences.")
        return web_difference.mass_differences(sorted(new_file_map.items()), push_status=self.push_status)   

    # ---------------------------------------------------------------------------------------------------

    def auto_rename_file(self, upload_name, upload_path):
        """Generate a CRDS name for an uploaded file."""
        extension = os.path.splitext(upload_name)[-1]
        instrument, filekind = self.get_file_properties(upload_path)
        return self.get_new_name(instrument, filekind, extension)
    
    def new_name(self, old_map):
        """Given an old mapping name, `old_map`, adjust the serial number to 
        create a new mapping name of the same series.
        """
        instrument, filekind = self.get_file_properties(old_map)
        extension = os.path.splitext(old_map)[-1]
        new_map = self.get_new_name(instrument, filekind, extension)
        assert not (rmap.mapping_exists(new_map) or models.FileBlob.exists(new_map)), \
            "Program error.  New mapping " + srepr(new_map) + " already exists."
        return new_map
    
    def get_new_name(self, instrument, filekind, extension):
        """get_new_name() iterates over candidate serial numbers until it finds
        one which does not already exist and composes a new filename based on its
        parameters.   For a rigid naming scheme,  the first try should work.   For 
        more free-form names,   multiple tries may be required to get an unused 
        serial number.
        
        get_new_name() works by guaranteeing that:
        1) Any generated name is not already "reserved" using the CounterModel.
        2) No generated name has already been submitted by using FileBlobs.
        
        The intent of CRDS naming is to be able to infer time order from serial number.
        """
        decomposable_pattern = "{}_{}_{}_*{}".format(self.observatory, instrument, filekind, extension)
        pattern_path = rmap.locate_file(decomposable_pattern, self.observatory)
        existing = [os.path.basename(name) for name in sorted(glob.glob(pattern_path))]
        while True:
            name = self._get_new_name(instrument, filekind, extension)
            if name in existing:
                log.info("New name", repr(name), "is already in the cache.  Regenerating name.")
                continue
            if existing and naming.newer(existing[-1], name):
                log.warning("Existing name", repr(existing[-1]), "looks newer than", repr(name), ".")
            try:
                models.FileBlob.load(name)
            except LookupError:
                log.info("Latest name for", (instrument, filekind, extension), "is", repr(name))
                return name
            else:
                log.info("New name", repr(name), "is already in the database.  Regenerating name.")
                continue
    
    def _get_new_name(self, instrument, filekind, extension):
        """Generate a candidate new name,  possibly with an existing serial number if un-renamed
        files are submitted out of order.
        """
        if extension.endswith("map") or self.observatory != "hst":
            return self.get_crds_name(instrument, filekind, extension)
        else:
            return self.locate.generate_unique_name_core(instrument, filekind, extension)
        
    def get_crds_name(self, instrument, filekind, extension):
        """Return a new CRDS-style name corresponding to instrument, filekind, and extension."""
        num = self.get_crds_serial(instrument, filekind, extension)
        parts = [x for x in [self.observatory, instrument, filekind, "%04d" % num] if x]
        return "_".join(parts) + extension
            
    def get_crds_serial(self, instrument, filekind, extension):
        """Return the next reference or mapping serial number associated with the
        given parameters and update the database.   There's no guarantee the
        number isn't already taken by an ad hoc filename.
        """
        return models.CounterModel.next(self.observatory, instrument, filekind, extension)
    
    def get_file_properties(self, path):
        """Return (instrument, filekind) related to `path`."""
        return utils.get_file_properties(self.observatory, path)
    
    def locate_file(self, path):
        """Return the absolute `path`,  or the file's path in the CRDS server cache if none is given."""
        return rmap.locate_file(path, self.observatory)
    
    @property
    def locate(self):
        """Return the locator module for this observatory."""
        return utils.get_locator_module(self.observatory)

    def updated_rmaps(self):
        """Returns [ replaced_rmaps... ]"""
        groups = self.group_references()
        return [ self.pmap.get_imap(instrument).get_rmap(filekind).name
                for ((instrument, filekind), uploaded_group) in groups ]
    
    def group_references(self):
        """Groups uploaded files by instrument and type.
        Returns {(instrument,filekind) : [part_of_uploaded_files...]}
        """
        groups = {}
        seen_instrument = None
        for (original_name, uploaded_path) in self.uploaded_files.items():
            try:
                instrument, filekind = self.get_file_properties(uploaded_path)
            except Exception:
                raise CrdsError("Can't determine instrument or file type for " + srepr(original_name) + " at " + 
                                repr(uploaded_path))
            if self.locked_instrument:
                if seen_instrument is None:
                    seen_instrument = instrument
                else:
                    assert instrument == seen_instrument, \
                        "More than one instrument submitted at '%s' : '%s' vs. '%s'." % \
                        (original_name, seen_instrument, instrument)
            if (instrument, filekind) not in groups:
                groups[(instrument, filekind)] = {}
            groups[(instrument, filekind)][original_name] = uploaded_path 
        return groups.items()

    def ensure_references(self):
        """Check for references only.   If this fails, certification will fail."""
        for uploaded in self.uploaded_files:
            assert not rmap.is_mapping(uploaded), \
                "Non-reference-file's cannot be submitted in a batch submission: " + srepr(uploaded)
            if not self.auto_rename:
                assert config.is_valid_reference_name(uploaded), \
                    "Only CRDS-style and CDBS-style names can be accepted without renaming."
    
    def modify_and_add_rmaps(self, old_rmaps, cached_references):
        """Generate and submit official rmaps correspending to `old_rmaps` in 
        derivation context `pmap`,  applying class function `modify_rmaps_function` to
        the (instrument, filekind) group taken from references in `cached_references`
        for each rmap   Generate a name for a new rmap corresponding to each rmap in `old_rmaps`.
        
        Each rmap in `old_rmaps` is presumed to exist in the CRDS database, archive, and local cache.
        
        `cached_references` is  [ cached_reference_name, ... ] which will be applied to  `old_rmaps`.
        
        Return { old_rmap : new_rmap, ...}
        """
        try:
            return self._modify_and_add_rmaps(old_rmaps, cached_references)
        except Exception, exc:
            raise CrdsError("Generation of new rmaps failed: " + str(exc))

    def _modify_and_add_rmaps(self, old_rmaps, cached_references):
        """Generate and submit official rmaps correspending to `old_rmaps` in 
        derivation context `pmap`,  applying class function `modify_rmaps_function` to
        the (instrument, filekind) group taken from references in `cached_references`
        for each rmap   Generate a name for a new rmap corresponding to each rmap in `old_rmaps`.
        
        Each rmap in `old_rmaps` is presumed to exist in the CRDS database, archive, and local cache.
        
        `cached_references` is  [ cached_reference_name, ... ] which will be applied to  `old_rmaps`.
        
        Return { old_rmap : new_rmap, ...}
        """
        reference_paths = [ self.locate_file(new_reference) for new_reference in cached_references ]
        rmap_replacement_map = {}
        for old_rmap in old_rmaps:
            (instrument, filekind) = self.get_file_properties(old_rmap)
            these_ref_paths = [ refpath for refpath in reference_paths 
                if (instrument, filekind) == self.get_file_properties(refpath) ]
            new_rmap = self.get_new_name(instrument, filekind, ".rmap")
            rmap_replacement_map[old_rmap] = new_rmap
            new_rmap_path = rmap.locate_mapping(new_rmap)
            old_rmap_path = rmap.locate_mapping(old_rmap)
            self.push_status("Generating new rmap '{}' from '{}'.".format(new_rmap, old_rmap))
            # refactor inserting references.
            self.__class__.modify_rmaps_function(old_rmap_path, new_rmap_path, these_ref_paths)
            # Submit the new rmap with added references
            self.add_crds_file(new_rmap, new_rmap_path, update_derivation=True)
        return rmap_replacement_map
    
    def certify_new_mapping_list(self, rmap_replacement_map, context):
        """Certify the new rmaps from `rmap_replacement_map` relative to .pmap `context`.
        Return { old_rmap : certify_output_for_new_rmap,  ... }
        """
        files = [(mapping, rmap.locate_mapping(mapping)) for mapping in rmap_replacement_map.values()]
        new_to_old = utils.invert_dict(rmap_replacement_map)
        disposition, certify_results = web_certify.certify_file_list(files, context=context, check_references=False, # check_references=True,
                push_status=self.push_status)
        certify_results = { new_to_old[mapping]: results for (mapping, results) in certify_results }
        return disposition, sorted(certify_results.items())
# ------------------------------------------------------------------------------------------------
      
def get_collision_list(newfiles):
    """Given a list of `newfiles`,  newly created files, check the database for other children 
    of the same parent.   Return a list of triplets:  [ (newfile, parent, other_children_of_parent), ... ]
    """
    collision_list = []
    for newfile in newfiles:
        blob = models.FileBlob.load(newfile)
        collisions = blob.collisions  # collisions is a db property so cache
        if collisions:
            collision_list.append((newfile, blob.derived_from, collisions))
    return collision_list

# ------------------------------------------------------------------------------------------------

class BatchReferenceSubmission(FileSubmission):
    """Submit the uploaded files as references,  and automatically generate new rmaps and contexts relative to
    the specified derivation context (pmap_name).
    """
    modify_rmaps_function = staticmethod(refactor.rmap_insert_references)
    
    def _submit(self):
        """Certify and submit the files,  returning information to confirm/cancel."""
        # Verify that ALL references certify,  raise CrdsError on first error.
        comparison_context = self.pmap_name if self.compare_old_reference else None
        
        self.verify_instrument_lock()
        
        self.ensure_references()
        
        #   XXX Certification and submit_file_list order is critical:  certify then submit
        reference_disposition, reference_certs = web_certify.certify_file_list(self.uploaded_files.items(), 
            context=comparison_context, compare_old_reference=self.compare_old_reference, push_status=self.push_status)
    
        if reference_disposition == "bad files":
            self.cleanup_failed_submission()
            return (reference_disposition, {}, {}, reference_certs, [], {}, [])
        
        # Refactor with temporary rmap files and references to support detecting 
        # problems with refactoring prior to generating official names.
        old_rmaps = self.bsr_temporary_refactor()
        
        # name the references and get them into CRDS.
        new_references_map = self.bsr_submit_references()
        
        # Generate modified rmaps using real reference names and
        new_mappings_map = self.modify_and_add_rmaps(old_rmaps, new_references_map.values())
        
        rmap_disposition, rmap_certs = self.certify_new_mapping_list(new_mappings_map, context=comparison_context)
        
        if rmap_disposition == "bad files":
            self.cleanup_failed_submission()
            return (rmap_disposition, new_references_map, new_mappings_map, reference_certs, rmap_certs, {}, [])

        collision_list = self.get_collision_list(new_mappings_map.values())
        
        diff_results = self.mass_differences(new_mappings_map)
        
        disposition = rmap_disposition or reference_disposition

        return (disposition, new_references_map, new_mappings_map, reference_certs, rmap_certs, 
                diff_results, collision_list)

# .............................................................................

    def bsr_temporary_refactor(self):
        """Try out refactoring,  filekind-by-filekind,  and return a list of the affected rmaps.
        Returns [ replaced_rmaps... ]
        """
        groups = self.group_references()
        return [ self.bsr_temp_refactor_filekind(uploaded_group, instrument, filekind)
                for ((instrument, filekind), uploaded_group) in groups ]
    
    def bsr_temp_refactor_filekind(self, uploaded_group, instrument, filekind):
        """Refactor the original rmap inserting temporary references, creating a 
        temporary rmap to see what actions will occur.   Raise an exception if 
        any of the submitted files are duds.
        """
        old_rmap = self.pmap.get_imap(instrument).get_rmap(filekind).name
        log.info("Resolved old rmap as", repr(old_rmap), "based on context", repr(self.pmap.name))
        old_rmap_path = rmap.locate_mapping(old_rmap, self.observatory)
        tmp_rmap = tempfile.NamedTemporaryFile()
        refactor.rmap_insert_references(old_rmap_path, tmp_rmap.name, uploaded_group.values())
        return old_rmap
    
# .............................................................................

    def bsr_submit_references(self):
        """Add the uploaded references to CRDS with the supplied metadata.
        Returns { uploaded_name :  official_name, ... }
        """
        # Once both references and refactoring checks out,  submit reference files
        # and collect mapping from uploaded names to official names.
        return {
            original_name : self.do_submit_file(original_name, uploaded_path, creation_method="batch submit")
            for (original_name, uploaded_path) in sorted(self.uploaded_files.items())
        }
    
# .............................................................................

class ExistingReferenceSubmission(FileSubmission):
    """ExistingReferenceSubmission is an abstract class for generating new rmaps based on the list
    of uploaded_files, a derivation context, and a class defined rmap modification function.
    
    NOTE: uploaded_files is a misnomer,  for this class it specifies files assumed to already be
    in CRDS.
    """
    modify_rmaps_function = None

    def _submit(self):
        """Certify and submit the files,  returning information to confirm/cancel."""
        
        assert self.modify_rmaps_function is not None, "ExistingReferenceSubmission is an abstract class."
        
        # Verify that ALL references certify,  raise CrdsError on first error.
        self.verify_instrument_lock()
        
        self.ensure_references()
        
        # Refactor with temporary rmap files and references to support detecting 
        # problems with refactoring prior to generating official names.
        old_rmaps = self.updated_rmaps()
        
        # Generate modified rmaps removing existing references named in uploaded_files
        new_mappings_map = self.modify_and_add_rmaps(old_rmaps, self.uploaded_files.values())
        
        disposition, rmap_certs = self.certify_new_mapping_list(new_mappings_map, context=self.pmap_name)
        
        collision_list = self.get_collision_list(new_mappings_map.values())
        
        diff_results = self.mass_differences(new_mappings_map)
        
        if disposition == "bad files":
            self.cleanup_failed_submission()
        
        return (disposition, new_mappings_map, rmap_certs, diff_results, collision_list)

class DeleteReferenceSubmission(ExistingReferenceSubmission):
    """Given a list of existing references in (misnamed) uploaded_files,  and a derivation context,
    generate a new context which deletes all the listed references.
    """
    modify_rmaps_function = staticmethod(refactor.rmap_delete_references)
    
class AddExistingReferenceSubmission(ExistingReferenceSubmission):
    """Given a list of existing references in (misnamed) uploaded_files,  and a derivation context,
    generate a new context which includes all the listed references without adding the references
    to CRDS.
    """
    modify_rmaps_function = staticmethod(refactor.rmap_insert_references)
    
# ------------------------------------------------------------------------------------------------

class SimpleFileSubmission(FileSubmission):
    """Submit primitive files.   For pure-rmap submissions,  optionally generate contexts."""

    def _submit(self, crds_filetype, generate_contexts):
        """Submit simple files to CRDS, literally, without making automatic rules adjustments.
        
        crds_filetype:       str  -- "reference" or "mapping"
        generate_contexts:   bool -- for rmap's,  automaticaly generate appropriate .imap's and .pmap.
        
        Returns:  disposition, certify_results, new_file_map, collision_list
        
        disposition:    str --  "Failed" for certify errors or None for no errors
        certify_results:   { original_file's : (status, cerify_output), ... }
        new_file_map:  { original_filename : new_filename, ... }
        collision_list :   info about derivation sources used multiple times.
        """
        self.restrict_genre(crds_filetype, generate_contexts)
    
        if generate_contexts:
            self.verify_instrument_lock()
        
        # XXX Certification and submit_file_list order is critical:  certify then submit
        disposition, certify_results = web_certify.certify_file_list(
            self.uploaded_files.items(), context=self.pmap_name, compare_old_reference=self.compare_old_reference,
            push_status=self.push_status)
        
        if disposition == "bad files":
            self.cleanup_failed_submission()
            return (disposition, certify_results, {}, [], [])
        
        # Add the files to the CRDS database as "uploaded",  pending certification and confirmation.
        new_file_map = self.submit_file_list("submit_files")
        
        collision_list = self.get_collision_list(new_file_map.values())
        
        # Get rmaps  used as a basis for creating a new context.
        if generate_contexts:
            context_rmaps = [filename for filename in new_file_map.values() if filename.endswith(".rmap")]
        else:
            context_rmaps = []

        return disposition, certify_results, new_file_map, collision_list, context_rmaps

    def restrict_genre(self, crds_filetype, generate_contexts):
        """Ensure all `uploaded_files` tuples correspond to the genre specified by crds_filetype:  
        mapping or reference.   If generate_contexts is True,  only .rmaps may be submitted.   If
        auto-rename is turned off,  additional naming constraints are applied here.
        """
        for uploaded in self.uploaded_files:
            if generate_contexts:
                assert uploaded.endswith(".rmap"), "Only .rmaps may be submitted if Generate Contexts is selected."
            if crds_filetype == "mapping":
                if not self.auto_rename:   # ad hoc rules names cannot be added.  decompose has asserts.
                    self.obs_locate.decompose_newstyle_name(uploaded)
                    if not config.is_valid_mapping_name(uploaded):
                        raise CrdsError("Can't submit references or badly named mapping '%s' using this page." % uploaded)
            else:
                if config.is_mapping(uploaded):
                    raise CrdsError("Can't submit mapping file: '%s' using this page." % uploaded)
                if not self.auto_rename and not config.is_valid_reference_name(uploaded):
                    raise CrdsError("Invalid reference name", repr(uploaded), "unless auto-renaming is used.")

# ------------------------------------------------------------------------------------------------
        
# ------------------------------------------------------------------------------------------------
        
def submit_confirm_core(confirmed, submission_kind, description, new_files, context_rmaps, user, pmap_name, pmap_mode,
                        locked_instrument, related_files=None):
    """Handle the confirm/cancel decision of a file submission.  If context_rmaps is not [],  then it's a list
    of .rmaps from which to generate new contexts.   
    """
    instrument = filekind = "unknown"
    paths = []
    for filename in new_files:
        try:
            blob = models.FileBlob.load(filename)
        except LookupError:
            raise CrdsError("Unknown CRDS file " + srepr(filename))
        assert user == blob.deliverer_user, \
            "User " + srepr(user) + " did not submit " + srepr(filename)
        assert blob.state == "uploaded", \
            "File " + srepr(filename) + " is no longer in the 'uploaded' state."
        if blob.instrument != "unknown":
            instrument = blob.instrument
        if blob.filekind != "unknown":
            filekind = blob.filekind
        paths.append(blob.pathname)
        
    if not paths:
        raise CrdsError("No files submitted.")
    
    context_name_map = {}
    final_pmap = collisions = None
    if confirmed:
        if context_rmaps:
            # Instrument lock required since we're generating a new .imap from context_rmaps.
            locks.verify_instrument_locked_files(user, locked_instrument, paths, blob.observatory)
            # context_rmaps aren't necessarily in new_file_map and may be existing files.  So they only
            # specify changes to `pmap_name`,  not file deliveries.
            submission = FileSubmission(pmap_name, uploaded_files=None, description=description, user=user, creator="crds", 
                                        pmap_mode=pmap_mode)
            final_pmap, context_name_map = submission.do_create_contexts(context_rmaps)
            delivered_files = sorted(new_files + context_name_map.values())
        else:
            delivered_files = new_files
      
        delivery = Delivery(user, delivered_files, description, submission_kind, related_files=related_files)
        delivery.deliver()
        
        collisions = get_collision_list(context_name_map.values())
    else:
        destroy_file_list(new_files)

    return  final_pmap or pmap_name, context_name_map, collisions
    
# ------------------------------------------------------------------------------------------------
        
def create_contexts(description, context_rmaps, user, pmap_name):
    """Quick-and-dirty create contexts,  unconfirmed,  intended for super-users."""
    for filename in context_rmaps:
        try:
            blob = models.FileBlob.load(filename)
        except LookupError:
            raise CrdsError("Unknown CRDS file " + srepr(filename))
        assert blob.state in sconfig.CRDS_DISTRIBUTION_STATES, "File " + srepr(filename) + " is only in state " + srepr(blob.state)
        
    # context_rmaps aren't necessarily in new_file_map and may be existing files.  So they only
    # specify changes to `pmap_name`,  not file deliveries.
    submission = FileSubmission(pmap_name, uploaded_files=None, description=description, user=user, creator="crds")
    
    # UNLOCKED context creation
    _final_pmap, context_name_map = submission.do_create_contexts_unlocked(context_rmaps)

    delivered_files = sorted(context_name_map.values())
    delivery = Delivery(user, delivered_files, description, "new context")
    delivery.deliver()
        
    collisions = get_collision_list(context_name_map.values())

    return  context_name_map, collisions
    
# ------------------------------------------------------------------------------------------------

def fix_unicode(items):
    return [(str(old), str(new)) for (old, new) in items]
 
def destroy_file_list(files):
    """Remove the database record of `files` as well as `files` themselves.
    NOTE: This only removes the CRDS official copy of the file, not the original upload copy.
    """
    for filename in files:
        blob = models.FileBlob.load(filename)
        blob.destroy()

# ------------------------------------------------------------------------------------------------

def deliver_file_list(user, observatory, delivered_files, description, action):
    """Deliver a list of files,  making them available for OPUS pickup but not yet archived."""
    delivery = Delivery(user, delivered_files, description, action, observatory=observatory)
    return delivery.deliver()

class Delivery(object):
    """The Delivery class manages creating a delivery catalog and file links for delivered files
    in the appropriate directory.  Afterward it updates FileBlobs to refer to the delivery .cat file
    and to have state "delivered".   While the CRDS pipeline is executing the delivery,  the .cat
    file is renamed to .cat_proc.   When the archive has accepted the delivery,  the .cat_proc file
    is removed.   CRDS updates the state of "delivered" files
    """
    def __init__(self, user, delivered_files, description, action, observatory=sconfig.observatory, related_files=None):
        self.user = str(user)
        self.description = description
        self.action = action
        if not len(delivered_files):
            raise CrdsError("No files were selected for delivery.")
        self.delivered_files = [str(x) for x in sorted(delivered_files)]
        self.observatory = observatory
        self.related_files = related_files or []
            
    def deliver(self):
        """Perform delivery actions for `delivered_files` by setting up the
        catalog file and making links, updating database and audit trail.
        """
        catalog = self.deliver_file_catalog()
        paths = self.delivered_paths
        try:
            catalog_link = self.deliver_make_links(catalog, paths)
        except Exception, exc:
            self.deliver_remove_fail(catalog, paths)
            raise CrdsError("Delivery failed: " + str(exc))
        self.update_file_blobs(catalog_link)
        details = repr([os.path.basename(catalog)] + self.delivered_files + self.related_files)
        models.AuditBlob.new( 
            self.user, self.action, os.path.basename(catalog), self.description, details, self.observatory)        
        for filename in self.delivered_files:
            models.AuditBlob.new(self.user, self.action, filename, self.description, details, self.observatory)

    @property
    def delivered_paths(self):
        """Adjust the database to account for this delivery.   Returns a list of
        absolute paths to `files`.
        """
        return [models.FileBlob.load(filename).pathname for filename in self.delivered_files]

    def update_file_blobs(self, catalog_link):
        """Set the `catalog_link` in the FileBlob for each delivered file and change
        state to "delivered".  Delivered means that OPUS now has the opportunity to pick up the file.   
        As long as the .cat or .cat_proc (variants of catalog_link) exists, it is considered "delivered"
        but not yet archived or "operational".  When the catalog_link no longer
        exists,  it is assumed OPUS has copied the file, deleted the delivery link,
        and the file transitions from "delivered" to "operational".   Here,
        "operational" means that OPUS and the archives have the context or file 
        available,  not necessarily that the pipeline is currently using the context.
        """
        for filename in self.delivered_files:
            blob = models.FileBlob.load(filename)
            blob.catalog_link = catalog_link
            blob.state = "delivered"
            blob.save()
    
    def deliver_file_catalog(self, operation="I"):
        """Generate the delivery catalog file and return its path.   The catalog
        file is a kind of manifest and semaphore used by OPUS to know that a
        delivery has been made and what files are in it.   When CRDS links the
        catalog file and deliveries into the delivery directories,  they are
        considered "delivered". When OPUS deletes the catalog link,  the file is
        considered "operational".
    
        The filepath is something like:
           /hstdev/store/srefpipe/deliverfilesauto/opus_12314_i.cat    
    
        Each line of the catalog has the form:
           <filename> <operation> <kind>
            .e.g. V9M1422QI_DRK I R
    
        where operation can be I=insert or D=delete
        where kind can be M=mapping or R=reference or T=table
        
        NOTE: The T=table kind is obsolete and not used.  All reference files, tables and 
        not-tables alike,  are type R.
        
        CRDS uses the catalog file name to name the delivery for auditing.
        """
        assert operation in ["I","D"], "Invalid delivery operation " + srepr(operation)
        delivery_id = models.CounterModel.next(self.observatory, "delivery_id")
        if self.observatory == "hst":
            catalog = "_".join(["opus", str(delivery_id), operation.lower()]) + ".cat"
        else:
            catalog = "jwst_" + str(delivery_id) + ".cat"
        catpath = os.path.join(sconfig.CRDS_CATALOG_DIR, catalog)
        utils.ensure_dir_exists(catpath)
        cat = open(catpath, "w")
        for filename in self.delivered_files:
            cat.write(filename + "\n")
        cat.close()
        os.chmod(catpath, 0444)
        return catpath

    def deliver_make_links(self, catalog, paths):
        """Copy file `paths` to the proper holding area and then make hard links to
        each file in each of the delivery site directories.   Return the path of 
        the of the master catalog link;  when the master link is deleted by the 
        recipient the entire delivery is considered complete and the files
        transition from "delivered" to "operational".
        """
        dirs = sconfig.CRDS_DELIVERY_DIRS
        for site in dirs:
            utils.ensure_dir_exists(site)
            for filename in paths + [catalog]:
                dest = site +"/" + os.path.basename(filename)
                try:
                    os.link(filename, dest)
                except Exception, exc:
                    raise CrdsError("failed to link " + srepr(filename) + " to " + srepr(dest) + " : " + str(exc))
        master_catalog_link = os.path.join(dirs[0], os.path.basename(catalog))
        return master_catalog_link

    def deliver_remove_fail(self, catalog, paths):
        """Delete all the delivery links for a failed but possibly partially
        completed delivery.
        """
        for site in sconfig.CRDS_DELIVERY_DIRS + [os.path.dirname(catalog)]:
            for filename in paths + [catalog]:
                dest = site +"/" + os.path.basename(filename)
                try:
                    os.remove(dest)
                except Exception:
                    pass
    
# ------------------------------------------------------------------------------------------------
        
#if __name__ == "__main__":
#    SubmitFilesScript()()
