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
import getpass

from crds import cmdline, log, rmap, utils, refactor, newcontext, checksum, CrdsError

from . import models, web_certify, web_difference
from .common import srepr

from crds.server import config as sconfig

from django.contrib.auth.models import User

# ----------------------------------------------------------------------------------------------------

def file_exists_somehow(filename):
    """Return True IFF `filepath` really exists or CRDS thinks it does."""
    filepath = rmap.locate_file(filename, sconfig.observatory)
    return os.path.exists(filepath) or \
        models.FileBlob.exists(os.path.basename(filepath))

# ----------------------------------------------------------------------------------------------------

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
        self.add_argument("--change-level", choices=["trivial", "medium", "severe"], store_in="change_level", default="severe",
                          help="Degree to which submitted files impact science results.")
        self.add_argument("--description", help="Free text description of file submission.")
        self.add_argument("--auto-rename", action="store_true", default=False,
                          help="If specified,  automatically rename files to CRDS-style versioned names.")
        self.add_argument("--compare-old-references", action="store_true", default=False,
                          help="If specified, check references against the files they replace in derive-from-context, where applicable.")
        self.add_argument("--generate-rules", action="store_true", default=False,
                          help="If specified, generate mappings as required to add the submitted files to the derived-from-context.")
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
        
# ------------------------------------------------------------------------------------------------

class FileSubmission(object):
    """Baseclass for file submissions,  carrier object for submission metadata and files."""
    
    def __init__(self, pmap_name, uploaded_files, description, user, creator="UNKNOWN",
                 change_level="SEVERE", auto_rename=True, compare_old_reference=False):
        self.pmap = rmap.get_cached_mapping(pmap_name)
        self.observatory = self.pmap.observatory
        self.uploaded_files = uploaded_files
        self.description = description
        self.user = user if isinstance(user, User) else User.objects.get(username=user)
        self.creator = creator
        self.change_level = change_level
        self.auto_rename = auto_rename
        self.compare_old_reference = compare_old_reference
        self.instrument = None
    
    def submit(self):
        """Validate the submitted files and add them to the database."""
        
    def ensure_unique_uploaded_names(self):
        """Make sure there are no duplicate names in the submitted file list."""
        # This is a sensible check for files originating on the command line.
        uploaded_as, paths = zip(*self.uploaded_files)
        pathmap = dict(*zip(paths, uploaded_as))
        for name in uploaded_as:
            assert uploaded_as.count(name) == 1, "File '%s' appears more than once." % name
        for path in paths:
            assert paths.count(path) == 1, "File path for '%s' appears more than once." %  pathmap[path]
    
    def submit_file_list(self, creation_method):
        """Ingest a list of `uploaded_files` tuples into CRDS."""
        return { original_name: self.do_submit_file(original_name, uploaded_path, creation_method=creation_method)
                for (original_name, uploaded_path) in self.uploaded_files.items() }

    def do_submit_file(self, original_name, upload_location, creation_method):
        """Do the core processing of a file submission,  including file certification 
        and blacklist checking, naming, upload, and record keeping.
        """
        if rmap.is_mapping(original_name):
            try:
                checksum.update_checksum(upload_location)
            except rmap.MappingError, exc:
                raise CrdsError("Error updating checksum: " + srepr(exc))
        
        # Automatically 
        if self.auto_rename:
            permanent_name = auto_rename_file(self.observatory, original_name, upload_location)
        else:
            if file_exists_somehow(original_name):
                raise CrdsError("File " + srepr(original_name) + " already exists.") 
            else:
                permanent_name = os.path.basename(original_name)   
    
        # CRDS keeps all new files in a standard layout.  Existing files in /grp/cdbs
        # are currently referenced by standard symlinks in the CRDS server file tree.
        permanent_location = rmap.locate_file(permanent_name, self.observatory)
    
        # Make sure none of the dependencies are blacklisted,  else fail w/o state.
        blacklisted_by = web_certify.get_blacklists(original_name, upload_location)
        if blacklisted_by:
            raise CrdsError("File " + srepr(original_name) + " is blacklisted by " + srepr(blacklisted_by))
        
        # Move or copy the temporary file to its permanent location.
        utils.ensure_dir_exists(permanent_location)
        os.link(upload_location, permanent_location)
    
        # Make a database record for this file.
        self.add_crds_file(original_name, permanent_location)
        
        return os.path.basename(permanent_location)

    def do_create_contexts(self, updated_rmaps):
        """Create new contexts based on `pmap_name` which refer to `updated_rmaps`
        instead of the corresponding old rmaps.  Add the new contexts to the
        CRDS database and return a list of new context mapping names.
        """
        # Get the mapping from old imap to new rmap, basically the imaps that
        # must be updated onto the list of rmap updates to do.
        updates_by_instrument = newcontext.get_update_map(self.pmap.name, updated_rmaps)
        
        # For each imap being edited,  and the pipeline context,  reserve new
        # official names and return the dictionary { old_mapping : new_mapping }.
        new_name_map = self.generate_new_names(updates_by_instrument)
        
        # Actually generate the new mappings,  by first copying the old mappings 
        # and then substituting old names with their updated equivalents.
        new_contexts = newcontext.generate_new_contexts(self.pmap.name, updates_by_instrument, new_name_map)
     
        new_pmap = [ctx for ctx in new_contexts if ctx.endswith(".pmap")][0]
        new_loc = rmap.locate_mapping(new_pmap)  
        web_certify.do_certify_file(new_loc, new_loc, context=self.pmap.name)
    
        # Create delivery records for each of the new files
        for old_ctx, new_ctx in new_name_map.items():
            self.add_crds_file(old_ctx, rmap.locate_mapping(new_ctx))
        
        return new_name_map
    
    def generate_new_names(self, updates):
        """Generate a map from old pipeline and instrument context names to the
        names for their replacements.
        """
        return { old:new_name(old) for old in [self.pmap.name] + updates.keys() }

    def add_crds_file(self, original_name, filepath, state="uploaded"):
        """Create a FileBlob model instance using properties of this FileSubmission."""
        return models.add_crds_file(self.observatory, original_name, filepath,  str(self.user), self.user.email, 
            self.description, change_level=self.change_level, creator_name=self.creator, state=state)
        
