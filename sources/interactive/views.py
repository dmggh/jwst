"""This module defines the Django view functions which respond to HTTP requests
and return HTTP response objects.
"""
import os.path
import re
import tarfile
import glob
import json
import fnmatch
import ast
import io

# ===========================================================================

# from django.http import HttpResponse
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

import django.contrib.auth.models
from django.contrib.auth.decorators import login_required as login_required
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth.views import login as django_login

# ===========================================================================

import crds
from crds import uses, matches, data_file
from crds import CrdsError
from crds.core import (rmap, utils, timestamp, log, config)
from crds.core import (pysh, heavy_client)
from crds.certify import reftypes

# ===========================================================================

from ..jpoll import views as jpoll_views
from ..jsonapi import views as jsonapi_views
from .. import settings
from .. import config as sconfig

from . import confirm
from .render import crds_render
from .render import redirect_repeatable_result
from .render import redirect_jpoll_result
from .render import render_repeatable_result

# ===========================================================================

from . import (models, web_certify, web_difference, submit, versions, locks, mail)
from . import common
from . import catalog_fusion
from . import browsify_file
from . import render
from .templatetags import stdtags
from .common import FieldError, MissingInputError
from .common import capture_output, srepr, complete_re
from .common import validate, crds_format_html
from .common import profile, log_view  # view wrappers

HERE = os.path.dirname(__file__) or "./"

# ===========================================================================

def error_trap(template):
    """error_trap() is a 'decorator maker' which returns a decorator which
    traps exceptions in views and re-issues the input `template` with an
    appropriate error message so the user can try again.
    """
    def decorator(func):
        """decorator is bound to the template parameter of error_trap()."""
        def trap(request, *args, **keys):
            """trap() is bound to the func parameter of decorator()."""
            try:
                return func(request, *args, **keys)
            except (AssertionError, CrdsError, FieldError) as exc:
                msg = crds_format_html("ERROR: " + str(exc))
            # Generic exception handler,  undescriptive,  to prevent server probing via errors
            except Exception as exc:
                msg = crds_format_html("ERROR: internal server error")
            pars = dict(list(keys.items()) + [("error_message", msg)])
            return render.crds_render(request, template, pars, requires_pmaps=True)
        trap.__name__ = func.__name__
        return trap
    return decorator

def get_or_post(request, variable):
    """Return `variable` wherever it is defined in request, GET or POST."""
    return (variable in request.POST and request.POST[variable]) or \
           (variable in request.GET  and request.GET[variable])

def checkbox(request, variable):
    """Return the boolean value of checkbox `variable` with <input> in standard idiom."""
    val = get_or_post(request, variable)
    return interpret_checkbox(val)

def interpret_checkbox(val):
    """Convert checkbox value string into bool."""
    if val in ["False","false","FALSE","0","0.0","F","",0,None,0.0]:
        return False
    else:
        return True

def parse_date(datestr):
    """Validate a `datestr` form input and return it as a datetime."""
    assert len(datestr) < 100,  "Date input string is too long."
    return "*" if datestr in ["*", ""] else timestamp.parse_date(datestr)

# ===========================================================================

# "pattern" functions for validate_post/get

def is_pmap(filename):
    """Verify that `filename` names a known CRDS pipeline mapping.
    Otherwise raise AssertionError.
    """
    try:
        return is_mapping(filename, r"\.pmap")
    except Exception as exc:
        raise CrdsError("Invalid pmap: " + str(exc))

def is_imap(filename):
    """Verify that `filename` names a known CRDS instrument mapping.
    Otherwise raise AssertionError.
    """
    return is_mapping(filename, r"\.imap")

def is_rmap(filename):
    """Verify that `filename` names a known CRDS reference mapping.
    Otherwise raise AssertionError.
    """
    return is_mapping(filename, r"\.rmap")

def is_pmap_or_imap(filename):
    """Verify that `filename` names a known CRDS instrument or pipeline
    mapping and return it.   Otherwise,  AssertionError.
    """
    return is_mapping(filename, r"\.[ip]map")

def is_mapping(filename, extension=r"\.[pir]map"):
    """Verify that `filename` names a known CRDS mapping.
    Otherwise raise AssertionError.
    """
    if not re.match(complete_re(r"[A-Za-z0-9_]+" + extension), filename):
        raise CrdsError("Invalid mapping filename " + srepr(filename))
    is_known_file(filename)
    return filename

def is_reference(filename, extension=r"\.fits|\.r\dh|\.r\dd"):
    """Verify that `filename` names a known CRDS reference file.
    Otherwise raise AssertionError.
    """
    if not re.match(complete_re(r"\w+" + extension), filename):
        raise CrdsError("Invalid reference filename " + srepr(filename))
    is_known_file(filename)
    return filename

def is_known_file(filename):
    """Verify that `filename` identifies a file already known to CRDS and
    has progressed beyond the 'uploaded' temporary file stage.
    """
    config.check_filename(filename)
    try:
        _blob = models.FileBlob.load(filename)
    except LookupError:
        raise CrdsError("No database entry for " + srepr(filename) + ".")
#    assert blob.state != "uploaded", \
#        "File " + srepr(filename) + " has not yet been submitted."
    return filename

def is_known_file_list(text):
    """Break up a string of whitespace or comma seperated filenames into a list of files,
    verifying that the files exist in CRDS.
    """
    files = text.replace(","," ").split()
    for file_ in files:
        is_known_file(file_)
    return files

def is_available_file_blob(filename):
    """Verify that `filename` identifies a file already known to CRDS and
    meets any requirements for distribution.   Return its blob.
    """
    # replicates most of is_known_file because blob is required.
    config.check_filename(filename)
    try:
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise CrdsError("No database entry for " + srepr(filename) + ".")
    assert blob.available, \
        "File " + srepr(filename) + " is not yet available.   Files must be successfully delivered to the archive before operational use."
    return blob

def is_available_file(filename):
    """Verify that `filename` identifies a file already known to CRDS and
    meets any requirements for distribution.   Return the filename.
    """
    _blob = is_available_file_blob(filename)
    return filename

def is_list_of_rmaps(text):
    """Assert that `text` contains a list of comma for newline separated rmap
    names.
    """
    text = str(text)
    text = text.replace("\n"," ")
    text = text.replace("\r", "")
    text = " ".join(text.split(","))
    rmaps = [r.strip() for r in text.split()]
    for rmp in rmaps:
        try:
            is_rmap(rmp)
        except Exception:
            assert rmp.endswith("n/a")
    return rmaps

def is_match_tuple(tuple_str):
    """Raise an AssertionError if `tuple_str` is does not literal eval to a
    tuple.  Otherwise return the tuple.
    """
    try:
        tup = ast.literal_eval(tuple_str.upper())
        assert isinstance(tup, tuple), "Enter a tuple to match against."
    except Exception:
        raise AssertionError("Enter a tuple to match against.")
    return tup

def get_observatory(request):
    """Validate and return the observatory parameter from request.POST"""
    return validate(request, "observatory", models.OBSERVATORIES)

# ===========================================================================

def handle_known_or_uploaded_file(request, modevar, knownvar, uploadvar):
    """Process file variables for a file which is either known to CRDS
    and simply named,  or which is uploaded by the user.

    Return (uploaded_flag, name_on_users_system,  temporary_file_path)
    """
    must_delete = False
    if request.POST[modevar] == knownvar:
        # certified_file is a basename,  but CRDS figures out where it is.
        original_name = validate(request, knownvar, is_known_file)
        filepath = get_known_filepath(original_name)
    else:
        assert request.user.is_authenticated, \
            "file uploads are only available for authenticated users."
        ufile = get_uploaded_file(request, uploadvar)
        filepath = ufile.temporary_file_path()
        original_name = ufile.name
        # Kludge the temporary file extension to match the original filename.
        # This enables code which identifies type by extension to work.
        if os.path.splitext(filepath)[-1] != os.path.splitext(original_name)[-1]:
            filepath, filepath_old = os.path.splitext(filepath)[0] + os.path.splitext(original_name)[-1], filepath
            os.rename(filepath_old, filepath)
            must_delete = True
    return must_delete, str(original_name), str(filepath)

def handle_upload_delete(must_delete, orig, path):
    """Delete uploaded file at `path` originally named `orig` IFF `must_delete`."""
    if must_delete:
        with log.warn_on_exception("Failed deleting uploaded temporary", repr(orig), "at", repr(path)):
            os.remove(path)

def get_uploaded_file(request, formvar):
    """Return the DJango UploadedFile associated with `request` and `formvar`,
    screening the original filename for legality.  Handles
    <input type='file'>, part 1.
    """
    assert request.user.is_authenticated, \
        "file uploads are only available for authenticated users."
    try:
        ufile = request.FILES[formvar]
    except KeyError:
        raise MissingInputError("Specify a file to upload for " + srepr(formvar))
    config.check_filename(ufile.name)
    return ufile

def get_files(request):
    """Obtain uploaded files from a common multi-mode form mechanism,
    returning:   remove_dir,   { original_name : file_path }
    """
    path = os.path.join(sconfig.CRDS_INGEST_DIR, str(request.user))
    uploads = { str(os.path.basename(file_)) : str(file_) for file_ in glob.glob(path + "/*") }
    log.info("Scanned", srepr(path), "for uploaded files:", uploads)
    for file_ in uploads:
        if rmap.is_mapping(file_):
            # this will fail for user-scp'ed ingests.  but... maybe file already writeable.
            with log.warn_on_exception("Failed setting file mode on", repr(file_)):
                os.chmod(uploads[file_], 0o660)
    if not uploads:
        raise CrdsError("No input files were specified.")
    return path, uploads

def get_known_filepath(filename):
    """Given the basename of a mapping or reference file, `file`,
    determine the full path of the file on the server.
    """
    try:
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise FieldError("CRDS doesn't know about file " + srepr(filename))
    return blob.pathname

def get_recent_or_user_mode_and_context(request):
    """Process standard request parameters for specifying context,  returning both the
    specification mode and the context itself.  edit and operational contexts may need
    to use quasi-lazy evaluation and be reevaluated later in case someone else submitted.
    """
    pmap_mode = validate(
            request, "pmap_mode", "pmap_menu|pmap_text|pmap_edit|pmap_operational")
    if pmap_mode == "pmap_edit":
        context = models.get_default_context(models.OBSERVATORY, "edit")
    elif pmap_mode == "pmap_operational":
        context = models.get_default_context(models.OBSERVATORY, "operational")
    else:
        context = validate(request, pmap_mode, is_pmap)
    return pmap_mode, str(context)

