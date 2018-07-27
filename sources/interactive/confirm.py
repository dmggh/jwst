"""This module defines common code related to confirming file submissions and
rules updates of various forms.    

The purpose of confirmation is to finalize the status of files which have been
accepted into CRDS or generated (rmaps) and often also to generate higher level
context files (imaps and pmaps) which depend on the active context.

Files which are confirmed are:

* Transitioned in the database from an "uploaded" to a more official "delivered" state.
* Linked into a delivery directory for delivery to the archive.

Files which are canceled are:

* Removed from the database
* Removed from the CRDS cache

There is potential for confirmation to generate higher level contexts:

* Typically the source context is defined relative to the <observatory>-edit context, e.g. jwst-edit
* While locked,  updated imaps and corresponding pmap are generated to support new rmaps
* The edit context is set to the resulting generated context
* All the generated files are cataloged and delivered similar to the submitted files
* It's possible for different instruments to compete for the context
   - Instrument locks prevent modification of the same imaps
   - Abstract contexts (-edit, -operational) adjust to using a context updated by a submission for another instrument.

A brief summary of the functions performed by the submission confirmation process is:

0. Confirmation is only performed on a web page after reviewing submission results.
1. User authentication is verified,  including membership in group file_submission.
2. The instrument lock is verified, ensuring it has not been dropped and/or re-qcuired
3. Failsafe error trapping
4. Higher functionality error trapping with e-mail and web messaging
5. Repeatable results for later review of submission
6. Confirmation e-mail
7. Higher level context generation
8. File linking to CRDS poller delivery directory
"""
import os.path
import re

# ===========================================================================

from crds import CrdsError
from crds.core import log, pysh

# ===========================================================================

from .. import config as sconfig

# ===========================================================================

from . import models
from . import submit
from . import locks
from . import mail
from . import render
from .common import srepr

# ===========================================================================

HERE = os.path.dirname(__file__) or "./"

# ===========================================================================