# ------------------------------------------------------------------------------------------------

def do_create_contexts(pmap_name, updated_rmaps, description, user):
    """Support the create contexts view with a function call."""
    submission = FileSubmission(pmap_name, uploaded_files=None, description=description, user=user, creator="crds")
    return submission.do_create_contexts(updated_rmaps)

# ------------------------------------------------------------------------------------------------

class BatchReferenceSubmission(FileSubmission):
    """Submit the uploaded files as references,  and automatically generate new rmaps and contexts relative to
    the specified derivation context (pmap_name).
    """
    def submit(self):
        """Certify and submit the files,  returning information to confirm/cancel."""
        # Verify that ALL references certify,  raise CrdsError on first error.
        comparison_context = self.pmap.name if self.compare_old_reference else None
        
        self.bsr_ensure_references()
        
        reference_disposition, reference_certs = web_certify.certify_file_list(self.uploaded_files.items(), 
            context=comparison_context, compare_old_reference=self.compare_old_reference)
    
        # Refactor with temporary rmap files and references to support detecting 
        # problems with refactoring prior to generating official names.
        old_rmaps = self.bsr_temporary_refactor()
        
        # name the references and get them into CRDS.
        new_references_map = self.bsr_submit_references()
        
        # Generate modified rmaps using real reference names and
        new_mappings_map = self.bsr_generate_real_rmaps(old_rmaps, new_references_map)
        
        rmap_disposition, rmap_certs = self.bsr_certify_new_mapping_list(new_mappings_map, context=comparison_context)
        
