"""This module defines the Django view functions which respond to HTTP requests
and return HTTP response objects.
"""

# Create your views here.
import sys
import os
import os.path
import re
import cStringIO
import traceback
import tarfile
import glob
import json
import time
import fnmatch

# from django.http import HttpResponse
from django.template import loader, RequestContext
from django.shortcuts import redirect
from django.shortcuts import render as django_render
from django.http import HttpResponse, HttpResponseRedirect
import django.utils.safestring as safestring
from django.utils import simplejson
from django.core.urlresolvers import reverse

import django.contrib.auth
import django.contrib.auth.models
from django.contrib.auth.decorators import login_required as login_required

import pyfits

from crds import (rmap, utils, timestamp, uses, matches, checksum, compat, log, config)
from crds import (data_file, pysh)
from crds import CrdsError

from crds.timestamp import (DATE_RE_STR, TIME_RE_STR)

from . import (models, database, web_certify, web_difference, submit, versions, locks, html)
from .templatetags import stdtags
from .models import FieldError, MissingInputError
from .common import capture_output, srepr, profile

from crds.server.jpoll import views as jpoll_views
from crds.server.jsonapi import views as jsonapi_views
from crds.server import settings
from crds.server import config as sconfig

HERE = os.path.dirname(__file__) or "./"

# ===========================================================================

log.add_stream_handler(sys.stderr)
log.remove_console_handler()

# ===========================================================================

def check_value(value, pattern, msg):
    """Ensure that `value` satisifies the conditions implied by `pattern`,
    otherwise raise a FieldError containing `msg`.
    
    If pattern is a function,  call it and trap for assertions, adjust value.
    If pattern is a list,  `value` must be in it.
    If pattern is a string, it is a regex which `value` must match.
    
    Return `value` if it checks out OK.
    """
    value = str(value)
    if isinstance(pattern, type(check_value)):
        try: 
            return pattern(value)
        except AssertionError, exc:
            raise FieldError(msg + " : " + str(exc))
    elif isinstance(pattern, list):
        for choice in pattern:
            assert "|" not in choice, "Found | in choice " + srepr(choice) + \
                " seen as regex special char"
        pattern = "|".join(pattern)
    if not re.match(pattern, value):
        raise FieldError(msg)
    return value


def validate(request, variable, pattern):
    """Check a `variable` from `request`,  ensuring that it meets the
    check_value() conditions specified by `pattern`.  Use GET or POST
    depending on request type.
    """
    vars = request.GET if request.method == "GET" else request.POST
    value = str(vars[variable]).strip()
    return check_value(value, pattern, "Invalid value " + srepr(value) + 
                                        " for " + srepr(variable))

def get_or_post(request, variable):
    """Return `variable` wherever it is defined in request, GET or POST."""    
    return (variable in request.POST and request.POST[variable]) or \
           (variable in request.GET  and request.GET[variable])

def checkbox(request, variable):
    """Return the boolean value of checkbox `variable` with <input> in standard idiom."""
    return bool(get_or_post(request, variable))

# ===========================================================================

# "pattern" functions for validate_post/get

FILE_RE = r"[A-Za-z0-9_]+(\.fits|\.pmap|\.imap|\.rmap|\.r\d[hd])"
DESCRIPTION_RE = r"[A-Za-z0-9._ ]+"
PERSON_RE = r"[A-Za-z_0-9\.@]*"
DATASET_ID_RE = r"[A-Za-z0-9_]+"
URL_RE = r"(/[A-Za-z0-9_]?)+"
FITS_KEY_RE = r"[A-Z0-9_\-]+"
FITS_VAL_RE = r"[A-Za-z0-9_\- :\.]*"

def is_pmap(filename):
    """Verify that `filename` names a known CRDS pipeline mapping.
    Otherwise raise AssertionError.
    """
    try:
        return is_mapping(filename, r"\.pmap")
    except Exception, exc:
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
    if not re.match("\w+" + extension, filename):
        raise CrdsError("Invalid mapping filename " + srepr(filename))
    is_known_file(filename)
    return filename

def is_reference(filename, extension=r"\.fits|\.r\dh|\.r\dd"):
    """Verify that `filename` names a known CRDS reference file.
    Otherwise raise AssertionError.
    """
    if not re.match(r"\w+"+extension, filename):
        raise CrdsError("Invalid reference filename " + srepr(filename))
    is_known_file(filename)
    return filename

def is_known_file(filename):
    """Verify that `filename` identifies a file already known to CRDS and
    has progressed beyond the 'uploaded' temporary file stage.
    """
    if not re.match(FILE_RE, filename):
        raise CrdsError("Invalid filename " + srepr(filename))
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
    for file in files:
        is_known_file(file)
    return files

def is_available_file_blob(filename):
    """Verify that `filename` identifies a file already known to CRDS and
    meets any requirements for distribution.   Return its blob.
    """
    if not re.match(FILE_RE, filename):
        raise CrdsError("Invalid filename " + srepr(filename))
    try:
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise CrdsError("No database entry for " + srepr(filename) + ".")
    assert blob.available, \
        "File " + srepr(filename) + " is not yet available."
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
        is_rmap(rmp)
    return rmaps

def is_match_tuple(tuple_str):
    """Raise an AssertionError if `tuple_str` is does not literal eval to a 
    tuple.  Otherwise return the tuple.
    """
    try:
        tup = compat.literal_eval(tuple_str.upper())
        assert isinstance(tup, tuple), "Enter a tuple to match against."
    except Exception:
        raise AssertionError("Enter a tuple to match against.")
    return tup

DESCRIPTION_RE = "[^<>]+"

def get_observatory(request):
    """Validate and return the observatory parameter from request.POST"""
    return validate(request, "observatory", models.OBSERVATORIES)

def usernames():
    """Return a list of all the usernames defined in the database."""
    try:
        return [str(x) for x in django.contrib.auth.models.User.objects.filter()]
    except Exception:  # provide a workable choice if it fails.
        return ["*"]

# ===========================================================================

def crds_render_html(request, template, dict_=None, requires_pmaps=False):
    """Render a template,  making same-named inputs from request available
    for echoing,  scrubbing file paths.   Return HTML.
    """
    rdict = get_rendering_dict(request, dict_=dict_, requires_pmaps=requires_pmaps)
    # Generate a first pass of the response HTML.
    loaded_template = loader.get_template(template)
    context = RequestContext(request, rdict)
    html = loaded_template.render(context)
    # Remove file paths and fix temporary names with client side names
    uploaded_pairs = rdict.get("uploaded_file_names", get_uploaded_filepaths(request))
    html = scrub_file_paths(html, uploaded_pairs)
    return html

def crds_render(request, template, dict_=None, requires_pmaps=False):
    """Render an HttpReponse object.    Return HttpResponse."""
    html = crds_render_html(request=request, template=template, dict_=dict_, requires_pmaps=requires_pmaps)
    return HttpResponse(html)

def get_rendering_dict(request, dict_=None, requires_pmaps=False):
    """Render a template,  making same-named inputs from request available
    for echoing.
    """
    statuses = ["*"] + models.FILE_STATUS_MAP.keys()
    statuses.remove("uploaded")
    
    locked = get_locked_instrument(request)
    locked = locked if locked else ""
    
    rdict = {   # standard template variables
        "observatory" : models.OBSERVATORY,
             
        "instrument" : "*",
        "instruments" : ["*"] + models.INSTRUMENTS,

        "filekind" : "*",
        "filekinds" : models.FILEKIND_TEXT_DESCR,

        "extensions" : ["*"] + models.EXTENSIONS,
        "users": ["*"] + usernames(),

        "status" : "*",
        "statuses": statuses,

        "action" : "*",
        "actions" : ["*"] + models.AUDITED_ACTIONS,

        "filename" : "*",
        "deliverer_user" : "*",
        "current_path" : request.get_full_path(),
        
        "locked_instrument" : locked,

        "username" : str(request.user),

        "auto_rename" : False,
        "server_usecase" :  sconfig.server_usecase.lower(),
    }
    
    # echo escaped inputs.
    for key, value in request.GET.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.POST.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.FILES.items():
        rdict[key] = safestring.mark_for_escaping(value)

    if requires_pmaps:
        pmap_edit = models.get_default_context()
        pmap_operational = models.get_default_context(state="operational")
        rdict.update({
            "pmap_edit" : pmap_edit,
            "edit_context_label" : pmap_label(pmap_edit),
            "pmap_operational" : pmap_operational,
            "operational_context_label" : pmap_label(pmap_operational),
            "pmaps" : get_recent_pmaps(),
        })

    # include view outputs
    if dict_ is not None:
        for key, value in dict_.items():
            rdict[key] = value
            
    # This is only for the purpose of showing/hiding logout.
    rdict["is_authenticated"] = request.user.is_authenticated()
    rdict["is_superuser"] = request.user.is_superuser
    
    # Set up variables required to support django-json-rpc Javacsript
    jsonrpc_vars = jsonapi_views.get_jsonrpc_template_vars()
    for var in jsonrpc_vars:
        if var in rdict:
            raise CrdsError("Template variable collision on " + srepr(var))
        else:
            rdict[var] = jsonrpc_vars[var]
            
    return rdict
            