class Confirm:
    """Check submission confirmation inputs,  authentication, and verify instrument 
    locking relative to `request` and prior submission results.  Store various parameters 
    as attributes for later use during the confirm/cancel.
    """
    def __init__(self, request, button, results_id):
        # don't rely on locking mechanisms to verify this since @login_required is turned off
        # and locking may change.
        if not request.user.is_authenticated:
            raise CrdsError("You must be logged in to confirm or cancel file submissions.")
        self.disposition = button + "d" if button.endswith("e") else button + "ed"
        # The repeatable result model from the READY response carries info needed to confirm
        try:
            self.repeatable_model = models.RepeatableResultBlob.load(results_id)
        except Exception as exc:
            raise CrdsError("Error fetching result: " + results_id + " : " + str(exc))        
        if self.repeatable_model.parameters.get("disposition", None):
            raise CrdsError("This submission was already confirmed or cancelled.")
        self.result = self.repeatable_model.parameters
        
        # Locking needs to be checked before finalizing below.
        self._check_locking(request)

    @property
    def confirmed(self):
        return self.disposition in ["confirmed", "forced"]

    @property    
    def new_file_map(self):
        return dict(self.result.new_file_map)
    
    @property
    def new_files(self):
        return list(self.new_file_map.values())
    
    def _check_locking(self, request):
        """Verify that the same lock used by the original submission is still held by
        the user. 
        
        This verifies that they did not lose it and reaquire it, effectively defeating 
        the point of locking since another user could have obtained, submitted, and 
        dropped the lock during the gap.   
    
        This is particularly convoluted due to the CRDS client's command line interface 
        which necessarily does authentication and lock reservation and uses a different
        web session.
        """
        self.instrument_lock_id = locks.get_instrument_lock_id(request)
        should_still_be_locked = self.result.get("should_still_be_locked", None) 
        self.locked_instrument = locks.instrument_from_lock_id(should_still_be_locked)
        username = str(request.user)
        if self.disposition == "confirmed":
            assert username == self.result.user, \
                "User mismatch: file Submitter='%s' and Confirmer='%s' don't match." % (username, self.result.user)
            if should_still_be_locked and should_still_be_locked != self.instrument_lock_id:
                raise locks.BrokenLockError(
                    "BROKEN LOCK: Original submission lock", repr(should_still_be_locked), 
                    "does not match current lock", repr(self.instrument_lock_id), 
                    ".  Use 'force' to confirm anyway.")
        elif self.disposition in ["cancel", "force"]:
            my_locked_instrument = locks.instrument_of(username)
            if self.locked_instrument and my_locked_instrument != self.locked_instrument:
                raise CrdsError("You locked", repr(my_locked_instrument), "but must own lock for", 
                                repr(self.locked_instrument), "to cancel or force this submission.")

    def process(self, request):
        """Execute this confirmation request based on the button clicked,  either confirming
        or canceling.   Issue an appropriate e-mail and render confirmed.html as a repeatable
        result.   Return the result which can be sent to JPOLL's done response, returned by the view 
        function,  and referenced by the confirm/cancel e-mail.
        """
        # Mark the READY model as finalizing to prevent double confirmations,  must save now
        # to block other asynchronous confirm invocations.
        self.repeatable_model.set_par("disposition", "finalizing")
        self.repeatable_model.save()
    
        if self.confirmed:
            template_vars = self.confirm_files(request)
        else:
            template_vars = self.cancel_files()
            
        repeatable_result = self.common_reply(request, template_vars)

        return repeatable_result

    def confirm_files(self, request):
        """If `context_rmaps` is a list of rmaps,  generate appropriate imaps and .pmap.
        Either way,  deliver all submitted and generated files to delivery directory.
        """
        self.check_new_files()

        final_pmap, context_map, delivered_files = self.context_generation()
        
        delivery = submit.Delivery(
            self.result.user, delivered_files, self.result.description, self.result.submission_kind)
        delivery.deliver()
        
        collision_list = submit.get_collision_list(list(context_map.values()))        

        # NOTE single model save later in processing flow
        # By the time confirmation happens,  the derived_from pmap may have evolved for another instrument.
        # Record the pmap the submitter added to,  and the final pmap generated here.
        self.repeatable_model.set_par("original_pmap", self.result.pmap)
        self.repeatable_model.set_par("pmap", final_pmap)

        template_vars = self.get_confirm_vars(final_pmap, context_map, collision_list)

        clear_uploads(request, self.result.uploaded_basenames)
        models.clear_cache()
        submit.update_edit_context(delivered_files)

        return template_vars
    
    def context_generation(self):
        """If the READY result defined rmaps to inject into a context,  generate the context
        (imaps and pmaps) now and add them to the list of delivered files.
        """
        if self.result.context_rmaps:   # Make a fake(?) submission to generate contexts
            file_submission = submit.FileSubmission(
                self.result.pmap, uploaded_files=None, description=self.result.description, 
                user=self.result.user, creator="crds", pmap_mode=self.result.pmap_mode)

            final_pmap, context_map = file_submission.do_create_contexts(self.result.context_rmaps)
            
            delivered_files = sorted(self.new_files + list(context_map.values()))
            
            return final_pmap, context_map, delivered_files
        else:   # no context generated,  only deliver new files.
            return None, {}, self.new_files
        
    
    def get_confirm_vars(self, final_pmap, context_map, collision_list):
        """Return template variables appropriate for confirming this submission."""  
        new_file_map = sorted(list(self.new_file_map.items()) + list(context_map.items()))
        generated_files = sorted([(old, new) for (old, new) in new_file_map
                                  if old not in self.result.uploaded_basenames])
        uploaded_files = [(old, new) for (old, new) in new_file_map
                          if (old, new) not in generated_files]
        
        # rmaps specified for context generation but not uploaded or generated
        context_rmaps = [filename for filename in self.result.context_rmaps
            if filename not in list(dict(generated_files).values()) + self.result.uploaded_basenames]
    
        template_vars = dict(
            context_map = context_map,
            pmap_mode = self.result.pmap_mode,
            pmap = self.result.pmap,    # .pmap seen at submission time,  expected derive_from
            final_pmap = final_pmap,    # actual abstract .pmap at confirmation time,  actual derive_from
            original_pmap = self.result.original_pmap,
            uploaded_files=uploaded_files,
            added_files=getattr(self.result, "added_files", []),
            deleted_files=getattr(self.result, "deleted_files", []),
            context_rmaps=context_rmaps,
            generated_files=generated_files,
            new_file_map=new_file_map,
            collision_list=collision_list,
            more_submits=self.result.more_submits)
    
        return template_vars

    def cancel_files(self):
        """Wipe out any database + file system representation of `new_files` and return empty 
        template vars suitable for the cancel response.
        """
        for new in self.new_files:
            with log.error_on_exception("Failed marking", repr(new), "as cancelled."):
                blob = models.FileBlob.load(new)
                blob.destroy()
        template_vars = dict(
            uploaded_files = [],
            generated_files = [],
            added_files = [],
            deleted_files = [],
            final_pmap = None,
            context_map = {},
            collision_list = None,
            )
        # template_vars, final_pmap, context_map, collision_list
        return template_vars

    def common_reply(self, request, template_vars):
        """Based on `template_vars` augmented by values common to confirm + cancel,
        generate the confirmation HTML and e-mail using common  web and mail templates.
        
        The HTML response is rendered to a repeatable result model which will later be
        displayed for the first time using a redirection to the repeatable results view.
        Likewise the e-mail and JPOLL done message will refer to that repeatable results
        URL.
        
        Returns a new CONFIRM / CANCEL repeatable result that follows the repeatable READY 
        result from the original submission view.
        """
        # Update the "READY" model with the results of this confirmation to prevent repeat confirms
        self.repeatable_model.set_par("disposition" , self.disposition)
        self.repeatable_model.save()  # NOTE required by earlier set_par() above
    
        # Add info common to both confirmed and canceled
        template_vars["disposition"] = self.disposition
        template_vars["confirmed"] = self.confirmed
        template_vars["description"] = self.repeatable_model.parameters["description"]
        template_vars["prior_results_url"] = self.repeatable_model.abs_repeatable_url
        
        # Do the web response
        new_result = render.render_repeatable_result(request, "confirmed.html", template_vars)
    
        # Issue and e-mail indicating confirm/cancel with details from the submission.
        username = request.user.first_name + " " + request.user.last_name
        results_kind = self.repeatable_model.parameters["submission_kind"].title()
        mail.crds_notification(
            body = mail.GENERIC_CONFIRMED_BODY, status=self.disposition.upper(),
            username = username, user_email = request.user.email, 
            results_kind = results_kind,
            repeatable_url = new_result.abs_repeatable_url,
            to_addresses  = sconfig.CRDS_STATUS_CONFIRM_ADDRESSES,
            **template_vars)
        
        return new_result
    
    def check_new_files(self):
        """Verify that each filename in `new_files`:
        1. Exists in CRDS in the uploaded state.
        2. Was delivered by `user` name.
        3. Resulting list of CRDS file paths is not an empty list.
        """
        paths = []
        for filename in self.new_files:
            try:
                blob = models.FileBlob.load(filename)
            except LookupError:
                raise CrdsError("Unknown CRDS file " + srepr(filename))
            assert self.result.user == blob.deliverer_user, \
                "User " + srepr(self.result.user) + " did not submit " + srepr(filename)
            assert blob.state == "uploaded", \
                "File " + srepr(filename) + " is no longer in the 'uploaded' state."
            paths.append(blob.pathname)
        if not paths:
            raise CrdsError("No files submitted.")
    

def clear_uploads(request, uploads):
    """Remove the basenames listed in `uploads` from the upload directory."""
    username = str(request.user)
    for filename in uploads:
        upload_delete(username, filename)

def upload_delete(username, filename):
    """Worker function for upload_delete."""
    ingest_path = get_ingest_path(username, filename)
    with log.error_on_exception("Failed upload_delete for:", srepr(filename)):
        log.info("upload_delete", srepr(ingest_path))
        pysh.sh("rm -f ${ingest_path}")   # secure,  constructed path

def get_ingest_path(username, filename):
    """Return the file ingest path associated with `username` and basename `filename`."""
    assert re.match("[A-Za-z0-9_]+", username), "Invalid file_local_dir " + srepr(username)
    ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, username, filename)
    return ingest_path