#        # Generate a new context referring to the new rmap
#        higher_level_mapping_map = self.do_create_contexts(new_mappings_map.values())
#        
#        new_mappings_map.update(higher_level_mapping_map)
    
        collision_list = get_collision_list(new_mappings_map.values())
        
        # Just display the .pmap,  which recursively captures the others and sorts first.
        diff_results = web_difference.mass_differences(sorted(new_mappings_map.items()))
        
        disposition = rmap_disposition or reference_disposition
        
        return (disposition, new_references_map, new_mappings_map, reference_certs, rmap_certs, diff_results, collision_list)

# .............................................................................

    def bsr_ensure_references(self):
        """Check for references only.   If this fails, certification will fail."""
        for uploaded in self.uploaded_files:
            assert not rmap.is_mapping(uploaded), \
                "Non-reference-file's cannot be submitted in a batch submission: " + srepr(uploaded)

    def bsr_temporary_refactor(self):
        """Try out refactoring,  filekind-by-filekind,  and return a list of the affected rmaps.
        Returns [ replaced_rmaps... ]
        """
        return [ self.bsr_temp_refactor_filekind(uploaded_group, instrument, filekind)
                for ((instrument, filekind), uploaded_group) in self.bsr_group_references() ]
    
    def bsr_temp_refactor_filekind(self, uploaded_group, instrument, filekind):
        """Refactor the original rmap inserting temporary references, creating a 
        temporary rmap to see what actions will occur.   Raise an exception if 
        any of the submitted files are duds.
        """
        old_rmap = self.pmap.get_imap(instrument).get_rmap(filekind).name
        old_rmap_path = rmap.locate_mapping(old_rmap, self.observatory)
        tmp_rmap = tempfile.NamedTemporaryFile()
        refactor.rmap_insert_references(old_rmap_path, tmp_rmap.name, uploaded_group.values())
        # XXX TODO unhandled files,  references resulting in no change.
        # XXX TODO duplicate matches,  references changing the same path.    
        return old_rmap
    
    def bsr_group_references(self):
        """Groups uploaded files by instrument and type.
        Returns {(instrument,filekind) : [part_of_uploaded_files...]}
        """
        groups = {}
        for (original_name, uploaded_path) in self.uploaded_files.items():
            try:
                instrument, filekind = utils.get_file_properties(self.observatory, uploaded_path)
            except Exception:
                raise CrdsError("Can't determine instrument or file type for " + srepr(original_name))
            if self.instrument is not None:
                assert instrument == self.instrument, \
                    "More than one instrument submitted at '%s' : '%s' vs. '%s'." % (original_name, self.instrument, instrument)
            self.instrument = instrument
            if (instrument, filekind) not in groups:
                groups[(instrument, filekind)] = {}
            groups[(instrument, filekind)][original_name] = uploaded_path 
        return groups.items()
    
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
    
    def bsr_certify_new_mapping_list(self, rmap_replacement_map, context):
        """Certify the new rmaps from `rmap_replacement_map` relative to .pmap `context`.
        Return { old_rmap : certify_output_for_new_rmap,  ... }
        """
        files = [(mapping, rmap.locate_mapping(mapping)) for mapping in rmap_replacement_map.values()]
        new_to_old = utils.invert_dict(rmap_replacement_map)
        disposition, certify_results = web_certify.certify_file_list(files, context=context, check_references=False)
        certify_results = { new_to_old[mapping]: results for (mapping, results) in certify_results }
        return disposition, sorted(certify_results.items())