def get_recent_or_user_context(request):
    """Process standard request parameters for specifying context."""
    return get_recent_or_user_mode_and_context(request)[1]

# ===========================================================================

class ServerError(Exception):
    """Uncaught exception which will be returned as HTTP 500"""

# ===========================================================================
# ===========================================================================
# ===========================================================================
# Authentication and locking strategy:
#
# 1. File submission views require an authenticated user
#
# 2. As part of login,  an instrument is reserved to that user,  and only they can submit for it.
# This part is triggered by the user_logged_in signal which allocates database based locks for that
# instrument and user.
#
# 3. Database-based locks are refreshed whenever the session is refreshed.
# This is achieved by providing lock refreshing middleware.  Any interactive use of the site causes refresh.
#
# 4. Both Sessions and locks expire 4 hours after the last access by the logged in user.
#
# 5. Logging out releases locks owned by a user.
#
#
# There are two ways for a session to expire:
# a. The session clock runs out and it expires.
# b. The user logs out.

def superuser_login_required(func):
    """Decorator to ensure login and check superuser flag."""
    @login_required
    def _inner(request, *args, **keys):
        """Decorated function to check superuser status."""
        if not request.user.is_superuser:
            raise CrdsError(str(request.user) + " is not a super user.")
        return func(request, *args, **keys)
    _inner.__name__ = func.__name__
    return _inner


def group_required(*group_names):
    """Requires user membership in at least one of the groups passed in."""
    def in_groups(u):
        if u.is_authenticated:
            if bool(u.groups.filter(name__in=group_names)) | u.is_superuser:
                return True
        return False
    return user_passes_test(in_groups)

# ===========================================================================
#
# Hooks for coordinating locks on instruments with logins,  ensuring they're
# obtained on login,  maintained across views, and eventually released on logout.
# Implemented as Django login/logout signal handlers and a view decorator.
#
# This is a kind of pessimistic locking,  where a user reserves a particular instrument
# for as long as they're logged in,  but guaranteeing that when it comes time to submit
# and confirm they've either still got a lock or they'll get notified they were booted.
# This is in contrast to the optimistic approach of getting all set to commit without
# locking and then finding out someone else has locked the instrument and is waiting
# to confirm for some reason...  or even has submitted their own copies of the same files.
#
# These signal handlers are called after a user is logged in or out to manage instrument locks.
#
# See also middleware.py which resets lock expiry for most interactive views

def lock_login_receiver(sender, **keys):
    """Signal handler to acquire locks for a user when they login."""
    request = keys["request"]
    user = str(keys["user"])

    with log.error_on_exception("Failed creating ingest directory."):
        ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, str(request.user))
        if not os.path.exists(ingest_path):
            log.info("Creating ingest directory for", repr(user))
            os.mkdir(ingest_path, 0o770)
        else:
            log.info("Ingest directory already exists for", repr(user))

    if "instrument" in request.POST:
        instrument = validate(request, "instrument", models.INSTRUMENTS + ["none"])
        if instrument != "none":
            if locks.get_request_lock(request):
                if locks.instrument_of(user) == instrument:
                    return
                else:
                    locks.release_locks(user=user)
            try:
                locks.acquire(user=user, type="instrument", name=instrument,
                              timeout=settings.CRDS_LOCK_ACQUIRE_TIMEOUT,
                              max_age=settings.CRDS_MAX_LOCK_AGE)
            except locks.ResourceLockedError:
                django.contrib.auth.logout(request)
                owner = locks.owner_of(name=instrument, type="instrument")
                raise CrdsError("User '%s' has already locked instrument '%s'." % (owner, instrument))
            except Exception as exc:
                django.contrib.auth.logout(request)
                log.error("Untrapped login locking exception:", repr(exc), ":", str(exc))
                raise

user_logged_in.connect(lock_login_receiver, dispatch_uid="lock_login_receiver")

def lock_logout_receiver(sender, **keys):
    """Signal handler to release a user's locks if they log out."""
    with log.info_on_exception("logout releasing locks failed"):
        # request = keys["request"]
        user = str(keys["user"])
        locks.release_locks(user=user)

user_logged_out.connect(lock_logout_receiver, dispatch_uid="lock_logout_receiver")

# @login_required
def lock_status(request, user=None):
    """AJAX view to return state of user lock."""
    status = locks.get_lock_status(type="instrument", 
                                   user=user or str(request.user))
    return HttpResponse(json.dumps(status), content_type='application/json')

def instrument_lock_required(func):
    """Decorator to ensure a user still owns an un-expired lock defined by their session data."""
    def _wrapped(request, *args, **keys):
        """instrument_log_required wrapper function."""
        assert request.user.is_authenticated, "You must log in."
        instrument = locks.get_instrument_lock_id(request)
        if not (instrument or request.user.is_superuser):
            raise CrdsError("You can't access this function without logging in for a particular instrument.")
        return func(request, *args, **keys)
    _wrapped.__name__ = func.__name__
    return _wrapped

# ===========================================================================

@profile("index.stats")
@error_trap("base.html")
@log_view
def index(request):
    """Return the top level page for all of interactive CRDS."""
    pars = get_context_table_parameters("operational")
    pars["history"], pars["history_tuples"] = get_context_history_variables(4)
    pars["include_diff"] = False
    pars["remote_contexts"] = models.RemoteContextModel.objects.all()
    response = crds_render(request, "index.html", pars, requires_pmaps=True)
    # The following is necessary because the index page doesn't change suffiently between context
    # page reloads even when no updates are occuring.
    response['Cache-Control'] = "no-cache"
    return response

# ===========================================================================

@error_trap("base.html")
@log_view
def display_result(request, results_id):
    """Render the repeatable result with `results_id`.  Handle the /display_result/ URL.
    Although it does not directly require login,  this view enforces the .authentication_required
    attribute of repeatable results.
    """
    try:
        result = models.RepeatableResultBlob.load(results_id)
    except Exception as exc:
        raise CrdsError("Error loading result", results_id, ":", str(exc))
    pars = result.parameters
    if pars.get("requires_authentication", False) and not request.user.is_authenticated:
        CrdsError("You must be logged in to view this page.")
    pars["results_id"] = results_id  # needed to implement "disposition", confirmed or cancelled.
    return crds_render(request, result.page_template, pars)

@error_trap("base.html")
@log_view
@login_required    # THIS is the whole point of this view.
def authenticated_result(request, results_id):
    """Render the repeatable result with `results_id`.  Handle the /display_result/ URL
    This view is used to transparently login,  not verify authentication.
    ."""
    return display_result(request, results_id)


# ===========================================================================

@error_trap("base.html")
@log_view
def docs(request, page):
    """Render the specified documentation template.  Munge it up a little with the secret .crds suffix to
    keep clever people from rendering arbitrary templates found somewhere in the Django ecosphere.
    """
    return crds_render(request, page + ".crds.html")

# ===========================================================================
# @profile("login.stats")
@error_trap("base.html")
# @log_view   XXX security,  expose password?
def login(request):
    """CRDS login view function,  sets and tests session cookie."""
    extras = dict(
        observatory = models.OBSERVATORY,
        instruments = models.INSTRUMENTS + ["none"],
        server_usecase = sconfig.server_usecase.lower())
    return django_login(request, "registration/login.html", extra_context=extras)


@log_view
@login_required
def logout(request):
    """View to get rid of authentication state and become nobody again."""
    django.contrib.auth.logout(request)
    return redirect("/") # secure

@error_trap("set_password.html")
# @log_view    XXX security,  expose password?
@login_required
def set_password(request):
    """Support changing a user's own password."""
    if request.method == "POST":
        if request.user.is_superuser:
            username = validate(request, "username", "[A-Za-z_0-9]+")
            try:
                user = django.contrib.auth.models.User.objects.get(username=username)
            except Exception:
                raise CrdsError("Unknown user.")
        else:
            old_password =  validate(request, "old_password", ".+")
            user = django.contrib.auth.authenticate(username=str(request.user), password=old_password)
            assert user is not None, "Old password is not valid."
        new_password1 = validate(request, "new_password1", ".+")
        new_password2 = validate(request, "new_password2", ".+")
        assert new_password1 == new_password2, "New passwords are not the same."
        assert len(new_password1) >= 6, "At least 6 characters please."
        if not request.user.is_superuser:
            assert re.match(complete_re(r".*\d.*"), new_password1),  "At least one digit please."
            assert re.match(complete_re(r".*[a-zA-Z].*"), new_password1),  "At least one letter please."
        user.set_password(new_password1)
        user.save()
        return crds_render(request, "set_password_results.html")
    else:
        return crds_render(request, "set_password.html")

# ===========================================================================

# The following code is derived from django-jquery-file-upload

# Fileupload is a Django port of a jQuery project from here:
# https://github.com/sigurdga/django-jquery-file-upload

def response_content_type(request):
    """Return the content_type string associated with `request`."""
    if "application/json" in request.META['HTTP_ACCEPT']:
        return "application/json"
    else:
        return "text/plain"

class JSONResponse(HttpResponse):
    """JSON response class."""
    def __init__(self, obj='', json_opts={}, content_type="application/json", *args, **kwargs):
        content = json.dumps(obj, **json_opts)
        super(JSONResponse, self).__init__(content, content_type, *args, **kwargs)
        self['Content-Disposition'] = 'inline; filename=files.json'

@error_trap("base.html")
@log_view
@login_required
def upload_new(request, template="upload_new_input.html"):
    """Support adding new files to the upload area for django-file-upload."""
    if request.method == "GET":
        return HttpResponseRedirect('/upload/list/')  # secure
    else:
        return upload_new_post(request)

def upload_new_post(request):
    """Handle a POST to the new file upload of django-file-upload."""

    file_ = get_uploaded_file(request, 'files')
    upload_path = file_.temporary_file_path()
    filename = file_.name
    config.check_filename(filename)    
    username = str(request.user)
    ingest_path = confirm.get_ingest_path(username, filename)

    link_upload_to_ingest(upload_path, ingest_path)  # must secure ingest_path
    
    data = {"files" : [json_file_details(filename, upload_path)] }
    return JSONResponse(data, {}, response_content_type(request))