def scrub_file_paths(response, uploaded_pairs):
    """Fix filepath leakage here as a brevity and security issue.   Uploaded file
    temporary names or paths are replaced with the client-side original name.  CRDS
    file tree paths of various kinds are replaced with the empty string.
    
    response:   the original un-scrubbed fully instantiated HTML response string.
    
    uploaded_pairs:  [(client_side_filename, temporary_upload_path), ...]
    """
    for (original_name, path) in uploaded_pairs:
        response = response.replace(path, original_name)
        path = os.path.basename(path)
        response = response.replace(path, original_name)
    observatory = models.OBSERVATORY
    response = response.replace(config.get_path("dummy.pmap", observatory) + "/", "")
    response = response.replace(config.get_path("dummy.fits", observatory) + "/", "")
    response = response.replace(config.get_crds_path() + "/", "")
    response = response.replace(sconfig.install_root + "/", "")
    return response

def get_uploaded_filepaths(request):
    """Return [ (original_name, temporary_path), ...] for uploaded files in `request`."""
    pairs = []
    for ufile in request.FILES.values():
        filepath = str(ufile.temporary_file_path())
        original_name = str(ufile.name)
        pairs.append((original_name, filepath))
    return pairs

# ===========================================================================

def handle_known_or_uploaded_file(request, modevar, knownvar, uploadvar):
    """Process file variables for a file which is either known to CRDS
    and simply named,  or which is uploaded by the user.
    
    Return (uploaded_flag, name_on_users_system,  temporary_file_path)
    """
    if request.POST[modevar] == knownvar:
        # certified_file is a basename,  but CRDS figures out where it is.
        original_name = validate(request, knownvar, is_known_file)
        filepath = get_known_filepath(original_name)
    else:
        ufile = get_uploaded_file(request, uploadvar)
        filepath = ufile.temporary_file_path()
        original_name = ufile.name
    return str(original_name), str(filepath)

def get_uploaded_file(request, formvar):
    """Return the DJango UploadedFile associated with `request` and `formvar`,
    raising an exception if it's original name does not end with one of
    `legal_exts` file extensions.   Handles <input type='file'>, part 1.
    """
    try:
        ufile = request.FILES[formvar]
    except KeyError:
        raise MissingInputError("Specify a file to upload for " + srepr(formvar))
    if not re.match(FILE_RE, ufile.name):
        raise FieldError("Unexpected file extension for " + srepr(ufile.name))
    return ufile

def get_files(request):
    """Obtain uploaded files from a common multi-mode form mechanism,  
    returning:   remove_dir,   { original_name : file_path }
    """
    dir = os.path.join(sconfig.CRDS_INGEST_DIR, str(request.user))
    uploads = { str(os.path.basename(f)) : str(f) for f in glob.glob(dir + "/*") }
    log.info("Scanned", srepr(dir), "for uploaded files:", uploads)
    for f in uploads:
        if rmap.is_mapping(f):
            # this will fail for user-scp'ed ingests.  but... maybe file already writeable.
            with log.warn_on_exception("Failed setting file mode on", repr(f)):
                os.chmod(uploads[f], 0660)
            # os.chmod(uploads[f], 0222)  # XXXX test test test
            # this will fail if `f` is not writeable.  but... maybe checksum already good.
            with log.warn_on_exception("Failed updating checksum on", repr(f)):
                checksum.update_checksum(uploads[f])
    if not uploads:
        raise CrdsError("No input files were specified.")
    return dir, uploads

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
        context = models.get_default_context()
    elif pmap_mode == "pmap_operational":
        context = models.get_default_context(state="operational")
    else:
        context = validate(request, pmap_mode, is_pmap)
    return pmap_mode, str(context)

def get_recent_or_user_context(request):
    """Process standard request parameters for specifying context."""
    return get_recent_or_user_mode_and_context(request)[1]

# ===========================================================================

class ServerError(Exception):
    """Uncaught exception which will be returned as HTTP 500"""
    
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
                msg = "ERROR: " + str(exc)
                pars = dict(keys.items() + [("error_message", msg)])
                return crds_render(request, template, pars, requires_pmaps=True)
        trap.func_name = func.func_name
        return trap
    return decorator

def log_view(func):
    """log() captures view inputs, output, and response to a log file.
    It should be called inside any error_trap() decorator so that it 
    executes before error_trap() absorbs many exceptions.
    """
    def dolog(request, *args, **keys):
        """trap() is bound to the func parameter of decorator()."""        
        log.info() # start with blank line to make concat logs readable
        log.info("REQUEST:", request.path, request.method, "ajax="+str(request.is_ajax()))
        # log.info("META:", log.PP(request.META))
        if request.GET:
            log.info("GET:",   repr(request.GET))
        if request.POST:
            log.info("POST:",  repr(request.POST))
#        if request.COOKIES:
#            log.info("COOKIES:", repr(request.COOKIES), stdout=None)
        # log.info("SESSION:", request.session.session_key, "expires", request.session.get_expiry_date())
        if request.FILES:
            log.info("FILES:", repr(request.FILES))
        # log.info("OUTPUT:")
        try:    
            response = func(request, *args, **keys)
#            log.info("RESPONSE:\n" + response.content, stdout=None)
            return response
        except locks.LockingError, exc:  # Skip the traceback for these,  remove manually for debug to log tracebacks
            log.error("Locking error: " + str(exc))
            raise  
        except Exception, exc:
            log.info("EXCEPTION REPR:", repr(exc))
            log.info("EXCEPTION STR:", str(exc))
            log.info("EXCEPTION TRACEBACK:")
            info = sys.exc_info()
            tb_list = traceback.extract_tb(info[2])
            for line in traceback.format_list(tb_list):
                log.info(line.strip(), time=False)
            raise
        finally:
            pass
    dolog.func_name = func.func_name
    return dolog

# ===========================================================================
# ===========================================================================
# ===========================================================================
"""Authentication and locking strategy:

1. File submission views require an authenticated user

2. As part of login,  an instrument is reserved to that user,  and only they can submit for it.
This part is triggered by the user_logged_in signal which allocates database based locks for that
instrument and user.

3. Database-based locks are refreshed whenever the session is refreshed.
This is achieved by providing lock refreshing middleware.  Any interactive use of the site causes refresh.

4. Both Sessions and locks expire 36 hours after the last access by the logged in user.

5. Logging out releases locks owned by a user.


There are two ways for a session to expire:
a. The session clock runs out and it expires.
b. The user logs out.
"""

def superuser_login_required(func):
    @login_required
    def _inner(request, *args, **keys):
        if not request.user.is_superuser:
            raise CrdsError(str(request.user) + " is not a super user.")
        return func(request, *args, **keys)
    _inner.func_name = func.func_name
    return _inner

# ===========================================================================

"""Hooks for coordinating locks on instruments with logins,  ensuring they're
obtained on login,  maintained across views, and eventually released on logout.
Implemented as Django login/logout signal handlers and a view decorator.

This is a kind of pessimistic locking,  where a user reserves a particular instrument
for as long as they're logged in,  but guaranteeing that when it comes time to submit
and confirm they've either still got a lock or they'll get notified they were booted.
This is in contrast to the optimistic approach of getting all set to commit without 
locking and then finding out someone else has locked the instrument and is waiting 
to confirm for some reason...  or even has submitted their own copies of the same files.
"""

# These signal handlers are called after a user is logged in or out to manage instrument locks.

from django.contrib.auth.signals import user_logged_in, user_logged_out

def lock_login_receiver(sender, **keys):
    """Signal handler to acquire locks for a user when they login."""
    request = keys["request"]
    user = str(keys["user"])
    
    if "instrument" in request.POST:
        instrument = validate(request, "instrument", models.INSTRUMENTS + ["none"])
        if instrument != "none":
            # log.info("Login receiver releasing all instrument locks for user '%s' session '%s'." % (user, request.session.session_key))
            with log.info_on_exception("login releasing locks failed"):
                locks.release_locks(user=user)
            
            del_locked_instrument(request)

            # log.info("Login receiver acquiring '%s' instrument lock for user '%s' session '%s'." % (instrument, user, request.session.session_key))
            try:
                locks.acquire(user=user, type="instrument", name=instrument, 
                              timeout=settings.CRDS_LOCK_ACQUIRE_TIMEOUT,
                              max_age=settings.CRDS_MAX_LOCK_AGE)
                set_locked_instrument(request, instrument)
            except locks.ResourceLockedError:
                owner = locks.owner_of(name=instrument, type="instrument")
                raise CrdsError("User '%s' has already locked instrument '%s'." % (owner, instrument))