# .............................................................................

    def bsr_generate_real_rmaps(self, old_rmaps, new_references_map):
        """Generate and submit official rmaps correspending to `old_rmaps` in 
        derivation context `pmap`,  inserting references from `new_references_map`.
        
        Now that we know that refactoring works and what the new references will be
        named,  allocate new supporting rmap names and refactor again for real.
        
        Return { old_rmap : new_rmap, ...}
        """
        # Dig these out of the database rather than passing them around.
        reference_paths = [ models.FileBlob.load(new_reference).pathname
                            for new_reference in new_references_map.values() ]
        rmap_replacement_map = {}
        for old_rmap in old_rmaps:
            (instrument, filekind) = utils.get_file_properties(self.observatory, old_rmap)
            these_ref_paths = [ refpath for refpath in reference_paths 
                if (instrument, filekind) == utils.get_file_properties(self.observatory, refpath) ]
            new_rmap = get_new_name(self.observatory, instrument, filekind, ".rmap")
            rmap_replacement_map[old_rmap] = new_rmap
            new_rmap_path = rmap.locate_mapping(new_rmap)
            old_rmap_path = rmap.locate_mapping(old_rmap)
            # refactor inserting references.
            refactor.rmap_insert_references(old_rmap_path, new_rmap_path, these_ref_paths)
            # Submit the new rmap with added references
            self.add_crds_file(new_rmap, new_rmap_path)
        return rmap_replacement_map
    
# ------------------------------------------------------------------------------------------------

class SimpleFileSubmission(FileSubmission):
    """Submit primitive files.   For pure-rmap submissions,  optionally generate contexts."""

    def submit(self, crds_filetype, generate_contexts):
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
    
        # Verify that ALL files certify.
        disposition, certify_results = web_certify.certify_file_list(
            self.uploaded_files.items(), context=self.pmap.name, compare_old_reference=self.compare_old_reference)
        
        # Add the files to the CRDS database as "uploaded",  pending confirmation.
        new_file_map = self.submit_file_list("submit files")
        
        collision_list = get_collision_list(new_file_map.values())
        
        # Get rmaps  used as a basis for creating a new context.
        if generate_contexts:
            context_rmaps = [filename for filename in new_file_map.values() if filename.endswith(".rmap")]
        else:
            context_rmaps = []
        
        return disposition, certify_results, new_file_map, collision_list, context_rmaps

    def restrict_genre(self, crds_filetype, generate_contexts):
        """Ensure all `uploaded_files` tuples correspond to the genre specified by crds_filetype:  
        mapping or reference.   If generate_contexts is True,  only .rmaps may be submitted.
        """
        for uploaded in self.uploaded_files:
            if generate_contexts:
                assert uploaded.endswith(".rmap"), "Only .rmaps may be submitted if Generate Contexts is selected."
            if crds_filetype == "mapping":
                if not rmap.is_mapping(uploaded):
                    raise CrdsError("Can't submit non-mapping file: " + repr(uploaded) + " using this page.")
                if generate_contexts and not uploaded.endswith(".rmap"):
                    raise CrdsError("Can't submit non-rmap's and generate contexts: " + srepr(uploaded))
            else:
                if rmap.is_mapping(uploaded):
                    raise CrdsError("Can't submit mapping file: " + repr(uploaded) + " using this page.")

# ------------------------------------------------------------------------------------------------
        
def get_new_serial(observatory, instrument, filekind, extension):
    """Return the next reference or mapping serial number associated with the
    given parameters and update the database.   There's no guarantee the
    number isn't already taken by an ad hoc filename.
    """
    return models.CounterBlob.next(observatory, instrument, filekind, extension)

def _get_new_name(observatory, instrument, filekind, extension):
    """Generate a candidate new name,  possibly with an existing serial number.
    """
    num = get_new_serial(observatory, instrument, filekind, extension)
    parts = [x for x in [observatory, instrument, filekind, "%04d" % num] if x]
    return "_".join(parts) + extension