def link_upload_to_ingest(upload_path, ingest_path):
    """Remove any file or directory at `ingest_path` and then make a hard link
    from `upload_path` to `ingest_path`.
    """
    with log.verbose_on_exception("Failed removing", repr(ingest_path)):
        pysh.sh("rm -f ${ingest_path}")   #  secure, constructed path
        log.info("Removed existing", repr(ingest_path))
    utils.ensure_dir_exists(ingest_path, mode=0o770)
    log.info("Linking", upload_path, "to", ingest_path)
    os.link(upload_path, ingest_path)

def json_file_details(filename, upload_path):
    """Return a dictionary of details about `filename` at `upload_path` for django-file-upload."""
    return {'name': filename,
            'size' : os.stat(upload_path).st_size,
            'deleteUrl': reverse('upload-delete', args=[filename]),
            'deleteType': "DELETE"}

@error_trap("base.html")
@log_view
@login_required
def upload_list(request, _template="upload_new_input.html"):
    """Return JSON describing files in the upload area."""

    username = str(request.user)
    ingest_glob = confirm.get_ingest_path(username, "*")

    try:
        ingest_paths = { os.path.basename(f):f for f in glob.glob(ingest_glob) }
        log.info("Listing existing ingest files", repr(ingest_paths))
    except Exception:
        ingest_paths = []
        log.info("Failed globbing ingest files.")

    data = {"files" : [ json_file_details(name, ingest_paths[name]) for name in ingest_paths ] }
    return JSONResponse(data, {}, response_content_type(request))

@error_trap("base.html")
@log_view
@login_required
def upload_delete(request, filename):
    """Manage AJAX file deletes for django-file-upload multifile upload interface."""
    config.check_filename(filename)
    username = str(request.user)

    confirm.upload_delete(username, filename)

    if request.is_ajax():
        return JSONResponse(True, {}, response_content_type(request))
    else:
        return HttpResponseRedirect('/upload/new/')  # secure


# ===========================================================================
'''
@error_trap("upload_alt_new.html")
@log_view
@login_required
def upload_alt_new(request, template="upload_alt_new.html"):
    """Support adding new files to the upload area."""
    if request.method == "GET":
        return crds_render(request, template)
    else:
        file_ = get_uploaded_file(request, 'file')
        file_local_dir = str(request.user)
        config.check_filename(file_.name)
        assert re.match("[A-Za-z0-9_]+", file_local_dir), "Invalid file_local_dir " + srepr(file_local_dir)
        ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, file_local_dir, file_.name)
        with log.verbose_on_exception("Failed removing", repr(ingest_path)):
            pysh.sh("rm -f ${ingest_path}")   #  secure, constructed path
            log.info("Removed existing", repr(ingest_path))
        utils.ensure_dir_exists(ingest_path, mode=0770)
        log.info("Linking", file_.temporary_file_path(), "to", ingest_path)
        os.link(file_.temporary_file_path(), ingest_path)
        data = [json_file_details(file_.name, file_.temporary_file_path())]
        response = JSONResponse(data, {}, response_content_type(request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response
'''

# ===========================================================================

@error_trap("bestrefs_dataset_input.html")
@log_view
def bestrefs(request):
    """View to get the instrument context for best references."""
    if request.method == "GET":
        return crds_render(request, "bestrefs_dataset_input.html",
                {
                 "pmap_initial_mode" : "operational",
                }, requires_pmaps=True)
    else:
        return bestrefs_post(request)

@profile("dataset_bestrefs.stats")
def bestrefs_post(request):
    """View to get best reference dataset parameters."""
    context = get_recent_or_user_context(request)
    pmap = crds.get_symbolic_mapping(context)
    dataset_mode = validate(
        request, "dataset_mode", "dataset_archive|dataset_uploaded|dataset_local")
    if dataset_mode == "dataset_uploaded":
        uploaded_file = get_uploaded_file(request, "dataset_uploaded")
        dataset_name = uploaded_file.name
    elif dataset_mode == "dataset_local":
        dataset_name = "Uploaded-Dataset-Header"
    elif dataset_mode == "dataset_archive":
        dataset_name = validate(request, "dataset_archive", common.DATASET_ID_RE)
    with log.augment_exception("Problem getting dataset parameters for", srepr(dataset_name)):
        # exception_class=CrdsError):
        if dataset_mode == "dataset_uploaded":
            dataset_path = uploaded_file.temporary_file_path()
            header = data_file.get_free_header(dataset_path, original_name=dataset_name)
            header = utils.condition_header(header)
        elif dataset_mode == "dataset_local":
            inputs = validate(request, "dataset_local", ".+")
            header = header_string_to_header(inputs)
        elif dataset_mode == "dataset_archive":
            # If dataset is an association,  it will return multiple headers,  just show one.
            headers = jsonapi_views.get_simplified_dataset_headers_by_id(context, [dataset_name])
            first = sorted(headers.keys())[0]
            header = headers[first]
        if isinstance(header, str):
            raise CrdsError(header)

    # base on the context and datset,  compute best references
    results = bestrefs_results(request, pmap, header, dataset_name)

    log.info("Best Refs Results:", log.PP(results))

    return results

def header_string_to_header(hstring):
    """Convert a string representing a FITS header into a dictionary, screening
    for illegal keys or values.
    """
    try:
        return _dict_header_format(hstring)
    except Exception:
        return _simple_header_format(hstring)

def _dict_header_format(hstring):
    """Enable users to cut-and-paste CRDS header dump dictionaries."""
    hstring = re.sub(r" \[" + common.FITS_KEY_RE_STR + r"\]'", r"'", hstring)
    log.info("_dict_header_format revised inputs:", repr(hstring))
    header = ast.literal_eval(hstring)
    for (key, value) in list(header.items()):
        value = utils.condition_value(value)
        if not common.FITS_KEY_RE.match(key) and common.FITS_VAL_RE.match(value):
            log.warning("Dropping illegal keyword '%s' with value '%s'." % (key, value))
            continue
        header[key] = value
    return header
        
def _simple_header_format(hstring):
    """Enable simple line based header format where each line is of the form: <key> <value>
    """
    header = {}
    for line in io.StringIO(str(hstring)):
        words = line.strip().split()
        if not words:
            continue
        key = words[0]
        value = " ".join(words[1:])
        value = utils.condition_value(value)
        if not common.FITS_KEY_RE.match(key) and common.FITS_VAL_RE.match(value):
            log.warning("Dropping illegal keyword '%s' with value '%s'." % (key, value))
            continue
        header[key] = value
    return header

def bestrefs_results(request, pmap, header, dataset_name=""):
    """Render best reference recommendations under context `pmap` for
    critical parameters dictionary `header`.
    """
    log.info("bestrefs_results matching header:", header)
    recommendations, bestrefs_debug_output = captured_bestrefs(pmap, header)
    old_recommendations = {}
    # with log.error_on_exception("Failed fetching old bestrefs"):
    #    header = { key.upper() : val.lower() for (key,val) in header.items() }
    #    old_recommendations = pmap.get_old_references(header)
    # organize and format results for HTML display
    header_min = pmap.minimize_header(header)
    header_min.pop("REFTYPE", None)
    header_items = sorted(header_min.items())
    bestrefs_items = get_bestrefs_items(recommendations)
    old_bestrefs_items = get_bestrefs_items(old_recommendations)
    defined = { key:val for (key,val) in old_bestrefs_items if val.lower() != "undefined" }
    instrument = pmap.get_instrument(header)
    imap = pmap.get_imap(instrument)
    rmap_names = { key.upper():val for (key,val) in imap.selector.items() }
    pars = {
        "observatory" : pmap.observatory,
        "context_name" : str(pmap.basename),
        "dataset_name" : dataset_name,
        "header_items" : header_items,
        "bestrefs_items" : bestrefs_items,
        "bestrefs_debug_output" : bestrefs_debug_output,
        "rmap_names" : rmap_names,
        }
    if defined:
        pars["old_bestrefs_items"] = old_bestrefs_items
    return crds_render(request, "bestrefs_results.html", pars)

def get_bestrefs_items(recommendations):
    bestrefs_items = []
    for key, val in sorted(recommendations.items()):
        if isinstance(val, str) and val.startswith("NOT FOUND"):
            val = val[len("NOT FOUND "):].strip()
        match = re.match(r"^(.ref\$)(.*)$", val)
        if match:
            val = match.group(2)
        if val.startswith("crds://"):
            val = val[len("crds://"):]
        bestrefs_items.append((key.upper(), val.lower()))
    return bestrefs_items

# XXXX non-reentrant,  not safe for threaded servers,  process model only.
# 99%,  it will work anyway.  Failing would depend on concurrent web bestrefs.
@common.capture_output
def captured_bestrefs(pmap, header):
    """Run bestrefs in verbose mode capturing debug output.
    Return (bestrefs_dict,  captured_debug_output)
    """
    old = log.set_verbose(60)  # problem here.
    try:
        recommendations = heavy_client.getrecommendations(
            header, context=pmap.name, observatory=pmap.observatory)
        # recommendations = rmap.get_best_references(pmap, header)
    finally:
        log.set_verbose(old)
    return recommendations

# ===========================================================================

@error_trap("bestrefs_explore_index.html")
@log_view
def bestrefs_explore(request):
    """View to get the instrument context for best references."""
    if request.method == "GET":
        return crds_render(request, "bestrefs_explore_index.html", {
                    "pmap_initial_mode" : "operational",
                    "instruments" : models.INSTRUMENTS,
                }, requires_pmaps=True)
    else:
        return bestrefs_explore_post(request)

@profile("bestrefs_explore.stats")
def bestrefs_explore_post(request):
    """View to get best reference dataset parameters."""
    context = get_recent_or_user_context(request)
    pmap = crds.get_symbolic_mapping(context)
    instrument = validate(request, "instrument", models.INSTRUMENTS)
    valid_values = dict(pmap.get_imap(instrument).get_parkey_map())
    for key, values in list(valid_values.items()):
        if values == ["N/A"]:
            values = []
        if "CORR" not in key:
            if values and "*" not in values:
                values = values + ["*"]
            if values and "N/A" not in values:
                values = values + ["N/A"]
        valid_values[key] = values
    dateobs, timeobs = timestamp.now().split()
    timeobs = timeobs.split(".")[0]
    return crds_render(request, "bestrefs_explore_input.html", {
            "mapping" : pmap,
            "valid_values" : sorted(valid_values.items()),
            "instrument":instrument,
            "dateobs" : dateobs,
            "timeobs" : timeobs,
        })