user_logged_in.connect(lock_login_receiver, dispatch_uid="lock_login_receiver")

def lock_logout_receiver(sender, **keys):
    """Signal handler to release a user's locks if they log out."""
    with log.info_on_exception("logout releasing locks failed"):
        request = keys["request"]
        user = str(keys["user"])
        locks.release_locks(user=user)   
    del_locked_instrument(request)

user_logged_out.connect(lock_logout_receiver, dispatch_uid="lock_logout_receiver")

def lock_status(request):
    """AJAX view to return state of user lock."""
    status = locks.get_lock_status(type="instrument",
                                   user=str(request.user))
    return HttpResponse(json.dumps(status), mimetype='application/json')
        

def instrument_lock_required(func):
    """Decorator to ensure a user still owns an un-expired lock defined by their session data."""
    def _wrapped(request, *args, **keys):
        assert request.user.is_authenticated(), "You must log in."
        instrument = get_locked_instrument(request)
        user = str(request.user)
        if instrument is not None:
            locks.verify_locked(type="instrument", name=instrument, user=user)
        else:
            if not request.user.is_superuser:
                raise CrdsError("You can't access this function without logging in for a particular instrument.")
        return func(request, *args, **keys)
    _wrapped.func_name = func.func_name
    return _wrapped

def get_locked_instrument(request):
    """Based on the request,  return the instrument locked inside @instrument_lock_required."""
    return request.session.get("locked_instrument", None)

def set_locked_instrument(request, instrument):
    """Record which instrument is locked relative to this request."""
    request.session["locked_instrument"] = instrument
    
def del_locked_instrument(request):
    """Remove any trace of a locked instrument."""
    if hasattr(request, "session") and "locked_instrument" in request.session:
        with log.info_on_exception("forgetting locked instrument failed"):
            del request.session["locked_instrument"]

# ===========================================================================

# @profile("index.stats")
def index(request):
    """Return the top level page for all of interactive CRDS."""
    pars = get_context_table_parameters(request, "operational")
    return crds_render(request, "index.html", pars)

# ===========================================================================

@error_trap("base.html")
@login_required
def display_result(request, results_id):
    """Render the repeatable result with `results_id`.  Handle the /display_result/ URL."""
    results_id = int(results_id)
    try:
        result = models.RepeatableResultBlob.get(results_id)
    except Exception, exc:
        raise CrdsError("Error loading result " + str(results_id) + " : " + str(exc))
    pars = result.parameters
    pars["results_id"] = results_id  # needed to implement "disposition", confirmed or cancelled.
    return crds_render(request, result.page_template, pars)

def render_repeatable_result(request, template, rdict, jpoll_handler=None):
    """Create a repeatable results model instance and redirect to it."""
    rdict["user"] = str(request.user)
    rdict["uploaded_file_names"] = get_uploaded_filepaths(request)
    result = models.RepeatableResultBlob.new(template, rdict)
    if jpoll_handler:
        jpoll_handler.done(0, result.repeatable_url)
        time.sleep(10.0)  # wait 10 seconds to give jpoll done processing consistent behavior
    return HttpResponseRedirect(result.repeatable_url)

# ===========================================================================
from django.contrib.auth.views import login as django_login

# @profile("login.stats")
@error_trap("base.html")
def login(request):
    if request.method == 'POST':
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
            return django_login(request, "login.html", extra_context=dict(instruments=models.INSTRUMENTS + ["none"]))
        else:
            raise CrdsError("Please enable cookies and try again.")
    else:
        request.session.set_test_cookie()
        return django_login(request, "login.html", extra_context={
                    "observatory" : models.OBSERVATORY,
                    "instruments" : models.INSTRUMENTS + ["none"],
                })


def logout(request):
    """View to get rid of authentication state and become nobody again."""
    django.contrib.auth.logout(request)
    return redirect("/")

@error_trap("set_password.html")
@login_required
def set_password(request):
    """Support changing a user's own password."""
    if request.method == "POST":
        old_password =  validate(request, "old_password", ".+")
        user = django.contrib.auth.authenticate(username=str(request.user), password=old_password)
        assert user is not None, "Old password is not valid."
        new_password1 = validate(request, "new_password1", ".+")
        new_password2 = validate(request, "new_password2", ".+")
        assert new_password1 == new_password2, "New passwords are not the same."
        assert len(new_password1) >= 6, "At least 6 characters please."
        if not request.user.is_superuser:
            assert re.match("\w*\d\w*", new_password1),  "At least one digit please."
            assert re.match("\w*[a-zA-Z]\w*", new_password1),  "At least one letter please."
        request.user.set_password(new_password1)
        request.user.save()
        return crds_render(request, "set_password_results.html")
    else:
        return crds_render(request, "set_password.html")
    
# ===========================================================================

# The following code is derived from django-jquery-file-upload

# Fileupload is a Django port of a jQuery project from here:
# https://github.com/sigurdga/django-jquery-file-upload

def response_mimetype(request):
    if "application/json" in request.META['HTTP_ACCEPT']:
        return "application/json"
    else:
        return "text/plain"

class JSONResponse(HttpResponse):
    """JSON response class."""
    def __init__(self, obj='', json_opts={}, mimetype="application/json", *args, **kwargs):
        content = simplejson.dumps(obj, **json_opts)
        super(JSONResponse, self).__init__(content, mimetype, *args, **kwargs)

