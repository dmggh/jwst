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
8. File final
"""
import sys
import os
import os.path
import re
import traceback
import tarfile
import glob
import json
import time
import fnmatch
import ast
import tempfile

# ===========================================================================

# from django.http import HttpResponse
from django.template import loader, RequestContext
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect
import django.utils.safestring as safestring
import django.utils
from django.utils.html import conditional_escape
from django.urls import reverse

import django.contrib.auth
import django.contrib.auth.models
from django.contrib.auth.decorators import login_required as login_required
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth.views import login as django_login

# ===========================================================================

from astropy.io import fits as pyfits

# ===========================================================================

import crds
from crds import uses, matches, data_file
from crds import CrdsError
from crds.core import (rmap, utils, timestamp, log, config, python23)
from crds.core import (pysh, heavy_client)
from crds.certify import reftypes

# ===========================================================================

from crds.server.jpoll import views as jpoll_views
from crds.server.jsonapi import views as jsonapi_views
from crds.server import settings
from crds.server import config as sconfig

# ===========================================================================

from . import (models, web_certify, web_difference, submit, versions, locks, html, mail)
from . import common
from . import catalog_fusion
from . import browsify_file
from .templatetags import stdtags
from .models import FieldError, MissingInputError
from .common import capture_output, srepr, profile, complete_re, crds_format_html

HERE = os.path.dirname(__file__) or "./"

# ===========================================================================

@profile("submit_confirm_post.stats")
@error_trap("base.html")
@log_view
# @login_required  (since this drops and re-acquires lock,  don't use.)
@group_required("file_submission")
@instrument_lock_required  # ensures authenticated,  has instrument lock of submission.
def submit_confirm(request): #, button, results_id):
    """Accept or discard proposed files from various file upload and
    generation mechanisms.
    """
    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    submitter = SubmitConfirm(request)
    
    new_result = submitter.process(request)

    with log.error_on_exception(
            "Failed logging and/or releasing lockss after confirm/cancel/force."):
        # instrument = locks.instrument_of(str(request.user))
        # locks.release_locks(name=instrument, type="instrument")
        django.contrib.auth.logout(request)
    
    return redirect_jpoll_result(new_result, jpoll_handler)



# ===========================================================================

class SubmitConfirm:
    """Check submission confirmation inputs and verify instrument locking 
    relative to `request` and prior submission results.  Store various parameters 
    as attributes for later use during the confirm/cancel.
    """
    def __init__(self, request):
        # don't rely on locking mechanisms to verify this since @login_required is turned off
        # and locking may change.
        if not request.user.is_authenticated:
            raise CrdsError("You must be logged in to confirm or cancel file submissions.")

        button = validate(request, "button", "confirm|cancel|force")
        self.disposition = button + "d" if button.endswith("e") else button + "ed"
        results_id = validate(request, "results_id", common.UUID_RE)
        
        try:
            self.repeatable_model = models.RepeatableResultBlob.load(results_id)
        except Exception as exc:
            raise CrdsError("Error fetching result: " + results_id + " : " + str(exc))        
        if self.repeatable_model.parameters.get("disposition", None):
            raise CrdsError("This submission was already confirmed or cancelled.")

        self.result = self.repeatable_model.parameters
        self._check_locking(request, self.result)

        # Mark the READY model as finalizing to prevent double confirmations,  must save now.
        self.repeatable_model.set_par("disposition", "finalizing")
        self.repeatable_model.save()
    
    def _check_locking(self, request, result):
        self.instrument_lock_id = get_instrument_lock_id(request)
        should_still_be_locked = result.get("should_still_be_locked", None) 
        self.locked_instrument = locks.instrument_from_lock_id(should_still_be_locked)
        username = str(request.user)
        if self.disposition == "confirmed":
            assert username == result.user, \
                "User mismatch: file Submitter='%s' and Confirmer='%s' don't match." % (username, result.user)
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

    @property
    def confirmed(self):
        return self.disposition in ["confirmed", "forced"]

    @property    
    def new_file_map(self):
        return dict(self.result.new_file_map)
    
    @property
    def new_files(self):
        return list(self.new_file_map.values())
    
    def process(self, request):
        if submitter.confirmed:
            confirm_results = submitter.confirm_files(request)
        else:
            confirm_results = submitter.cancel_files(new_files)
    
        new_result = submitter.common_reply(request, confirm_results)
        return new_result

    def confirm_files(self):
        final_pmap, context_map, collision_list = submit.submit_confirm_core(
            confirmed, submitter.result.submission_kind, self.result.description,
            new_files, submitter.result.context_rmaps, self.result.user,
            submitter.result.pmap, submitter.result.pmap_mode)
        
    def submit_confirm_core(submission_kind, description, new_files, context_rmaps, user, pmap_name, pmap_mode):
        """Handle the confirm/cancel decision of a file submission.  If context_rmaps is not [],  then it's a list
        of .rmaps from which to generate new contexts.   
        """
        paths, instrument, filekind = check_new_files(new_files, user)
        if context_rmaps:
            # Instrument lock required since we're generating a new .imap from context_rmaps.
            # locks.verify_instrument_locked_files(user, instrument_lock_id, paths, blob.observatory)
            # context_rmaps aren't necessarily in new_file_map and may be existing files.  So they only
            # specify changes to `pmap_name`,  not file deliveries.
            submission = FileSubmission(
                self.result.pmap, uploaded_files=None, description=self.result.description, 
                user=self.result.user, creator="crds", pmap_mode=self.result.pmap_mode)
            final_pmap, context_map = submission.do_create_contexts(self.result.context_rmaps)
            delivered_files = sorted(new_files + list(context_map.values()))
        else:
            delivered_files = new_files
            pmaps = [ os.path.basename(name) for name in new_files if name.endswith(".pmap") ]
            if pmaps:  # when no context generation was done,  choose highest .pmap,  if any
                new_pmap = sorted(pmaps)[-1]
                models.set_default_context(new_pmap)
            final_pmap = None
            context_map = {}
            
        delivery = submit.Delivery(user, delivered_files, self.result.description, self.result.submission_kind, 
                                   related_files=related_files)
        delivery.deliver()
        
        collision_list = get_collision_list(list(context_map.values()))        

        # XXX single model save later in processing flow    
        self.repeatable_model.set_par("original_pmap", self.result.pmap)
        self.repeatable_model.set_par("pmap", final_pmap)

        confirm_results = affirm_files(self.result, self.new_file_map, context_map, collision_list)

        return confirm_results, final_pmap, context_map, collision_list    

    def cancel_files(self):
        """Wipe out any database + file system representation of `new_files` and return empty template params."""
        for new in self.new_files:
            with log.error_on_exception("Failed marking", repr(new), "as cancelled."):
                blob = models.FileBlob.load(new)
                blob.destroy()
        confirm_results = dict(
            uploaded_files = [],
            generated_files = [],
            added_files = [],
            deleted_files = [],
            )
        # confirm_results, final_pmap, context_map, collision_list
        return confirm_results, None, {}, None

    def common_reply(self, request, confirm_results):
        # Update the "READY" model with the results of this confirmation to prevent repeat confirms
        self.repeatable_model.set_par("disposition" , self.disposition)
        self.repeatable_model.save()  # XXX required by further set_par() above
    
        # Add info common to both confirmed and canceled
        confirm_results["disposition"] = self.disposition
        confirm_results["confirmed"] = self.confirmed
        confirm_results["description"] = self.repeatable_model.parameters["description"]
        confirm_results["prior_results_url"] = self.repeatable_model.abs_repeatable_url
        
        # Do the web response
        new_result = render_repeatable_result(request, "confirmed.html", confirm_results)
    
        """Issue and e-mail indicating confirm/cancel with details from the submission."""
        username = request.user.first_name + " " + request.user.last_name
        results_kind = self.repeatable_model.parameters["submission_kind"].title()
        mail.crds_notification(
            body = mail.GENERIC_CONFIRMED_BODY, status=self.disposition.upper(),
            username = username, user_email = request.user.email, 
            results_kind = results_kind,
            repeatable_url = new_result.abs_repeatable_url,
            to_addresses  = sconfig.CRDS_STATUS_CONFIRM_ADDRESSES,
            **confirm_results)
        return new_result
    
# ===========================================================================

def affirm_files(result, new_file_map, context_map, collision_list):
    """Return template variables appropriate for confirming this submission. Clear upload dir.  Clear models cache."""
    
    new_file_map = sorted(list(new_file_map.items()) + list(context_map.items()))
    generated_files = sorted([(old, new) for (old, new) in new_file_map if old not in result.uploaded_basenames])
    uploaded_files = [(old, new) for (old, new) in new_file_map if (old, new) not in generated_files]
    
    # rmaps specified for context generation but not uploaded or generated
    context_rmaps = [filename for filename in self.result.context_rmaps
        if filename not in list(dict(generated_files).values()) + self.result.uploaded_basenames]

    clear_uploads(request, self.result.uploaded_basenames)

    models.clear_cache()
    
    confirm_results = dict(
        pmap_mode = result.pmap_mode,
        pmap = result.pmap,
        original_pmap = result.original_pmap,
        uploaded_files=uploaded_files,
        added_files=getattr(self.result, "added_files", []),
        deleted_files=getattr(self.result, "deleted_files", []),
        context_rmaps=context_rmaps,
        generated_files=generated_files,
        new_file_map=new_file_map,
        collision_list=collision_list,
        more_submits=result.more_submits)

    return confirm_results

# ===========================================================================
        
def check_new_files(new_files, user):
    """Verify that each filename in `new_files`:
    1. Exists in CRDS in the uploaded state.
    2. Was delivered by `user` name.
    3. Resulting list of CRDS file paths is not an empty list.
    
    Returns   list of cache paths,  instrument name, filekind name
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
    return paths, instrument, filekind
    
def destroy_file_list(files):
    """Remove the database record of `files` as well as `files` themselves.
    NOTE: This only removes the CRDS official copy of the file, not the original upload copy.
    """
    for filename in files:
        blob = models.FileBlob.load(filename)
        blob.destroy()