VALID_PARAMETER_VALUE_CHARS = r"[A-Za-z0-9\+\-\.\/\*]*"

@error_trap("bestrefs_explore_input.html")
@log_view
def bestrefs_explore_compute(request):
    """Validate parameter inputs from the best refs explorer drop-down
    menus and render best reference recommendations.
    """
    context = validate(request, "context", is_pmap)
    instrument = validate(request, "instrument", models.INSTRUMENTS)
    pmap = crds.get_symbolic_mapping(context)
    imap = pmap.get_imap(instrument)
    header = { pmap.instrument_key : instrument.upper() }
    pars = list(imap.get_parkey_map().keys())
    for par in pars:
        try:
            write_in =  validate(request, par + "_text", VALID_PARAMETER_VALUE_CHARS)
        except Exception:
            write_in = None
        if write_in:
            header[par] = write_in
        else:
            header[par] = utils.condition_value(
                validate(request, par, VALID_PARAMETER_VALUE_CHARS))
    header["DATE-OBS"] = validate(request, "DATE-OBS", timestamp.DATE_RE_STR)
    header["TIME-OBS"] = validate(request, "TIME-OBS", timestamp.TIME_RE_STR)
    return bestrefs_results(request, pmap, header, instrument)

# ===========================================================================

@error_trap("certify_input.html")
@log_view
@login_required
def certify_file(request):
    """View to return certify input form or process POST."""
    if request.method == "GET":
        return crds_render(request, "certify_input.html", requires_pmaps=True)
    else:
        return certify_post(request)

@profile("certify.stats")
def certify_post(request):
    """View fragment to process file certification POSTs."""

    context = get_recent_or_user_context(request)
    compare_old_reference = checkbox(request, "compare_old_reference")
    comparison_context = context if compare_old_reference else None
    _remove_dir, uploaded_files = get_files(request)

    all_files = models.get_fileblob_map()

    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    disposition, certify_results = web_certify.certify_file_list(list(uploaded_files.items()), context=comparison_context,
        compare_old_reference=compare_old_reference, push_status=jpoll_handler.write)

    if disposition != "bad files":
        blacklist_results = web_certify.get_blacklist_file_list(list(uploaded_files.items()), all_files=all_files)
    else:
        blacklist_results = []

    return redirect_repeatable_result(request, "certify_results.html", {
             "certify_results":certify_results,
             "blacklist_results":blacklist_results,
             },  jpoll_handler=jpoll_handler)

# ===========================================================================

@error_trap("base.html")
@log_view
@login_required
def monitor_process(request, process_key):
    """Return a page response to periodically monitor and display status for `process_key`."""
    request.session["jpoll_key"] = process_key
    return crds_render(request, "monitor_process.html", {
            "process_key" : process_key,
            })
    
# ===========================================================================

@error_trap("batch_submit_reference_input.html")
@log_view
@login_required
@group_required("file_submission")
@instrument_lock_required
def batch_submit_references(request,  extra_parameters={}, template=None):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        pars = {
            "compare_old_reference" : "checked",
        }
        pars.update(extra_parameters)
        template = template or "batch_submit_reference_input.html"
        return crds_render(request, template, pars, requires_pmaps=True)
    else:
        return batch_submit_references_post(request, extra_parameters, template)

@profile("batch_submit_post.stats")
def batch_submit_references_post(request, extra_parameters={}, template=None):

    template = template or "batch_submit_reference_results.html"

    """View fragment to process file batch reference submission POSTs."""
    # For the initial submission, pmap_name is predictive,  not definitive
    # It can change after confirmation if other subnmissions occured which
    # also generate it.   Batch submissions ALWAYS define this even if
    # they're not comparing to a prior context.
    pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    description = validate(request, "description", common.DESCRIPTION_RE)
    creator = validate(request, "creator", common.PERSON_RE)
    change_level = validate(request, "change_level", models.CHANGE_LEVELS)
    auto_rename = checkbox(request, "auto_rename")
    compare_old_reference = checkbox(request, "compare_old_reference")
    _remove_dir, uploaded_files = get_files(request)
    instrument_lock_id = locks.get_instrument_lock_id(request)

    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    simplified_uploads = [ name for (name, path) in list(uploaded_files.items()) ]

    username = request.user.first_name + " " + request.user.last_name
    results_kind = "Batch Submit"
    mail.crds_notification(body=mail.GENERIC_STARTED_BODY, status="STARTED",
            username=username, user_email=request.user.email, 
            uploaded_files = simplified_uploads, results_kind = results_kind,
            description = description, monitor_url=jpoll_handler.monitor_url)

    bsr = submit.BatchReferenceSubmission(pmap_name, uploaded_files, description,
        user=request.user, creator=creator, change_level=change_level,
        auto_rename=auto_rename, compare_old_reference=compare_old_reference,
        instrument_lock_id=instrument_lock_id, status_channel = jpoll_handler)

    disposition, new_references_map, new_mappings_map, reference_certs, mapping_certs, \
        mapping_diffs, collision_list = bsr.submit()

    # Map from old filenames to new filenames,  regardless of origin / purpose
    new_file_map = list(new_mappings_map.items()) + list(new_references_map.items())
    
    status = "READY" if not disposition else disposition.upper()

    bsr_results = {
                "pmap" : pmap_name,
                "pmap_mode" : pmap_mode,

                "new_file_map" : new_file_map,
                "uploaded_basenames" : list(uploaded_files.keys()),
                "submission_kind" : "batch submit",
                "title" : "Batch Reference Submit",
                "description" : description,
                "context_rmaps" : sorted(new_mappings_map.values()),

                "certify_results" : reference_certs + mapping_certs,
                "collision_list" : collision_list,

                "diff_results" : mapping_diffs,

                "should_still_be_locked" : instrument_lock_id,
                "requires_locking" : True,

                "more_submits" : "/batch_submit_references/",
                "disposition": disposition,
            }
    bsr_results.update(extra_parameters)

    result = render_repeatable_result(request, template, bsr_results)

    renamed_uploads = list(new_references_map.items())
    mail.crds_notification(body=mail.GENERIC_READY_BODY, status=status,
            username=username, user_email=request.user.email, 
            uploaded_files = renamed_uploads, results_kind = results_kind,
            description = description, repeatable_url=result.authenticated_url)
    
    return redirect_jpoll_result(result, jpoll_handler)

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
    button = validate(request, "button", "confirm|cancel|force")
    results_id = validate(request, "results_id", common.UUID_RE)

    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    confirmer = confirm.Confirm(request, button, results_id)
    
    new_result = confirmer.process(request)

    with log.error_on_exception(
            "Failed logging and/or releasing lockss after confirm/cancel/force."):
        django.contrib.auth.logout(request)
    
    return redirect_jpoll_result(new_result, jpoll_handler)

# ===========================================================================

@error_trap("delete_references_input.html")
@log_view
@instrument_lock_required
def delete_references(request):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        return crds_render(request, "delete_references_input.html", {
        }, requires_pmaps=True)
    else:
        return delete_references_post(request)

@profile("delete_references.stats")
def delete_references_post(request):
    """View fragment to process file delete references POSTs."""

    pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    description = validate(request, "description", common.DESCRIPTION_RE)

    deleted_files = validate(request, "deleted_files", is_known_file_list)
    uploaded_files = { fname:rmap.locate_file(fname, models.OBSERVATORY) for fname in deleted_files }

    instrument_lock_id = locks.get_instrument_lock_id(request)
    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    pmap = crds.get_symbolic_mapping(pmap_name)
    pmap_references = pmap.reference_names()
    for deleted in deleted_files:
        assert deleted in pmap_references, "File " + repr(deleted) + " does not appear in context " + repr(pmap.name)

    with log.error_on_exception("Failed Delete Existing STARTED e-mail"):
        simplified_uploads = [ name for (name, path) in list(uploaded_files.items()) ]
        results_kind = "Delete Existing"
        username = request.user.first_name + " " + request.user.last_name
        mail.crds_notification(
            body=mail.GENERIC_STARTED_BODY, status="STARTED",
            username=username, user_email=request.user.email, 
            uploaded_files = simplified_uploads, results_kind = results_kind,
            description = description, monitor_url=jpoll_handler.monitor_url)
        
    drs = submit.DeleteReferenceSubmission(pmap_name, uploaded_files, description,
        user=request.user, instrument_lock_id=instrument_lock_id, status_channel=jpoll_handler)
    disposition, new_mappings_map, mapping_certs, mapping_diffs, collision_list = drs.submit()

    del_results = {
                "pmap" : pmap_name,
                "pmap_mode" : pmap_mode,

                "new_file_map" : new_mappings_map,
                "uploaded_basenames" : [],
                "deleted_files" : deleted_files,
                "submission_kind" : "delete references",
                "title" : "Delete References",
                "description" : description,
                "context_rmaps" : sorted(new_mappings_map.values()),

                "certify_results" : mapping_certs,
                "diff_results" : mapping_diffs,

                "collision_list" : collision_list,

                "should_still_be_locked" : instrument_lock_id,
                "requires_locking" : True,
                "more_submits" : "/delete/reference/",
                "disposition": disposition,
            }

    result = render_repeatable_result(
        request, 'delete_references_results.html', del_results)

    with log.error_on_exception("Failed Delete Existing READY e-mail"):
        renamed_uploads = list(new_mappings_map.items())
        status = "READY" if not disposition else disposition.upper()
        mail.crds_notification(
            body=mail.GENERIC_READY_BODY, status=status,
            username=username, user_email=request.user.email, 
            uploaded_files = renamed_uploads, results_kind = results_kind,
            description = description, repeatable_url=result.authenticated_url)
        
    return redirect_jpoll_result(result, jpoll_handler)

# ===========================================================================

@error_trap("add_existing_references_input.html")
@log_view
@instrument_lock_required
def add_existing_references(request):
    """This view supports adding references which are already in CRDS to a context
    which doesn't contain them yet.
    """
    if request.method == "GET":
        return crds_render(request, "add_existing_references_input.html", {
        }, requires_pmaps=True)
    else:
        return add_existing_references_post(request)