@error_trap("base.html")
@log_view
@login_required
def upload_new(request, template="upload_new_input.html"):
    """Support adding new files to the upload area."""
    if request.method == "GET":
        return crds_render(request, template)
    else:
        f = get_uploaded_file(request, 'file')
        file_local_dir = str(request.user)
        assert re.match(FILE_RE, f.name), "Invalid upload_new filename: " + srepr(f.name)
        assert re.match("[A-Za-z0-9_]+", file_local_dir), "Invalid file_local_dir " + srepr(file_local_dir)
        ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, file_local_dir, f.name)
        with log.verbose_on_exception("Failed removing", repr(ingest_path)):
            pysh.sh("rm -f ${ingest_path}")
            log.info("Removed existing", repr(ingest_path))
        utils.ensure_dir_exists(ingest_path, mode=0770)
        log.info("Linking", f.temporary_file_path(), "to", ingest_path)
        os.link(f.temporary_file_path(), ingest_path)
        data = [json_file_details(f.name, f.temporary_file_path())]
        response = JSONResponse(data, {}, response_mimetype(request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response

def json_file_details(filename, filepath):
    return {'name': filename, 
            # 'url': settings.MEDIA_URL + "pictures/" + f.name.replace(" ", "_"), 
            # 'thumbnail_url': settings.MEDIA_URL + "pictures/" + f.name.replace(" ", "_"), 
            'size' : os.stat(filepath).st_size,
            'delete_url': reverse('upload-delete', args=[filename]),
            'delete_type': "DELETE"}

@error_trap("base.html")
@log_view
@login_required
def upload_list(request, template="upload_new_input.html"):
    file_local_dir = str(request.user)
    assert re.match("[A-Za-z0-9_]+", file_local_dir), \
        "Invalid file_local_dir " + srepr(file_local_dir)
    ingest_glob = os.path.join(sconfig.CRDS_INGEST_DIR, file_local_dir, "*")
    try:
        ingest_paths = { os.path.basename(f):f for f in glob.glob(ingest_glob) }
        log.info("Listing existing ingest files", repr(ingest_paths))
    except Exception, exc:
        ingest_paths = []
        log.info("Failed globbing ingest files.")
    data = [ json_file_details(name, ingest_paths[name]) for name in ingest_paths ]
    response = JSONResponse(data, {}, response_mimetype(request))
    response['Content-Disposition'] = 'inline; filename=files.json'
    return response

@error_trap("base.html")
@log_view
@login_required
def upload_delete(request, filename):
    _upload_delete(request, filename)
    if request.is_ajax():
        response = JSONResponse(True, {}, response_mimetype(request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response
    else:
        return HttpResponseRedirect('/upload/new')

def _upload_delete(request, filename):
    with log.error_on_exception("Failed upload_delete for:", srepr(filename)):
        assert re.match(FILE_RE, filename), "Invalid upload_delete filename " + srepr(filename)
        file_local_dir = str(request.user)
        assert re.match("[A-Za-z0-9_]+", file_local_dir), "Invalid file_local_dir " + srepr(file_local_dir)
        ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, file_local_dir, filename)
        log.info("upload_delete", srepr(ingest_path))
        pysh.sh("rm -f ${ingest_path}")
   
def clear_uploads(request, uploads):
    """Remove the basenames listed in `uploads` from the upload directory."""
    for filename in uploads:
        _upload_delete(request, filename)

# ===========================================================================

@error_trap("bestrefs_index2.html")
def bestrefs(request):
    """View to get the instrument context for best references."""
    if request.method == "GET":
        return crds_render(request, "bestrefs_index2.html", requires_pmaps=True)
    else:
        return bestrefs_post(request)

def bestrefs_post(request):
    """View to get best reference dataset parameters."""
    context = get_recent_or_user_context(request)
    pmap = rmap.get_cached_mapping(context)
    dataset_mode = validate(
        request, "dataset_mode", "dataset_archive|dataset_uploaded|dataset_local")
    if dataset_mode == "dataset_uploaded":
        uploaded_file = get_uploaded_file(request, "dataset_uploaded")
        dataset_path = uploaded_file.temporary_file_path()
        dataset_name = uploaded_file.name
        # base on the context and datset,  compute best references
        header = pmap.get_minimum_header(dataset_path, original_name=dataset_name)
    elif dataset_mode == "dataset_local":
        header = header_string_to_header(request.POST["dataset_local"])
        header = pmap.minimize_header(header)
        dataset_name = validate(request, "dataset_name", FILE_RE)
    elif dataset_mode == "dataset_archive":
        dataset_name = validate(request, "dataset_archive", DATASET_ID_RE)
        try:
            header = database.get_dataset_header(dataset_name, pmap.observatory)
        except Exception, exc:
            raise CrdsError("Problem getting header for dataset " + 
                            srepr(dataset_name) + ": " + str(exc))
        header = pmap.minimize_header(header)
    else:
        raise ValueError("Bad dataset_mode " + srepr(dataset_mode))

    results = bestrefs_results(request, pmap, header, dataset_name)

    return results

def header_string_to_header(hstring):
    """Convert a string representing a FITS header into a dictionary, screening
    for illegal keys or values.
    """
    header = {}
    for line in cStringIO.StringIO(str(hstring)):
        words = line.split()
        key = words[0]
        value = " ".join(words[1:])
        value = utils.condition_value(value)
        if not re.match(FITS_KEY_RE, key) and re.match(FITS_VAL_RE, value):
            log.warning("Dropping illegal keyword '%s' with value '%s'." % (key, value))
            continue
        header[key] = value
    return header

def bestrefs_results(request, pmap, header, dataset_name=""):
    """Render best reference recommendations under context `pmap` for
    critical parameters dictionary `header`.
    """
        
    recommendations = rmap.get_best_references(pmap, header)
    
    # organize and format results for HTML display    
    header_items = sorted(header.items())
    bestrefs_items = []
    archive_files = []
    for key, val in sorted(recommendations.items()):
        if isinstance(val, basestring) and val.startswith("NOT FOUND"):
            val = val[len("NOT FOUND"):]
        bestrefs_items.append((key.upper, val))
        
    archive_name = os.path.splitext(dataset_name)[0] + "_bestrefs.tar.gz"
    
    return crds_render(request, "bestrefs_results.html", {
            "observatory" : pmap.observatory,
            "dataset_name" : dataset_name,
            "header_items" : header_items,
            "bestrefs_items" : bestrefs_items,
        })

# ===========================================================================

@error_trap("bestrefs_explore_index.html")
@log_view
def bestrefs_explore(request):
    """View to get the instrument context for best references."""
    if request.method == "GET":
        return crds_render(request, "bestrefs_explore_index.html", requires_pmaps=True)
    else:
        return bestrefs_explore_post(request)
    
def get_recent_pmaps(last_n=10):
    """Return a list of option tuples for rendering HTML to choose recent
    pmaps (last 10). This defines what users will see for the context HTML 
    drop-down menu.
    """
    files = models.FileBlob.objects.filter(name__endswith=".pmap")
    pmaps = []
    for f in files:
        f.thaw()
        if f.state == "uploaded":
            continue
        pmaps.append((f.name, pmap_label(f)))
    return list(reversed(pmaps))[:last_n]
    
def pmap_label(blob):
    """Return the text displayed to users selecting known pmaps."""
    if isinstance(blob, basestring):
        try:
            blob = models.FileBlob.load(blob)
        except LookupError:
            return "FILE LOOKUP FAILED -- invalid context"
    available = "" if blob.available else "*unavailable*" 
    blacklisted = "*blacklisted*" if blob.blacklisted else ""
    rejected = "*rejected*" if blob.rejected else ""
    return " ".join([blob.name, str(blob.delivery_date)[:16], available])  #, blacklisted, rejected])

def bestrefs_explore_post(request):
    """View to get best reference dataset parameters."""
    context = get_recent_or_user_context(request)
    pmap = rmap.get_cached_mapping(context)
    instrument = validate(request, "instrument", models.INSTRUMENTS)
    valid_values = dict(pmap.get_imap(instrument).get_parkey_map())
    for key, values in valid_values.items():
        if values == ["N/A"]:
            values = []
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

@error_trap("bestrefs_explore_input.html")
@log_view
def bestrefs_explore_compute(request):
    """Validate parameter inputs from the best refs explorer drop-down
    menus and render best reference recommendations.
    """
    context = validate(request, "context", is_pmap)
    instrument = validate(request, "instrument", models.INSTRUMENTS)
    pmap = rmap.get_cached_mapping(context)
    imap = pmap.get_imap(instrument)
    header = { pmap.instrument_key : instrument.upper() }
    pars = imap.get_parkey_map().keys()
    for par in pars:
        header[par] = utils.condition_value(
            validate(request, par, r"[A-Za-z0-9\+\-.,*/;|{}\[\]:]*"))
    header["DATE-OBS"] = validate(request, "DATE-OBS", DATE_RE_STR)
    header["TIME-OBS"] = validate(request, "TIME-OBS", TIME_RE_STR)
    return bestrefs_results(request, pmap, header, instrument)

# ===========================================================================

@error_trap("certify_input.html")
@log_view
@login_required
# @profile
def certify_file(request):
    """View to return certify input form or process POST."""
    if request.method == "GET":
        return crds_render(request, "certify_input.html", requires_pmaps=True)
    else:
        return certify_post(request)

# @profile("certify5.stats")
def certify_post(request):
    """View fragment to process file certification POSTs."""

    context = get_recent_or_user_context(request)
    compare_old_reference = checkbox(request, "compare_old_reference")
    comparison_context = context if compare_old_reference else None
    remove_dir, uploaded_files = get_files(request)
    
    all_files = models.get_fileblob_map()

    jpoll_handler = jpoll_views.get_jpoll_handler(request)

    _disposition, certify_results = web_certify.certify_file_list(uploaded_files.items(), context=comparison_context, 
        compare_old_reference=compare_old_reference, push_status=jpoll_handler.write)

    blacklist_results = web_certify.get_blacklist_file_list(uploaded_files.items(), all_files=all_files)

    return crds_render(request, "certify_results.html", {
             "certify_results":certify_results,
             "blacklist_results":blacklist_results,
    })
    
# ===========================================================================

@error_trap("batch_submit_reference_input.html")
@log_view
@login_required
@instrument_lock_required
# @profile("batch_submit_reference.stats")
def batch_submit_references(request):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        return crds_render(request, "batch_submit_reference_input.html", {
                           "compare_old_reference" : "checked",
                           "auto_rename":""
                          }, requires_pmaps=True)
    else:
        return batch_submit_references_post(request)
    
def batch_submit_references_post(request):
    """View fragment to process file batch reference submnission POSTs."""
    # For the initial submission, pmap_name is predictive,  not definitive
    # It can change after confirmation if other subnmissions occured which
    # also generate it.   Batch submissions ALWAYS define this even if
    # they're not comparing to a prior context.
    pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    description = validate(request, "description", DESCRIPTION_RE)
    creator = validate(request, "creator", PERSON_RE)
    change_level = validate(request, "change_level", models.CHANGE_LEVELS)
    auto_rename = checkbox(request, "auto_rename")
    compare_old_reference = checkbox(request, "compare_old_reference")
    remove_dir, uploaded_files = get_files(request)
    locked_instrument = get_locked_instrument(request)
    
    jpoll_handler = jpoll_views.get_jpoll_handler(request)
    
    bsr = submit.BatchReferenceSubmission(pmap_name, uploaded_files, description, 
        user=request.user, creator=creator, change_level=change_level, 
        auto_rename=auto_rename, compare_old_reference=compare_old_reference,
        locked_instrument=locked_instrument, status_channel = jpoll_handler)
    
    disposition, new_references_map, new_mappings_map, reference_certs, mapping_certs, \
        mapping_diffs, collision_list = bsr.submit()
    
    # Map from old filenames to new filenames,  regardless of origin / purpose
    new_file_map = new_mappings_map.items() + new_references_map.items()
    
    bsr_results = {
                "pmap" : pmap_name,
                "pmap_mode" : pmap_mode,

                "new_file_map" : new_file_map,
                "uploaded_basenames" : uploaded_files.keys(),
                "submission_kind" : "batch submit",
                "title" : "Batch Reference Submit",
                "description" : description,
                "context_rmaps" : sorted(new_mappings_map.values()), 
                
#                "reference_certs" : reference_certs,
#                "mapping_certs" : mapping_certs, 
                "certify_results" : reference_certs + mapping_certs,
                "collision_list" : collision_list,
                
                "diff_results" : mapping_diffs,
                
                "should_still_be_locked" : locked_instrument,
                "requires_locking" : True,
                "lock_datestr" : locks.get_lock_datestr(locked_instrument, type="instrument", user=str(request.user)),

                "more_submits" : "/batch_submit_references/",
                "disposition": disposition,                
            }
    
    return render_repeatable_result(request, "batch_submit_reference_results.html", bsr_results,
                                    jpoll_handler=jpoll_handler)

# ============================================================================

@error_trap("base.html")
@login_required
@log_view
# critical to omit:   @instrument_lock_required
# @ilr will get a new lock.  critical that lock not expire prior to confirm.
def submit_confirm(request):
    """Accept or discard proposed files from various file upload and
    generation mechanisms.
    """
    button = validate(request, "button", "confirm|cancel|timeout")
    results_id = validate(request, "results_id", "\d+")
    locked_instrument = get_locked_instrument(request)

    jpoll_handler = jpoll_views.get_jpoll_handler(request)
    
    try:
        rmodel = models.RepeatableResultBlob.get(int(results_id))
        result = rmodel.parameters
    except Exception, exc:
        raise CrdsError("Error fetching result: " + results_id + " : " + str(exc))
    
    if result.get("disposition", None):
        raise CrdsError("This submission was already confirmed or cancelled.")

    usr = str(request.user)
    assert usr == result.user, "User mismatch: file Submitter='%s' and Confirmer='%s' don't match." % (usr, result.user)
    
    new_file_map = dict(result.new_file_map)
    new_files = new_file_map.values()
    
    if button == "confirm":   # assume confirmed unless lock fails
        disposition = "confirmed"
        if result.get("requires_locking", True):  # only verify locks if contexts are being generated.
            try:
                locks.verify_locked(type="instrument", name=locked_instrument, user=str(request.user), datestr=result["lock_datestr"])
            except locks.LockingError, exc:
                disposition = "cancelled due to: " + str(exc)
                log.info("Locking exception:", str(exc))
    elif button == "cancel":
        disposition = "cancelled by submitter"
    elif button == "timeout":
        disposition = "cancelled due to '%s' session lock timeout" % locked_instrument
        locks.release_locks(user=request.user)
        del_locked_instrument(request)

    confirmed = (disposition == "confirmed")
    if confirmed:
        final_pmap, context_map, collision_list = submit.submit_confirm_core( 
                confirmed, result.submission_kind, result.description, 
                new_files, result.context_rmaps, result.user,  result.pmap, result.pmap_mode, locked_instrument)

        rmodel.set_par("original_pmap", result.pmap)
        rmodel.set_par("pmap", final_pmap)
        rmodel.save()

        new_file_map = sorted(new_file_map.items() + context_map.items())
        generated_files = sorted([(old, new) for (old, new) in new_file_map if old not in result.uploaded_basenames])
        uploaded_files = [(old, new) for (old, new) in new_file_map if (old, new) not in generated_files]
        
        # rmaps specified for context generation but not uploaded or generated
        context_rmaps = [filename for filename in result.context_rmaps if filename not in dict(generated_files).values() + result.uploaded_basenames]
        
        confirm_results = dict(
            pmap_mode = result.pmap_mode,
            pmap = result.pmap,
            original_pmap = result.original_pmap,
            uploaded_files=uploaded_files,
            context_rmaps=context_rmaps,
            generated_files=generated_files,
            new_file_map=new_file_map,
            more_submits=result.more_submits,
            collision_list=collision_list)
        
        clear_uploads(request, result.uploaded_basenames)

    else:
        for new in new_files:
            with log.error_on_exception("Failed marking", repr(new), "as cancelled."):
                blob = models.FileBlob.load(new)
                blob.destroy()
        confirm_results = dict()
    
    models.RepeatableResultBlob.set_parameter(results_id, "disposition" , disposition)
    confirm_results["disposition"] = disposition
    confirm_results["confirmed"] = confirmed

    return render_repeatable_result(request, "confirmed.html", confirm_results, jpoll_handler=jpoll_handler)
    
# ===========================================================================

@error_trap("delete_references_input.html")
@log_view
@login_required
@instrument_lock_required
def delete_references(request):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        return crds_render(request, "delete_references_input.html", {
        }, requires_pmaps=True)
    else:
        return delete_references_post(request)
    
def delete_references_post(request):
    """View fragment to process file delete references POSTs."""

    pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    description = validate(request, "description", DESCRIPTION_RE)
    reject_type = validate(request, "reject_type", "reject|blacklist|both|no_reject")

    deleted_files = validate(request, "deleted_files", is_known_file_list)
    uploaded_files = { fname:rmap.locate_file(fname, models.OBSERVATORY) for fname in deleted_files }

    pmap = rmap.get_cached_mapping(pmap_name)
    pmap_references = pmap.reference_names()
    for deleted in deleted_files:
        assert deleted in pmap_references, "File " + repr(deleted) + " does not appear in context " + repr(pmap.name)
    
    locked_instrument = get_locked_instrument(request)
    
    drs = submit.DeleteReferenceSubmission(pmap_name, uploaded_files, description, 
        user=request.user, locked_instrument=locked_instrument)
    disposition, new_mappings_map, mapping_certs, mapping_diffs, collision_list = drs.submit()
    
    new_files = new_mappings_map.values()   # the new rmaps map
    final_pmap, context_map, collision_list = submit.submit_confirm_core( 
           True, "delete references", description, new_files, new_files, 
           str(request.user),  pmap_name, pmap_mode, locked_instrument, related_files=deleted_files)

    context_map.update(new_mappings_map)
    
    for file in deleted_files:
        models.AuditBlob.new(str(request.user), "delete references", file, description, 
                             details = repr(deleted_files + [final_pmap]))
    
    if reject_type != "no_reject":
        for file in deleted_files:
            set_file_enable_core(str(request.user), file, reject_type, "bad", description)
    
    del_results = {
                "pmap" : final_pmap,
                "original_pmap" : pmap_name,
                "pmap_mode" : pmap_mode,
                
                "deleted_files" : deleted_files,

                "context_map" : sorted(context_map.items()),
                "submission_kind" : "delete references",
                "description" : description,
                "context_rmaps" : sorted(new_mappings_map.values()),                 
                "collision_list" : collision_list,
                "disposition": disposition,                
            }
    
    return render_repeatable_result(request, "delete_references_results.html", del_results)

# ===========================================================================

@error_trap("add_existing_references_input.html")
@log_view
@login_required
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
    
def add_existing_references_post(request):
    """View fragment to process add existing references form POSTs."""

    pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    description = validate(request, "description", DESCRIPTION_RE)

    added_files = validate(request, "added_files", is_known_file_list)
    uploaded_files = { fname:rmap.locate_file(fname, models.OBSERVATORY) for fname in added_files }

    pmap = rmap.get_cached_mapping(pmap_name)
    pmap_references = pmap.reference_names()
    for added in added_files:
        assert added not in pmap_references, "File " + repr(added) + " is already in context " + repr(pmap.name)
    
    locked_instrument = get_locked_instrument(request)
    
    ars = submit.AddExistingReferenceSubmission(pmap_name, uploaded_files, description, 
                                                user=request.user, locked_instrument=locked_instrument)
    disposition, new_mappings_map, mapping_certs, mapping_diffs, collision_list = ars.submit()
    
    new_files = new_mappings_map.values()   # the new rmaps map
    final_pmap, context_map, collision_list = submit.submit_confirm_core( 
           True, "add references", description, new_files, new_files, 
           str(request.user),  pmap_name, pmap_mode, locked_instrument, related_files=added_files)

    context_map.update(new_mappings_map)
    
    for file in added_files:
        models.AuditBlob.new(str(request.user), "add references", file, description, 
                             details = repr(added_files + [final_pmap]))
    
    add_results = {
                "pmap" : final_pmap,
                "original_pmap" : pmap_name,
                "pmap_mode" : pmap_mode,
                
                "added_files" : added_files,

                "context_map" : sorted(context_map.items()),
                "submission_kind" : "add existing references",
                "description" : description,
                "context_rmaps" : sorted(new_mappings_map.values()),                 
                "collision_list" : collision_list,
                "disposition": disposition,                
            }
    
    return render_repeatable_result(request, "add_existing_references_results.html", add_results)

# ===========================================================================


# XXXX This is light-weight super-user functionality with minimal testing.

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
    description = validate(request, "description", DESCRIPTION_RE)
    context_name_map, collisions = submit.create_contexts(description, context_rmaps, str(request.user), pmap_name)
    return render_repeatable_result(request, "create_contexts_results.html", {
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
@instrument_lock_required
def submit_files(request, crds_filetype):
    """Handle file submission,  crds_filetype=reference|mapping."""
    if request.method == "GET":
        return crds_render(request, "submit_input.html", {
                    "crds_filetype" :  crds_filetype,
                    "compare_old_reference" : "checked",
                    "generate_contexts" : "checked",
                    "auto_rename":""
                }, requires_pmaps=True)
    else:
        return submit_files_post(request, crds_filetype)
    
def submit_files_post(request, crds_filetype):
    """Handle the POST case of submit_files, returning dict of template vars."""
    # crds_filetype constrained by RE in URL to 'mapping' or 'reference'.
    observatory = get_observatory(request)
    compare_old_reference = checkbox(request, "compare_old_reference")
    generate_contexts = checkbox(request, "generate_contexts")
    auto_rename = checkbox(request, "auto_rename")
    if generate_contexts or compare_old_reference:
        pmap_mode, pmap_name = get_recent_or_user_mode_and_context(request)
    else:
        pmap_mode, pmap_name = None, None
    description = validate(request, "description", DESCRIPTION_RE)
    creator = validate(request, "creator", PERSON_RE)
    change_level = validate(request, "change_level", models.CHANGE_LEVELS)            
    remove_dir, uploaded_files = get_files(request)
    locked_instrument = get_locked_instrument(request)

    assert not generate_contexts or locked_instrument,  "Can't generate contexts in unlocked mode."
    
    jpoll_handler = jpoll_views.get_jpoll_handler(request)
    
    simple = submit.SimpleFileSubmission(pmap_name, uploaded_files, description, user=request.user,  
        creator=creator, change_level=change_level, auto_rename=auto_rename, 
        compare_old_reference=compare_old_reference, locked_instrument=locked_instrument,
        status_channel=jpoll_handler)
    
    disposition, certify_results, new_file_map, collision_list, context_rmaps = simple.submit(crds_filetype, generate_contexts)    

    rdict = {
                "crds_filetype": crds_filetype,
                "collision_list" : collision_list,

                "context_rmaps" : context_rmaps,
                "new_file_map" : sorted(new_file_map.items()),
                "uploaded_basenames" : uploaded_files.keys(),
                "submission_kind" : "submit file",
                "title" : "Submit File",
                "description" : description,
                "pmap" : pmap_name,
                "pmap_mode" : pmap_mode,
                
                "certify_results" : certify_results,
                "more_submits" : "/submit/" + crds_filetype + "/",
                "requires_locking" : generate_contexts,
                "should_still_be_locked": locked_instrument,
                "lock_datestr" : locks.get_lock_datestr(locked_instrument, type="instrument", user=str(request.user)),
                
                "disposition" : disposition,
    }
    
    return render_repeatable_result(request, 'submit_results.html', rdict, jpoll_handler=jpoll_handler)

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

@error_trap("difference_input.html")
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
    else:
        file1_orig, file1_path = handle_known_or_uploaded_file(
            request, "filemode1", "file_known1", "file_uploaded1")
        file2_orig, file2_path = handle_known_or_uploaded_file(
            request, "filemode2", "file_known2", "file_uploaded2")
    
    if rmap.is_mapping(file1_orig):  # compute files for nested rmap differences
        upload_tuples, logical_errors = mapping_upload_tuples(file1_orig, file2_orig, file1_path, file2_path)
    else:   # references
        upload_tuples = [(file1_orig, file2_orig, file1_path, file2_path)]
        logical_errors = []
        
    # log.info("upload_tuples:", upload_tuples)
                
    diff_results = web_difference.mass_differences(upload_tuples)
    
    # log.info("diff_results:", log.PP(diff_results))

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

@error_trap("base.html")
@log_view
def browse_known_file(request, filename):
    """special view which accepts browse file from a URL parameter,  required
    by cross links like /browse/some_file.rmap
    """
    try:
        blob = models.FileBlob.load(filename)
        browsed_file = blob.pathname
        related_actions = models.AuditBlob.related_to(filename)
    except LookupError:
        raise CrdsError("Can't find " + repr(filename))
    
    if rmap.is_mapping(filename):
        file_contents = browsify_mapping2(filename, browsed_file)
    else:
        file_contents = browsify_reference(browsed_file)
        
    used_by_files = list(uses.uses([filename], blob.observatory))
    
    if blob and blob.type == "reference":
        context = models.get_default_context(blob.observatory)
        match_paths = matches.find_full_match_paths(context, filename)
        match_paths = [flatten(path) for path in match_paths]
#        try:
#            certify_results = web_certify.captured_certify(filename, blob.pathname, check_references=True, context=context)
#        except Exception, exc:
#            log.warning("certify failed for", blob.pathname)
#            certify_results = None
    else:
        match_paths = []
        # Not certified against a context because the default context will generally be from the "future"
        # and will therefore typically show a number of regressions.   Another option here which I'm skipping
        # for now is certifying against the mapping that `filename` was derived_from.
#        certify_results = web_certify.captured_certify(filename, blob.pathname, check_references=False)

    return crds_render(request, "browse_results.html", { 
             "fileblob" : blob,
             "observatory" : blob.observatory,
             "related_actions": related_actions,
             "used_by_files" : used_by_files,
             "match_paths" : match_paths,
             "file_contents": file_contents,
             "browsed_file": filename,
             'prior_file_versions' : get_prior_file_versions(blob)
    })

def get_prior_file_versions(blob, count=20):
    """Returns a list of the last `count` files used in the derivation
    of the file represented by FileBlob `blob`.   May be < count filenames.
    """
    versions = []
    while count:
        prior = blob.derived_from
        try:
            blob = models.FileBlob.load(prior)
        except LookupError:
            break
        versions.append(prior)
        count -= 1
    return versions

def browsify_mapping2(filename, browsed_file):
    """Format a CRDS mapping file as colorized and cross-linked HTML."""
    contents = ""
    try:
        lines = open(browsed_file).readlines()
    except OSError:
        return ["<h3 class='error'>File " 
                "<span class='grey'>%s<span> not found</h3>" % (filename,)]
    lines = ["<pre class='program'>"] + [l.rstrip() for l in lines] + ["</pre>"]
    return "\n".join(lines)

def browsify_mapping(filename, browsed_file):
    """Format a CRDS mapping file as colorized and cross-linked HTML."""
    contents = ""
    try:
        linegen = open(browsed_file).readlines()
    except OSError:
        return ["<h3 class='error'>File " 
                "<span class='grey'>%s<span> not found</h3>" % (filename,)]

    for line in linegen:
        if line.strip():
            line = browsify_mapping_line(line)
            # mapping or reference filename --> /browse/<file> link
            line = re.sub(r"'(" + FILE_RE + ")'",
                  r"""<a href='/browse/\1'>'\1'</a>""",
                  line)
            contents += line
    return contents

def browsify_mapping_line(line):
    """Markup one line of a CRDS mapping for use in HTML display and editing."""
    
    # header
    line = re.sub(r"(header|selector)(\s*=\s*)",
                  r"<span class='green'>\1</span>\2",
                  line)
    # '2011-02-07 08:21:00' : 'v3b1842dj_drk.fits',
    if re.search(r"'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d'\s*:", line):
        line = "<p class='useafter'>" + line.strip() + "</p>\n"
    elif re.search(r"UseAfter", line) or line.strip() == "}),":
        line = "<p class='match'>" + line.strip() + "</p>\n"
    elif re.match(r"^\s+'\w+'\s+:", line):
        line = "<p class='header'>" + line.strip() + "</p>\n"
    else:
        line = "<p>" + line.strip() + "</p>\n"

    # useafter date
    line = re.sub(r"('\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d')",
                  r"<span class='datetime'>\1</span>",
                  line)
    
    # Match, UseAfter  ({    --> <div> <span>
    line = re.sub(r".*header</span>.*",
                  r"<br/>\n\n<div class='header'>\n" + line.rstrip(),
                  line)

    line = re.sub(r".*selector</span>.*",
                  r"<br/>\n\n<div class='selector'>\n" + line.rstrip(),
                  line)

    line = re.sub(r"(.*)(Match)(\(.*)",
                  r"\1<span class='green'>\2</span>\3",
                  line)

    line = re.sub(r"(.*)(UseAfter)(\(.*)",
                  r"<div class='match'>\1<span class='green'>\2</span>\3",
                  line)
    
    # }  -->  } </div>
    line = re.sub(r"(.*\}.*)",  r"\1\n</div>\n", line)
    
    return line

def browsify_reference(browsed_file):
    """Format a CRDS reference file for HTML display.   Return HTML lines.
    """
    ref_blob = models.FileBlob.load(os.path.basename(browsed_file))
    default_context = models.get_default_context(ref_blob.observatory)
    mapping = rmap.get_cached_mapping(default_context)
    
    header = {}
    with log.error_on_exception("Failed getting minimum header for", repr(browsed_file)):
        header = mapping.get_minimum_header(browsed_file)
    header2 = {}
    with log.error_on_exception("Failed getting extra keys for", repr(browsed_file)):
        header2 = data_file.get_unconditioned_header(browsed_file, needed_keys=["APERTURE","USEAFTER"])
    if header:
        header.update(header2)
        output  = "<b>Header Parameters</b>\n"
        output += "<br/>\n"
        output += "<br/>\n"
        output += "<table border='1'>\n"
        for key, value in sorted(header.items()):
            if value != "UNDEFINED":
                output += "<tr><td class='label'>%s</td><td>%s</td></tr>\n" % (key, value)
        output += "</table>\n"
    else:
        output = "<p class='error'>File header unavailable for '%s'</p>" % str(browsed_file)

    output += "<br/>\n"
    
    if browsed_file.endswith(".fits"):
        try:
            fits_info = finfo(browsed_file)[1] + "\n"
        except Exception, exc:
            output += "<p class='error'>FITS info unavailable: '%s'</p>" % str(exc)
        else:
            output += "<b>FITS Info</b>\n"
            output += "<pre>\n"
            lines = fits_info.split("\n")
            if lines[0].lower().startswith("filename"):
                lines = lines[1:]
            output += "\n".join(lines)
            output += "</pre>\n"

    return output


@capture_output
def finfo(filename):
    """Capture the output from the pyfits info() function."""
    pyfits.info(filename)


# ===========================================================================

# @profile('recent_activity.stats')
@error_trap("recent_activity_input.html")
@log_view
# @login_required
def recent_activity(request):
    """recent_activity displays records from the AuditBlob database."""
    if request.method == "GET":
        return crds_render(request, "recent_activity_input.html")
    else:
        return recent_activity_post(request)

def recent_activity_post(request):
    """View fragment handling recent_activity POST case."""
    action = validate(
        request, "action", models.AUDITED_ACTIONS+[r"\*"])
    observatory = validate(
        request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate(
        request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate(
        request, "filekind", models.FILEKINDS+[r"\*"])
    extension = validate(
        request, "extension", models.EXTENSIONS+[r"\*"])
    filename = validate(
        request, "filename", r"[A-Za-z0-9_.\*]+")
    user = validate(
        request, "deliverer_user", r"[A-Za-z0-9_.\*]+")
    filters = {}
    for var in ["action", "instrument", "filekind", "extension", "user"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_activities = models.AuditBlob.filter(**filters)[::-1]
    
    # Skip .cat files since they're not deliverable files and don't currently browse.
    filtered_activities = [blob for blob in filtered_activities if not blob.filename.endswith((".cat",))]
    
    # Filter filenames with UNIX style name globbing
    filtered_activities = [blob for blob in filtered_activities if fnmatch.fnmatch(blob.filename, filename)]
    
    # Skip mass import actions by default since for HST there are 14k+ of them
    if action == "*":
        filtered_activities = [blob for blob in filtered_activities if blob.action != "mass import"]
    
    return crds_render(request, "recent_activity_results.html", {
                "filters": filters,
                "filtered_activities" : filtered_activities,
            })

# ===========================================================================

# @profile('delivery_status.stats')
@error_trap("base.html")
@log_view
@login_required
def delivery_status(request):
    """Show a table of the catlog files reflecting file deliveries and their status."""
    
    auditblobs = [ blob for blob in models.AuditBlob.objects.all() if blob.thaw().filename.endswith(".cat") ]
    fileblobs = models.get_fileblob_map()
    
    catalog_info = []
    for audit in auditblobs:
        audit.thaw()
        files = []
        status = "delivery corrupt"
        status_class="error"
        with log.error_on_exception("Failed interpreting catalog", repr(audit.filename)):
            files = sorted(open(os.path.join(sconfig.CRDS_CATALOG_DIR, audit.filename)).read().splitlines())
            status = fileblobs[files[0]].interpret_catalog_link()
            status_class = fileblobs[files[0]].status_class
        catalog_info.append(
                dict(date=audit.date,
                     action=audit.action,
                     user=audit.user,
                     description=audit.why,
                     files=files,
                     catalog=audit.filename,
                     status=status,
                     status_class=status_class)
            )
    delivery_status = list(reversed(sorted(catalog_info, key=lambda k: k["date"])))
    log.info("delivery_status catalog info:", delivery_status)
        
    return crds_render(request, "delivery_status.html", {
            "delivery_status": delivery_status,
    })

# ===========================================================================

# @profile("browse_db.stats")
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
    observatory = validate(
        request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate(
        request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate(
        request, "filekind", models.FILEKINDS+[r"\*"])
    extension = validate(
        request, "extension", models.EXTENSIONS+[r"\*"])
    filename = validate(
        request, "filename", FILE_RE + r"|\*")
    deliverer_user = validate(
        request, "deliverer_user", [r"\*"] + usernames())
    status = validate(
        request, "status",  r"[A-Za-z0-9_.\*]+")
    select_bad_files = checkbox(request, "select_bad_files")
    show_defects = checkbox(request, "show_defects")
    
    filters = {}
    for var in ["instrument", "filekind", "extension",
                "filename", "deliverer_user", "status"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
            
    filtered_db = models.FileBlob.filter(**filters)
    
    if select_bad_files:
        filtered_db = [ blob for blob in filtered_db if blob.get_defects() ]
    
    if request.is_ajax():
        table = render_browse_table_json(request, filtered_db, show_defects)
        response = JSONResponse(table, {}, response_mimetype(request))
        response['Content-Disposition'] = 'inline; filename=files.json'
    else:
        # table = render_browse_table(request, filtered_db, show_defects)
        table_data = render_browse_table_data(request, filtered_db, show_defects)
        table_data = to_datatables(table_data)
        table_json = json.dumps(table_data)
        return crds_render(request, "browse_db_results.html", {
                    "filters": filters,
                    "filtered_db" : filtered_db,
                    "table_json" : table_json,
                    "observatory" : observatory,
                })
    
def render_browse_table(request, filtered_db, show_defects):
    """Generate the HTML for the search results table."""
    super = request.user.is_superuser
    authenticated = request.user.is_authenticated()
    thead = html.thead(
        html.tr(
            html.th("delivery date") +
            html.th("name") +
            html.th("aperture") +
            html.th("useafter date") +
            html.th("status") +
            html.th("description") +
            html.th("instrument") + 
            html.th("reference type") +
            (html.th("deliverer") if authenticated else "") +
            (html.th("defects") if show_defects else "")
        )
    )
    rows = []
    for db in filtered_db:
        tr = html.tr(
            html.td(stdtags.minutes(db.delivery_date)) +
            html.td(stdtags.browse(db.name)) +
            html.td(db.aperture) +
            html.td(stdtags.minutes(db.useafter_date)) +
            html.td(db.status, status_class=db.status_class) +
            html.td(db.description) +
            html.td(db.instrument) + 
            html.td(db.filekind) +
            (html.td(db.deliverer_user) if authenticated else "") +
            (html.td(repr(db.get_defects())) if show_defects else "")
        )
        rows.append(tr)
    tbody = html.tbody("\n".join(rows))
    table = html.table("\n".join([thead, tbody]), id="crds_files_table")
    return table
    
def render_browse_table_data(request, filtered_db, show_defects):
    """Generate the HTML for the search results table."""
    super = request.user.is_superuser
    authenticated = request.user.is_authenticated()
    header = ["delivery date",
            "activation date",
            "useafter date",
            "name",
            "aperture",
            "status",
            "description",
            "instrument", 
            "reference type",
            "deliverer" if authenticated else "",
            "defects" if show_defects else "",
        ]
    rows = []
    for db in filtered_db:
        rows.append([
            stdtags.minutes(db.delivery_date),
            stdtags.minutes(db.activation_date),
            stdtags.minutes(db.useafter_date),
            stdtags.browse(db.name),
            db.aperture,
            db.status,
            db.description,
            db.instrument, 
            db.filekind,
            db.deliverer_user if authenticated else "",
            repr(db.get_defects()) if show_defects else "",
        ])
    return {"header":header, "data": rows}

def to_datatables(json_table):
    """Filter a header/data object into a jQuery datatables representation."""
    return dict(
            aoColumns = [ { "sTitle" : col } for col in json_table["header"] ],
            aaData = json_table["data"],
            )
    
# ============================================================================

@error_trap("base.html")
@log_view
def brokered_get(request, filename):
    """Brokered get checks that a file exists in CRDS and is available and then
    redirects the request to an optimized download server.   The optimized
    download might be owned by the archive (TBD) or it might be handled
    directly by CRDS Apache,  or possibly by servers better optimized than Apache.
    
    From a protocol standpoint,  redirecting is superior to asking for the URL
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

    return HttpResponseRedirect(url)

# @condition(etag_func=None)
@error_trap("base.html")
@log_view
def get_file_data(request, filename):
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
            except IOError, exc:
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
            for filename, path in files.items():
                tar.add(path, arcname=filename)
            tar.close()
            os.chmod(bundle_path, 0640)
    return bundle_path
    
def cached_bundle_path(request, arch_extension):
    """Compute the sha1sum of the filenames requested for a bundle to see
    if a bundle is already cached.
    """
    names = arch_extension # archive format is important,  download filename isn't
    for var in request.GET:
        if var.startswith("file"):
            name = validate(request, var, FILE_RE)
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
def version_info(request):
    """Output a page with a table of software component versions."""    
    return crds_render(request, "version_info.html", {
                "version_info" : sorted(versions.get_all_versions().items()),
                "crds_env" : sorted(config.get_crds_env_vars().items()),
            })

# ============================================================================

"""File enable/disable has somewhat complicated semantics due to the operation of CRDS
in a distributed fashion.   The core issue is that the reject and blacklist flags 
which appear in the CRDS DB catalog are not automatically distributed,  so checking
for bad files by remote clients takes extra work.   This is also complicatd by a 
design ambivalence and two kinds of file rejects:  reject and blacklist,  intransitve
and transitive respectively.

As things have turned out,  the most useful notion is the transitive form,  blacklisting
which taints the contexts which contain blacklisted files as blacklisted also.
"""

@error_trap("blacklist_input.html")
@log_view
@login_required
def set_file_enable(request):
    """Serve the blacklist input form or process the POST."""
    if request.method == "GET":
        return crds_render(request, "blacklist_input.html")
    else:
        return set_file_enable_post(request)

# TODO Add "archive/catalog" action resulting from blacklisting

def set_file_enable_post(request):
    """View fragment to process the blacklist POST."""
    observatory = get_observatory(request)
    blacklist_roots = validate(request, "file_known", is_known_file_list)
    # reject_type = validate(request, "reject_type", "reject|blacklist|both")
    reject_type = "both"
    badflag = validate(request, "badflag", "bad|ok")
    why = validate(request, "why", DESCRIPTION_RE)

    if badflag == "bad":
        for blacklist_root in blacklist_roots:
            check_bad_file(blacklist_root)
    
    affected_files = set()
    for blacklist_root in blacklist_roots:
        affected_files = affected_files.union(
            set(set_file_enable_core(str(request.user), blacklist_root, reject_type, badflag, why)))
    
    return crds_render(request, "blacklist_results.html", 
                  { "affected_files": sorted(list(affected_files)) })
    
def check_bad_file(blacklist_root):
    """Make sure `blacklist_root` does not appear in the operational context."""
    pmap_name = models.get_default_context(state="operational")
    pmap = rmap.get_cached_mapping(pmap_name)
    assert blacklist_root not in pmap.mapping_names() + pmap.reference_names(), \
        "File '{}' is in the current operational context '{}'.  Create a new context which does not contain " \
        "it and make that context operational.  Then mark '{}' as 'bad'." \
        .format(blacklist_root, pmap_name, blacklist_root)

def set_file_enable_core(user, blacklist_root, reject_type, badflag, why):
    """Set's file reject state of `blacklist_root` based on `reject_type` and `badflag`
    and creates an AuditBlob listing `why`.
    """
    if reject_type in ["blacklist","both"]:
        affected_files = models.transitive_blacklist(blacklist_root, badflag)
    else:
        affected_files = [blacklist_root]

    if reject_type in ["reject", "both"]:
        models.set_reject(blacklist_root, badflag=="bad")

    instrument, filekind = utils.get_file_properties(models.OBSERVATORY, blacklist_root)

    models.AuditBlob.new(
        user, "blacklist", blacklist_root, why, 
        "marked as " + srepr(badflag.upper()),
        instrument=instrument, filekind=filekind)

    return affected_files

# ===========================================================================

@error_trap("base.html")
@log_view
@login_required
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
            }, requires_pmaps=True)
    else:
        new_default = get_recent_or_user_context(request)
        context_type = validate(request, "context_type", models.CONTEXT_TYPES)
        description = validate(request, "description", DESCRIPTION_RE)

        old_default = update_default_context(new_default, description, context_type, str(request.user))
        
        return crds_render(request, "set_default_context_results.html", {
                    "new_default" :  new_default,
                    "old_default" :  old_default,
                    "context_type" : context_type,
                })

def get_context_pmaps(context_map):
    """Return a list of option tuples for rendering HTML to choose context
    pmaps (last 10). This defines what users will see for the context HTML 
    drop-down menu.
    """
    context_pmaps = {}
    files = models.FileBlob.objects.all()
    for f in files:
        if f.name in context_map.values():
            f.thaw()
            context_pmaps[f.name] = pmap_label(f)
    return context_pmaps

def update_default_context(new_default, description, context_type, user):
    """Do the work of choosing a new context."""
    is_available_file(new_default)
    old_default = models.get_default_context(models.OBSERVATORY, state=context_type)
    if old_default == new_default:
        raise CrdsError(srepr(old_default) + " is already in use for the " + srepr(context_type) + " context.")
    pmap = rmap.get_cached_mapping(new_default)
    blobs = models.get_fileblob_map()
    pmap_names = pmap.mapping_names() + pmap.reference_names()
    bad_files = [ name for name in pmap_names if blobs[name].rejected or blobs[name].blacklisted ]
    if bad_files and context_type == "operational":
        raise CrdsError("Context " + srepr(new_default) + 
                        " contains known bad files and cannot be made the default (first 3): " + repr(bad_files[:3]))
    models.set_default_context(new_default, observatory=models.OBSERVATORY, state=context_type, description=description)
    models.AuditBlob.new(user, "set default context", 
                         new_default, description, 
                         context_type + " context changed from " +  
                         srepr(old_default) + " to " + srepr(new_default))
    return old_default

@error_trap("base.html")
@log_view
def display_context_history(request):
    """Change the default context presented to users as the nominal start from
    which to derive new contexts.
    """
    history = models.get_context_history(observatory=models.OBSERVATORY, state="operational")
    context_blobs = { blob.name:blob for blob in models.FileBlob.objects.all() if blob.name.endswith(".pmap") }
    history_tuples = [ (hist, context_blobs[hist.context]) for hist in history ]
    return crds_render(request, "display_context_history.html", {
            "history" : history,
            "history_tuples" : history_tuples,
        }, requires_pmaps=False)

# ============================================================================

@error_trap("base.html")
@log_view
def context_table(request, mapping, recursive="10"):
    if re.match("operational|edit", mapping):
        mapping = models.get_default_context(state=mapping)
    is_mapping(mapping)
    recursive = int(recursive)
    if request.is_ajax():
        m = rmap.get_cached_mapping(mapping)
        return HttpResponse(m.tojson(), mimetype='application/json')
    else:
        pars = get_context_table_parameters(request, mapping)
        return crds_render(request, "context_table.html", pars, requires_pmaps=False)
        
def get_context_table_parameters(request, pmap):
    """Return the parameters required to display a context table for `mapping`."""
    try:
        if re.match("operational|edit", pmap):
            pmap = models.get_default_context(state=pmap)
        is_pmap(pmap)
        p = rmap.get_cached_mapping(pmap)
        return {
            "pmap" : p.todict(),
            "mapping_type" : p.header["mapping"],
        }    
    except Exception, exc:
        log.error("Failure in get_context_table_parameters:", str(exc))
        return {}
        
if sconfig.DEBUG:
    
    @capture_output
    def runit(mode, command):
        # log.info("DEBUG COMMAND:", repr(command))
        try:
            if mode == "eval":
                result = eval(command, locals(), globals())
            else:
                exec command in locals(), globals()
                result = None
        except Exception as exc:
            result = "EXCEPTION: " + str(exc)
        # log.info("DEBUG RESULT:", result)
        return result

    @error_trap("base.html")
    @log_view
    @superuser_login_required
    def debug_command(request):
        if request.method == "GET":
            return crds_render(request, "command_result.html")
        else:
            command = str(request.POST["command"].strip())
            mode = validate(request, "mode", "exec|eval")
            result, output = runit(mode, command)
            return crds_render(request, "command_result.html", dict(command_result=result, command_output=output))
    