def get_new_name(observatory, instrument, filekind, extension):
    """get_new_name() iterates over candidate serial numbers until it finds
    one which does not already exist and composes a new filename based on its
    parameters.   For a rigid naming scheme,  the first try should work.   For 
    more free-form names,   multiple tries may be required to get an unused 
    serial number.
    
    get_new_name() works by guaranteeing that:
    1) Any generated name is not already "reserved" using the CounterBlob.
    2) No generated name has already been submitted by using FileBlobs.
    """
    name = _get_new_name(observatory, instrument, filekind, extension)
    while True:
        try:
            _already_in_use = models.FileBlob.load(name)
        except LookupError:
            break
        name = _get_new_name(observatory, instrument, filekind, extension)
    return name

def auto_rename_file(observatory, upload_name, upload_path):
    """Generate a CRDS name for an uploaded file."""
    extension = os.path.splitext(upload_name)[-1]
    instrument, filekind = utils.get_file_properties(
        observatory, upload_path)
    return get_new_name(observatory, instrument, filekind, extension)

def new_name(old_map):
    """Given an old mapping name, `old_map`, adjust the serial number to 
    create a new mapping name of the same series.
    """
    observatory = rmap.get_cached_mapping(old_map).observatory
    instrument, filekind = utils.get_file_properties(
        observatory, old_map)
    extension = os.path.splitext(old_map)[-1]
    new_map = get_new_name(observatory, instrument, filekind, extension)
    assert not (rmap.mapping_exists(new_map) or models.FileBlob.exists(new_map)), \
        "Program error.  New mapping " + srepr(new_map) + " already exists."
    return new_map

# ------------------------------------------------------------------------------------------------
        
def get_collision_list(newfiles):
    """Given a list of `newfiles`,  newly created files,
    check the database for other children of the same parent.   Return a
    list of triplets:  [ (newfile, parent, other_children_of_parent), ... ]
    """
    collision_list = []
    for newfile in newfiles:
        blob = models.FileBlob.load(newfile)
        collisions = blob.collisions  # collisions is a db property so cache
        if collisions:
            collision_list.append((newfile, blob.derived_from, collisions))
    return collision_list

# ------------------------------------------------------------------------------------------------
        
def submit_confirm_core(confirmed, submission_kind, description, new_files, context_rmaps, user, pmap_name):
    """Handle the confirm/cancel decision of a file submission.  If context_rmaps is not [],  then it's a list
    of .rmaps from which to generate new contexts.   
    """
    instrument = filekind = "unknown"
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

    context_name_map = {}
    if confirmed:
        if context_rmaps:
            # context_rmaps aren't necessarily in new_file_map and may be existing files.  So they only
            # specify changes to `pmap_name`,  not file deliveries.
            context_name_map = do_create_contexts(pmap_name, context_rmaps, description, user)
            delivered_files = sorted(new_files + context_name_map.values())
        else:
            delivered_files = new_files
      
        delivery = Delivery(user, delivered_files, description, submission_kind)
        delivery.deliver()

        for mapping in new_files:
            if mapping.endswith(".pmap"):
                models.set_default_context(mapping)
                break
    else:
        destroy_file_list(new_files)

    return  context_name_map
    
def fix_unicode(items):
    return [(str(old),str(new)) for (old,new) in items]

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
    def __init__(self, user, delivered_files, description, action, observatory=sconfig.observatory):
        self.user = str(user)
        self.description = description
        self.action = action
        if not len(delivered_files):
            raise CrdsError("No files were selected for delivery.")
        self.delivered_files = [str(x) for x in sorted(delivered_files)]
        self.observatory = observatory
            
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
        details = repr([os.path.basename(catalog)] + self.delivered_files)
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
        delivery_id = models.CounterBlob.next(self.observatory, "delivery_id")
        catalog = "_".join(["opus", str(delivery_id), operation.lower()])+".cat"
        catpath = os.path.join(sconfig.CRDS_CATALOG_DIR, catalog)
        utils.ensure_dir_exists(catpath)
        cat = open(catpath, "w")
        for filename in self.delivered_files:
            kind = "R"
            cat.write(filename + " " + operation + " " + kind + "\n")
        cat.close()
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
        
if __name__ == "__main__":
    SubmitFilesScript()()