@profile("add_existing_references.stats")
def add_existing_references_post(request):
    """View fragment to process add existing references form POSTs."""

    pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    description = validate(request, "description", common.DESCRIPTION_RE)

    added_files = validate(request, "added_files", is_known_file_list)
    uploaded_files = { fname:rmap.locate_file(fname, models.OBSERVATORY) for fname in added_files }

    instrument_lock_id = locks.get_instrument_lock_id(request)
    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    with log.error_on_exception("Failed Add Existing STARTED e-mail"):
        simplified_uploads = [ name for (name, path) in list(uploaded_files.items()) ]
        results_kind = "Add Existing"
        username = request.user.first_name + " " + request.user.last_name
        mail.crds_notification(
            body=mail.GENERIC_STARTED_BODY, status="STARTED",
            username=username, user_email=request.user.email, 
            uploaded_files = simplified_uploads, results_kind = results_kind,
            description = description, monitor_url=jpoll_handler.monitor_url)
        
    pmap = crds.get_symbolic_mapping(pmap_name)
    pmap_references = pmap.reference_names()
    for added in added_files:
        assert added not in pmap_references, "File " + repr(added) + " is already in context " + repr(pmap.name)
        blob = models.FileBlob.load(added)
        assert not blob.rejected and not blob.blacklisted,  "File " + repr(added) + " is bad or contains bad files."

    ars = submit.AddExistingReferenceSubmission(pmap_name, uploaded_files, description,
                                                user=request.user, instrument_lock_id=instrument_lock_id,
                                                status_channel=jpoll_handler)
    disposition, new_mappings_map, mapping_certs, mapping_diffs, collision_list = ars.submit()

    add_results = {
                "pmap" : pmap_name,
                "pmap_mode" : pmap_mode,

                "new_file_map" : new_mappings_map,
                "uploaded_basenames" : [],
                "added_files" : added_files,
                "submission_kind" : "add references",
                "title" : "Add Existing References",
                "description" : description,
                "context_rmaps" : sorted(new_mappings_map.values()),

                "certify_results" : mapping_certs,
                "diff_results" : mapping_diffs,

                "collision_list" : collision_list,

                "should_still_be_locked" : instrument_lock_id,
                "requires_locking" : True,

                "more_submits" : "/add/reference/",
                "disposition": disposition,
            }

    result = render_repeatable_result(
        request, 'add_existing_references_results.html', add_results)

    with log.error_on_exception("Failed Add Existing READY e-mail"):
        renamed_uploads = list(new_mappings_map.items())
        status = "READY" if not disposition else disposition.upper()
        mail.crds_notification(
            body=mail.GENERIC_READY_BODY, status=status,
            username=username, user_email=request.user.email, 
            uploaded_files = renamed_uploads, results_kind = results_kind,
            description = description, repeatable_url=result.authenticated_url)
        
    return redirect_jpoll_result(result, jpoll_handler)

# ===========================================================================


# ===========================================================================


# This is light-weight super-user functionality with minimal testing.

@error_trap("create_contexts_input.html")
@log_view
@superuser_login_required
def create_contexts(request):
    """create_contexts generates a new pmap and imaps given an existing pmap
    and set of new rmaps.   Note that the "new" rmaps must already be in CRDS.
    """
    if request.method == "GET":
        return crds_render(request, "create_contexts_input.html", requires_pmaps=True)
    else:
        return create_contexts_post(request)

def create_contexts_post(request):
    """View fragment handling create_contexts POST case."""
    pmap_name = get_recent_or_user_context(request)
    context_rmaps = validate(request, "rmaps", is_list_of_rmaps)
    description = validate(request, "description", common.DESCRIPTION_RE)
    context_name_map, collisions = submit.create_contexts(description, context_rmaps, str(request.user), pmap_name)

    models.clear_cache()

    return redirect_repeatable_result(request, "create_contexts_results.html", {
                "pmap": pmap_name,
                "original_pmap": pmap_name,
                "pmap_mode" : "pmap_text",
                "requires_locking": False,
                "new_file_map" : [],
                "uploaded_basenames": [],
                "context_rmaps" : context_rmaps,
                "context_name_map" : context_name_map,
                "submission_kind" : "new context",
                "title" : "Create Contexts",
                "description" : description,
                "more_submits" : "/create_contexts/",
                "collision_list" : collisions,
            })

# ============================================================================

@error_trap("submit_input.html")
@log_view
@login_required
@group_required("file_submission")
@instrument_lock_required
def submit_files(request, crds_filetype):
    """Handle file submission,  crds_filetype=reference|mapping."""
    if request.method == "GET":
        if crds_filetype == "mapping":
            page_title_help = "Submit .rmaps, .imaps, or .pmaps."
        else:
            page_title_help = "Submit new references without generating new rules."
        return crds_render(request, "submit_input.html", {
                    "crds_filetype" :  crds_filetype,
                    "page_title_help" : page_title_help,
                    "compare_old_reference" : "checked",
                    "generate_contexts" : "checked",
                }, requires_pmaps=True)
    else:
        return submit_files_post(request, crds_filetype)

@profile("submit_files.stats")
def submit_files_post(request, crds_filetype):
    """Handle the POST case of submit_files, returning dict of template vars."""
    # crds_filetype constrained by RE in URL to 'mapping' or 'reference'.
    # observatory = get_observatory(request)
    compare_old_reference = checkbox(request, "compare_old_reference")
    generate_contexts = checkbox(request, "generate_contexts")
    auto_rename = checkbox(request, "auto_rename")
    if generate_contexts or compare_old_reference:
        pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    else:
        pmap_mode, pmap_name = None, None
    description = validate(request, "description", common.DESCRIPTION_RE)
    creator = validate(request, "creator", common.PERSON_RE)
    change_level = validate(request, "change_level", models.CHANGE_LEVELS)
    _remove_dir, uploaded_files = get_files(request)
    instrument_lock_id = locks.get_instrument_lock_id(request)

    assert not generate_contexts or instrument_lock_id or request.user.is_superuser,  \
        "Can't generate contexts in unlocked mode."

    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    with log.error_on_exception("Failed Submit File STARTED e-mail"):
        simplified_uploads = [ name for (name, path) in list(uploaded_files.items()) ]
        results_kind = f"Submit {crds_filetype.title()}"
        username = request.user.first_name + " " + request.user.last_name
        mail.crds_notification(
            body=mail.GENERIC_STARTED_BODY, status="STARTED",
            username=username, user_email=request.user.email, 
            uploaded_files = simplified_uploads, results_kind = results_kind,
            description = description, monitor_url=jpoll_handler.monitor_url)
        
    simple = submit.SimpleFileSubmission(pmap_name, uploaded_files, description, user=request.user,
        creator=creator, change_level=change_level, auto_rename=auto_rename,
        compare_old_reference=compare_old_reference, instrument_lock_id=instrument_lock_id,
        status_channel=jpoll_handler)

    disposition, certify_results, new_file_map, collision_list, context_rmaps = \
        simple.submit(crds_filetype, generate_contexts)

    rdict = {
                "crds_filetype": crds_filetype,
                "collision_list" : collision_list,

                "context_rmaps" : context_rmaps,
                "new_file_map" : sorted(new_file_map.items()),
                "uploaded_basenames" : list(uploaded_files.keys()),
                "submission_kind" : "submit file",
                "title" : "Submit File",
                "description" : description,
                "pmap" : pmap_name,
                "pmap_mode" : pmap_mode,

                "certify_results" : certify_results,
                "more_submits" : "/submit/" + crds_filetype + "/",
                "requires_locking" : generate_contexts,
                "should_still_be_locked": instrument_lock_id,

                "disposition" : disposition,
    }

    result = render_repeatable_result(
        request, 'submit_results.html', rdict)

    with log.error_on_exception("Failed Submit File READY e-mail"):
        renamed_uploads = list(new_file_map.items())
        status = "READY" if not disposition else disposition.upper()
        mail.crds_notification(
            body=mail.GENERIC_READY_BODY, status=status,
            username=username, user_email=request.user.email, 
            uploaded_files = renamed_uploads, results_kind = results_kind,
            description = description, repeatable_url=result.authenticated_url)
        
    return redirect_jpoll_result(result, jpoll_handler)

# ===========================================================================

def flatten(path):
    """match paths retain some structure: (top-level, match, useafter) which
    we ditch here.
    """
    newpath = ()
    for part in path:
        newpath = newpath + part
    return newpath

# ===========================================================================

@error_trap("base.html")
@log_view
def difference_files(request):
    """Compare two files,  either known or uploaded,  and display the diffs."""
    if request.method == "GET":
        file1 = request.GET.get("file1", None)
        file2 = request.GET.get("file2", None)
        if file1 is None and file2 is None:
            return crds_render(request, "difference_input.html")
        else:
            file1_orig = validate(request, "file1", is_known_file)
            file2_orig = validate(request, "file2", is_known_file)
            file1_path = models.FileBlob.load(file1_orig).pathname
            file2_path = models.FileBlob.load(file2_orig).pathname
        must_delete1 = must_delete2 = False
    else:
        must_delete1, file1_orig, file1_path = handle_known_or_uploaded_file(
            request, "filemode1", "file_known1", "file_uploaded1")
        must_delete2, file2_orig, file2_path = handle_known_or_uploaded_file(
            request, "filemode2", "file_known2", "file_uploaded2")

    assert os.path.splitext(file1_orig)[-1] == os.path.splitext(file2_orig)[-1], \
        "The specified files are not compatible for differencing.  (Different file name extensions.)"
    assert os.path.exists(file1_path), \
        "File " + repr(file1_path) + " is not available in the server file cache."
    assert os.path.exists(file2_path), \
        "File " + repr(file2_path) + " is not available in the server file cache."

    if rmap.is_mapping(file1_orig):  # compute files for nested rmap differences
        upload_tuples, logical_errors = mapping_upload_tuples(file1_orig, file2_orig, file1_path, file2_path)
    else:   # references
        upload_tuples = [(file1_orig, file2_orig, file1_path, file2_path)]
        logical_errors = []

    # log.info("upload_tuples:", upload_tuples)

    diff_results = web_difference.mass_differences(upload_tuples)

    # log.info("diff_results:", log.PP(diff_results))

    handle_upload_delete(must_delete1, file1_orig, file1_path)
    handle_upload_delete(must_delete2, file2_orig, file2_path)

    return crds_render(request, "difference_results.html", {
            "file1" : file1_orig,
            "file2" : file2_orig,
            "diff_results" : diff_results,
            "top_level_logical_errors": logical_errors,
        })

def mapping_upload_tuples(file1_orig, file2_orig, file1_path, file2_path):
    """From the exhaustive list of logical differences,  determine the set of top level files to difference.
    """
    ldiffs, lerrs = web_difference.mapping_logical_diffs(file1_orig, file2_orig, file1_path, file2_path)
    uploads = set()
    for diff in ldiffs:
        last_map = None
        for tup in diff:
            if tup == (file1_path, file2_path):
                tup = (file1_orig, file2_orig, file1_path, file2_path)
            if isinstance(tup, tuple) and len(tup) >= 2 and rmap.is_mapping(tup[0]) and rmap.is_mapping(tup[1]):
                last_map = tup
            else:
                break
        assert last_map is not None, "Unexpected mapping difference " + repr(diff)
        uploads.add(last_map)
    return sorted(list(uploads)), lerrs

# ===========================================================================

@profile("browse_details.stats")
@error_trap("base.html")
@log_view
def browse_known_file(request, filename):
    """special view which accepts browse file from a URL parameter,  required
    by cross links like /browse/some_file.rmap
    """
    config.check_filename(filename)
    try:
        blob = models.FileBlob.load(filename)
        browsed_file = blob.pathname
        related_actions = models.AuditBlob.related_to(filename)
    except LookupError:
        raise CrdsError("Can't find " + repr(filename))

    file_contents = browsify_file.browsify_file(filename, browsed_file)

    # used_by_files = list(uses.uses([filename], blob.observatory))

    if blob and blob.type == "reference":
        context = models.get_default_context(blob.observatory, "edit")
        match_paths = matches.find_full_match_paths(context, filename)
        match_paths = [flatten(path) for path in match_paths]
    else:
        match_paths = []

    ld_tpn_text = tpn_text = ""
    if not rmap.is_mapping(filename):
        with log.error_on_exception("Failed loading TPN constraints for", srepr(filename)):
            tpn_text = reftypes.get_types_object(blob.observatory).reference_name_to_tpn_text(filename)
        with log.error_on_exception("Failed loading LD_TPN constraints for", srepr(filename)):
            tpn_text = reftypes.get_types_object(blob.observatory).reference_name_to_tpn_text(filename)

    return crds_render(request, "browse_results.html", {
             "fileblob" : blob,
             "observatory" : blob.observatory,
             "related_actions": related_actions,
             # "used_by_files" : used_by_files,
             "match_paths" : match_paths,
             "file_contents": file_contents,
             "tpn_text" : tpn_text,
             "ld_tpn_text" : ld_tpn_text,
             "browsed_file": filename,
             'prior_file_versions' : get_prior_file_versions(blob)
    })

def get_prior_file_versions(blob, count=20):
    """Returns a list of the last `count` files used in the derivation
    of the file represented by FileBlob `blob`.   May be < count filenames.
    """
    file_versions = []
    while count:
        prior = blob.derived_from
        try:
            blob = models.FileBlob.load(prior)
        except LookupError:
            break
        file_versions.append(prior)
        count -= 1
    return file_versions

# ===========================================================================

# @profile('recent_activity.stats')
@error_trap("recent_activity_input.html")
@log_view
# @login_required
def recent_activity_input(request):
    """recent_activity displays records from the AuditBlob database."""
    return crds_render(request, "recent_activity_input.html")

@error_trap("recent_activity_input.html")
@log_view
@profile("recent_activity_query.stats")
def recent_activity_query(request):
    """View fragment handling recent_activity POST case."""

    action = validate(request, "action", models.AUDITED_ACTIONS+[r"\*"], "*")
    observatory = validate(request, "observatory", models.OBSERVATORIES+[r"\*"], "*")
    instrument = validate(request, "instrument", models.INSTRUMENTS+[r"\*"], "*")
    filekind = validate(request, "filekind", models.FILEKINDS+[r"\*"], "*")
    extension = validate(request, "extension", models.EXTENSIONS+[r"\*"], ".pmap")
    filename = validate(request, "filename", r"[A-Za-z0-9_.\*]+", "*")
    user = validate(request, "deliverer_user", r"[A-Za-z0-9_.\*]+", "*")
    start_date = validate(request, "start_date", parse_date, "*")
    stop_date = validate(request, "stop_date", parse_date, "*")

    if "*" not in [start_date, stop_date]:
        assert stop_date >= start_date,  "Stop date precedes start date,  no matches possible."

    if filename != "*":
        action = observatory = instrument = filekind = extension = user = start_date = stop_date = "*"
    filters = {}
    for var in ["action", "instrument", "filekind", "extension", "user"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    if start_date != "*":
        filters["date__gte"] = start_date
    if stop_date != "*":
        filters["date__lte"] = stop_date
    filtered_activities = models.AuditBlob.filter(**filters)[::-1]

    # Skip .cat files since they're not deliverable files and don't currently browse.
    filtered_activities = [blob for blob in filtered_activities if not blob.filename.endswith((".cat",))]

    # Filter filenames with UNIX style name globbing
    filtered_activities = [blob for blob in filtered_activities if fnmatch.fnmatch(blob.filename, filename)]

    # Skip mass import actions by default since for HST there are 14k+ of them
    if action == "*":
        filtered_activities = [blob for blob in filtered_activities if blob.action != "mass import"]

    if start_date != "*":
        filters["start_date"] = timestamp.format_date(filters.pop("date__gte"))
    if stop_date != "*":
        filters["stop_date"] = timestamp.format_date(filters.pop("date__lte"))

    return crds_render(request, "recent_activity_results.html", {
                "filters": sorted(filters.items()),
                "filtered_activities" : filtered_activities,
                "crds_name_map" : _get_crds_name_map(),
            })

@models.crds_cached
def _get_crds_name_map():
    """Return the filename relationships needed to support the 'browsify' template
    filter.   To optimize performance,  cache the results in Django's cache.

    Returns   { filename : (blob.uploaded_as,  blob.derived_from), ... }
    """
    fileblobs = models.FileBlob.objects.all()
    naming_map = { blob.name : (blob.uploaded_as, blob.derived_from) 
                   for blob in fileblobs }
    return naming_map

# ===========================================================================

@profile('delivery_status.stats')
@error_trap("base.html")
@log_view
@login_required
def delivery_status(request):
    """Show a table of the catlog files reflecting file deliveries and their status."""

    status = models.get_delivery_status()
    
    return crds_render(request, "delivery_status.html", {
            "delivery_status": status,
    })

# ===========================================================================

@profile("browse_db.stats")
@error_trap("browse_db_input.html")
@log_view
# @login_required
def browse_db(request):
    """browse_db displays records from the FileBlob (subclasses) database."""
    if request.method == "GET":
        return crds_render(request, "browse_db_input.html")
    else:
        return browse_db_post(request)

def browse_db_post(request):
    """View fragment handling browse_db POST case."""
    observatory = validate(request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate(request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate(request, "filekind", models.FILEKINDS+[r"\*"])
    extension = validate(request, "extension", models.EXTENSIONS+[r"\*"])
    filename = validate(request, "filename", complete_re(config.FILE_RE_STR + r"|" + complete_re(r"\*")))
    deliverer_user = validate(request, "deliverer_user", [r"\*"] + render.usernames())
    status = validate(request, "status",  complete_re(r"[A-Za-z0-9_.\*]+"))
    start_date = validate(request, "start_date", parse_date)
    stop_date = validate(request, "stop_date", parse_date)

    select_bad_files = checkbox(request, "select_bad_files")
    show_defects = checkbox(request, "show_defects")

    if "*" not in [start_date, stop_date]:
        assert stop_date >= start_date,  "Stop date precedes start date,  no matches possible."

    if filename != "*":
        instrument = filekind = extension = deliverer_user = status = start_date = stop_date = "*"

    filters = {}
    for var in ["instrument", "filekind", "extension",
                "filename", "deliverer_user", "status"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    if start_date != "*":
        filters["delivery_date__gte"] = start_date
    if stop_date != "*":
        filters["delivery_date__lte"] = stop_date

    table_json = cached_browse_table(tuple(sorted(filters.items())),
                                     select_bad_files=select_bad_files,
                                     show_defects=show_defects,
                                     authenticated=request.user.is_authenticated)

    if start_date != "*":
        filters["delivery_date_start"] = timestamp.format_date(filters.pop("delivery_date__gte"))
    if stop_date != "*":
        filters["delivery_date_stop"] = timestamp.format_date(filters.pop("delivery_date__lte"))

    return crds_render(request, "browse_db_results.html", {
            "filters": sorted(filters.items()),
            # "filtered_db" : filtered_db,
            "table_json" : table_json,
            "observatory" : observatory,
            })

@models.crds_cached
def cached_browse_table(filters, select_bad_files=False, show_defects=False, authenticated=False):
    """Compute the (mem)cached datatables JSON for database browsing."""
    filters = dict(filters)
    filtered_db = models.FileBlob.filter(**filters)
    if select_bad_files:
        filtered_db = [ blob for blob in filtered_db if blob.get_defects() ]
    header, rows = render_browse_table_data(filtered_db, show_defects, authenticated)
    table_data = to_datatables(header, rows)
    table_json = json.dumps(table_data)
    return table_json

def render_browse_table_data(filtered_db, show_defects, authenticated=False):
    """Generate JSON-able dicts for the search results table."""
    header = [
            "delivery date",
            "activation date",
            "useafter date",
            "name",
            "uploaded as",
            "aperture",
            "status",
            "description",
            "instrument",
            "reference type",
        ] + \
        (["deliverer"] if authenticated else []) + \
        (["defects"] if show_defects else []) + \
        ["<input type='submit' id='diff_button' value='diff' />"]


    rows = []
    for db in filtered_db:
        rows.append([
            stdtags.minutes(db.delivery_date_str),
            stdtags.minutes(db.activation_date_str),
            stdtags.minutes(db.useafter_date_str),
            stdtags.browse(db.name),
            db.uploaded_as,
            db.aperture,
            db.status,
            db.description,
            db.instrument,
            db.filekind,
            ] +
            ([db.deliverer_user] if authenticated else []) +
            ([repr(db.get_defects())] if show_defects else []) +
            ["<input type='checkbox' value='{}'/>".format(db.name)]
        )
    return header, rows

def to_datatables(header, rows):
    """Filter a header/data object into a jQuery datatables representation."""
    return dict(
            aoColumns = [ { "sTitle" : col } for col in header ],
            aaData = rows,
        )
# ============================================================================

@error_trap("base.html")
@log_view
def brokered_get(_request, filename):
    """Brokered get checks that a file exists in CRDS and is available and then
    redirects the request to an optimized download server.   The optimized
    download might be owned by the archive (TBD) or it might be handled
    directly by CRDS Apache,  or possibly by servers better optimized than Apache.

    From protocol standpoint,  redirecting is superior to asking for the URL
    and then fetching it sice it cuts out the return trip to client.  The CRDS
    /get/<filename> URL is fixed and mapped to this broker.   The broker then
    determines and redirects to the actual download URL.
    """
    try:
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise CrdsError("No CRDS database entry for" + srepr(filename))

    assert blob.available, \
        "File " + srepr(filename) + " is not yet available for distribution."

    url = jsonapi_views.create_unchecked_url(models.OBSERVATORY, filename)

    log.info("Brokering file", repr(filename), "from", repr(url))

    return HttpResponseRedirect(url)   # secure

if sconfig.DEBUG:
    # @condition(etag_func=None)
    @error_trap("base.html")
    @log_view
    def unchecked_get(_request, filename):
        """Get file data is a single URL within the CRDS/Django framework which
        can deliver files via HTTP.   Dedicated static file servers are recommended
        by Django,   but this is simple,  and works in debug mode.  Most likely
        this is not used in a production environment.
        """
        try:
            blob = models.FileBlob.load(filename)
        except LookupError:
            raise CrdsError("No CRDS database entry for" + srepr(filename))

        assert blob.available, \
            "File " + srepr(filename) + " is not yet available for distribution."

        if blob.type == "mapping":
            content_type = "text/plain"
        else:
            content_type = "application/octet-stream"

        response = HttpResponse( stream_response_generator(blob.pathname), content_type=content_type)
        response["Content-Disposition"] = 'attachment; filename=%s' % filename

        return response

def stream_response_generator(filename):
    """Attempt to support large files by yielding chunks of data to the response.
    Response streaming is fragile,  dependent on actions of middleware.
    """
    chunk = 0
    total = 0
    with open(filename, "rb") as infile:
        while True:
            try:
                data = infile.read(2**24)
            except IOError as exc:
                raise CrdsError("reading known CRDS file " + srepr(filename) +
                                " : " + str(exc))
            if not len(data):
                break
            log.info("Yielding", srepr(filename), "chunk #" + str(chunk), "of",
                      len(data), "bytes.")
            # yield data
            chunk += 1
            total += len(data)
            yield data

    log.info("Finished", srepr(filename), "total bytes", repr(total))

# @profile("get_archive.stats")
@error_trap("base.html")
@log_view
def get_archive(request, filename):
    """Supports a link for getting an archive of files of the form:

    http://hst-crds.stsci.edu/get_archive/<filename.tar.gz>?file1=hst.pmap&file2=hst_acs.imap?...
    """
    arch_extension = None
    for arch_extension in ARCH_MODES:
        if filename.endswith(arch_extension):
            break
    assert arch_extension in ARCH_MODES, \
        "Unsupported archive extension " + repr(filename)

    bundle_path = create_archive(request, arch_extension)

    response = HttpResponse(content_type="application/octet-stream")
    response.write(open(bundle_path).read())

    return response

ARCH_MODES = {
    "tar" : "w|",
    "tar.gz" : "w|gz",
    "tar.bz2" : "w|bz2",
}

def create_archive(request, arch_extension):
    """Based on filenames specified in GET request,  and format defined by
    arch_extension,  create and return an archive file,  caching it for next
    time.   The archive is cached based on requested names.
    """
    bundle_path = cached_bundle_path(request, arch_extension)
    if not os.path.exists(bundle_path):
        files = {}
        total_size = 0
        for var in request.GET:
            if var.startswith("file"):
                blob = validate(request, var, is_available_file_blob)
                total_size += blob.size
                if total_size >= sconfig.MAX_ARCHIVE_SIZE:
                    raise CrdsError("Archive request is too large.   Request bundled mappings only.")
                files[blob.name] = blob.pathname
        with log.error_on_exception("failed creating bundle", repr(bundle_path)):
            utils.ensure_dir_exists(bundle_path)
            tar = tarfile.open(bundle_path, mode=ARCH_MODES[arch_extension], dereference=True)
            for filename, path in list(files.items()):
                tar.add(path, arcname=filename)
            tar.close()
            os.chmod(bundle_path, 0o640)
    return bundle_path

def cached_bundle_path(request, arch_extension):
    """Compute the sha1sum of the filenames requested for a bundle to see
    if a bundle is already cached.
    """
    names = arch_extension # archive format is important,  download filename isn't
    for var in request.GET:
        if var.startswith("file"):
            name = validate(request, var, config.FILE_RE)
            names += name
    xsum = utils.str_checksum(names)
    path = sconfig.CRDS_ARCHIVE_CACHE_DIR + "/" + xsum + "."+ arch_extension
    return path


def get_archive_url(archive_name, filelist):
    """Return the URL CRDS uses to download an archive named `archive_name`
    containing the files in `filelist`.
    """
    if filelist:
        url = "/get_archive/" + archive_name + "?"
        for i, filename in enumerate(filelist):
            url += "file"+str(i)+"="+str(filename) + "&"
        return url[:-1]
    else:
        return ""

# ============================================================================

@error_trap("base.html")
@superuser_login_required
@log_view
def version_info(request):
    """Output a page with a table of software component versions."""
    return crds_render(request, "version_info.html", {
                "version_info" : sorted(versions.get_all_versions().items()),
                "crds_env" : sorted(config.get_crds_env_vars().items()),
            })

# ============================================================================

# File enable/disable has somewhat complicated semantics due to the operation of CRDS
# in a distributed fashion and the nature of interrelated mappings files.  In all cases
# files marked bad are assumed to produce scientifically invalid results.
#
# CRDS mappings are marked both "rejected" and "blacklisted".
# Blacklisting is a transitive reject which affects anscestor mappings, i.e. blacklisting
# and rmap blacklists all .pmap's which contain it.
# References are marked as "rejected" only.
# A list of "rejected" files is distributed to clients.  Clients reassess
# blacklisting on their own using the assumption that all mappings are blacklisted.
# Server knowledge of blacklisting mainly supports catalog displays of blacklist causes.

@error_trap("mark_bad_input.html")
@log_view
@login_required
@group_required("file_submission")
def mark_bad(request):
    """Serve the blacklist input form or process the POST."""
    if request.method == "GET":
        return crds_render(request, "mark_bad_input.html")
    else:
        return mark_bad_post(request)

@profile("mark_bad.stats")
def mark_bad_post(request):
    """View fragment to process the blacklist POST."""
    blacklist_roots = validate(request, "file_known", is_known_file_list)
    badflag = validate(request, "badflag", "bad|ok")
    why = validate(request, "why", common.DESCRIPTION_RE)

    if badflag == "bad":
        for blacklist_root in blacklist_roots:
            check_bad_file(blacklist_root)

    affected_files = set()
    for blacklist_root in blacklist_roots:
        affected_files = affected_files.union(
            set(mark_bad_core(str(request.user), blacklist_root, badflag, why)))

    models.clear_cache()

    affected_files = sorted(list(affected_files))
    with log.error_on_exception("Failed Mark Files Bad e-mail"):
        username = request.user.first_name + " " + request.user.last_name
        mail.crds_notification(
            body=mail.MARK_BAD_BODY, badflag=badflag.upper(),
            subject=f"Marked Files {badflag.upper()} by {username}.",
            username=username, user_email=request.user.email, 
            affected_files="\n".join(affected_files),
            description = why)

    return crds_render(request, "mark_bad_results.html", { "affected_files": sorted(list(affected_files)) })

def check_bad_file(blacklist_root):
    """Make sure `blacklist_root` does not appear in the operational context."""
    pmap_name = models.get_default_context(models.OBSERVATORY, "operational")
    pmap = crds.get_symbolic_mapping(pmap_name)
    assert blacklist_root not in pmap.mapping_names() + pmap.reference_names(), \
        "File '{}' is in the current operational context '{}'.  Create a new context which does not contain " \
        "it and make that context operational.  Then mark '{}' as 'bad'." \
        .format(blacklist_root, pmap_name, blacklist_root)

def mark_bad_core(user, blacklist_root, badflag, why):
    """Set's file reject state of `blacklist_root` based on `reject_type` and `badflag`
    and creates an AuditBlob listing `why`.
    """
    models.set_reject(blacklist_root, badflag=="bad")
    if rmap.is_mapping(blacklist_root):
        affected_files = models.transitive_blacklist(blacklist_root, badflag)
    else:
        affected_files = [blacklist_root]

    instrument, filekind = utils.get_file_properties(models.OBSERVATORY, blacklist_root)

    models.AuditBlob.new(
        user, "blacklist", blacklist_root, why,
        "marked as " + srepr(badflag.upper()),
        instrument=instrument, filekind=filekind)

    #
    # see CRDS_server/hosts scripts directory,  runs cron_sync pushing context
    #
    # XXXX: doing this direct cache sync has multiple issues with unit tests.
    #
    # For starters,  the server is no longer at the standard URL so given the
    # default (login? .setenv) shell environment the CRDS client's cron_sync 
    # hangs for 10 minutes retrying before timing out.
    #
    # Second,  even if the server was available,  it would never be appropriate
    # to sync the cache to the unit test database unless a test cache was in use.
    # Just like the server URL,  the full-up cache is used... which would potentially
    # change the server's active context to a test value.
    #
    # Hence,  commenting this out since a cron_job update once every few minutes or so
    # should be adequate.
    #
    # pysh.sh("update_server_cache")

    return affected_files

# ===========================================================================

@profile("set_default_context.stats")
@error_trap("base.html")
@log_view
@login_required
@group_required("file_submission")
def set_default_context(request):
    """Change the default context presented to users as the nominal start from
    which to derive new contexts.
    """
    if request.method == "GET":    # display rmap filters
        context_map = models.ContextModel.get_map()    # { operational : hst.pmap }
        context_pmaps = get_context_pmaps(context_map)  # { hst.pmap : hst.pmap <date> blacklisted }
        return crds_render(request, "set_default_context_input.html", {
                "context_map" : context_map,
                "context_pmaps" : context_pmaps,
                "context_types" : models.CONTEXT_TYPES,
                "description" : get_default_description_for_set_context(),
            }, requires_pmaps=True)
    else:
        new_default = get_recent_or_user_context(request)
        context_type = validate(request, "context_type", models.CONTEXT_TYPES)
        description = validate(request, "description", common.DESCRIPTION_RE)
        old_default = update_default_context(new_default, description, context_type, request.user)
        return crds_render(request, "set_default_context_results.html", {
                    "new_default" :  new_default,
                    "old_default" :  old_default,
                    "context_type" : context_type,
                })

def get_default_description_for_set_context(new_context=None):
    """Return the text of the description related to the transition from the current
    operational context to `new_context`.  Return "" for anything hard.
    """
    if new_context is None:
        new_context = models.get_default_context(models.OBSERVATORY, "edit")
    with log.error_on_exception("Can't find default description for transition to", srepr(new_context)):
        mappings = rmap.list_mappings("*.pmap", observatory=models.OBSERVATORY)
        old_context = models.get_default_context(models.OBSERVATORY, "operational")
        ith = mappings.index(old_context)
        if ith+1 < len(mappings) and mappings[ith+1] == new_context:
            description = models.FileBlob.load(new_context).thaw().description
        else:
            description = ""
        return description
    return ""

def get_context_pmaps(context_map):
    """Return a list of option tuples for rendering HTML to choose context
    pmaps (last 10). This defines what users will see for the context HTML
    drop-down menu.
    """
    context_pmaps = {}
    files = models.FileBlob.objects.all()
    for file_ in files:
        if file_.name in list(context_map.values()):
            file_.thaw()
            context_pmaps[file_.name] = render.pmap_label(file_)
    return context_pmaps

def update_default_context(new_default, description, context_type, user):
    """Do the work of choosing a new context."""
    is_available_file(new_default)
    old_default = models.get_default_context(models.OBSERVATORY, context_type)
    if old_default == new_default:
        raise CrdsError(srepr(old_default) + " is already in use for the " + srepr(context_type) + " context.")
    pmap = crds.get_symbolic_mapping(new_default)
    blobs = models.get_fileblob_map()
    pmap_names = pmap.mapping_names() + pmap.reference_names()
    bad_files = []
    with log.error_on_exception("Bad file check failed"):
        bad_files = [ name for name in pmap_names if name in blobs and blobs[name].rejected ]
    if bad_files and context_type == "operational":
        raise CrdsError("Context " + srepr(new_default) +
                        " contains known bad files and cannot be made the default (last 4 of " +
                        str(len(bad_files)) + " bad files): " + ", ".join(bad_files[-4:]))
    models.set_default_context(new_default, observatory=models.OBSERVATORY, state=context_type, description=description)
    models.AuditBlob.new(str(user), "set default context",
                         new_default, description,
                         context_type + " context changed from " +
                         srepr(old_default) + " to " + srepr(new_default))

    #
    # see CRDS_server/hosts scripts directory,  runs cron_sync pushing context
    #
    # XXXX: doing this direct cache sync has multiple issues with unit tests.
    #
    # For starters,  the server is no longer at the standard URL so given the
    # default (login? .setenv) shell environment the CRDS client's cron_sync 
    # hangs for 10 minutes retrying before timing out.
    #
    # Second,  even if the server was available,  it would never be appropriate
    # to sync the cache to the unit test database unless a test cache was in use.
    # Just like the server URL,  the full-up cache is used... which would potentially
    # change the server's active context to a test value.
    #
    # Hence,  commenting this out since a cron_job update once every few minutes or so
    # should be adequate.
    #
    # pysh.sh("update_server_cache")

    with log.error_on_exception("Failed Update Default Context e-mail"):
        username = user.first_name + " " + user.last_name
        mail.crds_notification(
            body=mail.UPDATE_CONTEXT_BODY, 
            subject=f"Update {context_type} context from '{old_default}' to '{new_default}'.",
            username=username, user_email=user.email, 
            old_default=old_default, new_default=new_default, state=context_type,
            description = description)
        
    return old_default

@profile("display_context_history.stats")
@error_trap("base.html")
@log_view
def display_context_history(request):
    """Change the default context presented to users as the nominal start from
    which to derive new contexts.
    """
    history, history_tuples = get_context_history_variables()
    response = crds_render(request, "display_context_history.html", {
            "history" : history,
            "history_tuples" : history_tuples,
            "include_diff" : True,
        }, requires_pmaps=False)
    response['Cache-Control'] = "no-cache"
    return response

#  @models.crds_cached  currently not cacheable due to datetime.datetime's
def get_context_history_variables(last_n=None):
    """Return the data required to render the context history,  suitable for caching."""
    history = models.get_context_history(observatory=models.OBSERVATORY, state="operational")
    if last_n is not None:
        history = history[:last_n]
    # log.info("context_history:", history)
    context_blobs = { blob.name:blob for blob in models.FileBlob.filter(name__endswith=".pmap") }
    # log.info("context_blobs:", context_blobs)
    history_tuples = [ (hist, context_blobs[hist.context]) for hist in history ]
    return history, history_tuples

@error_trap("edit_context_history.html")
@login_required
@log_view
@group_required("edit_context_history")
def edit_context_history(request, history_id):
    """Privileged page supporting replacing the context table description field."""
    if request.method == "GET":
        return crds_render(request, "edit_context_history.html", dict(
            context_history=models.ContextHistoryModel.objects.get(id=int(history_id)),
        ), requires_pmaps=False)
    else:
        context_history=models.ContextHistoryModel.objects.get(id=int(history_id))
        context_history.description = validate(request, "description", common.DESCRIPTION_RE)
        context_history.save()
        models.clear_cache()
        response = redirect("/display_context_history") # secure
        return response

# ============================================================================

@error_trap("base.html")
@log_view
def display_all_contexts(request):
    """Display a table of all contexts in time order."""
    context_blobs = reversed(sorted([ ( blob.name, blob) for blob in models.FileBlob.filter(name__endswith=".pmap") ]))
    response = crds_render(request, "display_all_contexts.html", {
            "context_blobs" : context_blobs,
            "include_diff" : True,
        }, requires_pmaps=False)
    response['Cache-Control'] = "no-cache"
    return response

# ============================================================================

@error_trap("base.html")
@log_view
def old_results(request):
    """Display a table of all contexts in time order."""
    result_blobs = []
    for blob in reversed(models.RepeatableResultBlob.objects.all()):
        blob.thaw()
        if blob.page_template not in ["certify_results.html"]:
            result_blobs.append(blob)
    for blob in result_blobs:
        new_file_map = blob.parameters.get("new_file_map", [])
        if isinstance(new_file_map, dict):
            new_file_map = list(new_file_map.items())
        files = [ names[1] for names in new_file_map ]
        files += [ names[1] for names in blob.parameters.get("uploaded_files_map", [])]
        files += [ name for name in blob.parameters.get("uploaded_basename", [])]
        files += [ name for name in blob.parameters.get("added_files", [])]
        files += [ name for name in blob.parameters.get("deleted_files", [])]
        blob.files = sorted(set([str(name) for name in files]))
    response = crds_render(request, "old_results.html", {
            "result_blobs" : result_blobs,
        }, requires_pmaps=False)
    response['Cache-Control'] = "no-cache"
    return response

# ============================================================================

@profile("uses.stats")
@log_view
def uses_view(request, filename):
    """Return the list of files that use `filename` as a JSON list."""
    filename = is_known_file(filename)
    files = uses.uses([filename], models.OBSERVATORY)
    return HttpResponse(json.dumps(files), content_type="application/json")

# ============================================================================

CATALOG_FIELDS = (
    ("activation_date_str", "Activation Date"),
)

@error_trap("base.html")
@log_view
def context_table(request, mapping, recursive="10"):
    """Return either the top level context table HTML associated with a historical
    context display *or* the JSON representation of a .rmap context display.
    """
    mapping = str(mapping)
    recursive = int(recursive)
    if mapping.endswith(".rmap"):
        header, rows = catalog_fusion.get_rmap_web_parameters(mapping, CATALOG_FIELDS)
        datatables = to_datatables(header, rows)
        return HttpResponse(json.dumps(datatables), content_type='application/json')
    else:
        pars = get_context_table_parameters(mapping)
        return crds_render(request, "context_table.html", pars, requires_pmaps=False)

@models.crds_cached
def get_context_table_parameters(pmap):
    """Return the parameters required to display a context table for `pmap`."""
    try:
        pmap_name, pmap_dict = catalog_fusion.get_mapping_dict(pmap)
        assert is_pmap(pmap_name), "mapping must be a .pmap"
        return {
            "pmap" : pmap_dict,
            "mapping_type" : pmap_dict["header"]["mapping"],
        }
    except Exception as exc:
        log.error("Failure in get_context_table_parameters:", str(exc))
        return {}

if sconfig.DEBUG:

    @capture_output
    def runit(mode, command):   # secure,  only available for config.DEBUG
        """Exec or Eval a Python command and capture the output."""
        # log.info("DEBUG COMMAND:", repr(command))
        try:
            if mode == "eval":
                result = eval(command, globals(), locals())   # secure,  only available for config.DEBUG
            else:
                exec(command, globals(), locals())  # secure,  only available for config.DEBUG
                result = None
        except Exception as exc:
            result = "EXCEPTION: " + str(exc)
        # log.info("DEBUG RESULT:", result)
        return result

    @error_trap("base.html")
    @log_view
    @superuser_login_required
    def debug_command(request):
        """Support a debug page for evaluating Python expressions and statements on the running server.
        Intended for Django debug mode only,  not production use,  security hole.
        """
        if request.method == "GET":
            return crds_render(request, "command_result.html")
        else:
            command = str(request.POST["command"].strip())
            mode = validate(request, "mode", "exec|eval")
            result, output = runit(mode, command)   # @capture_output adds tuple format + output string
            return crds_render(request, "command_result.html", dict(command_result=result, command_output=output))

