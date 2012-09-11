"""This module defines the Django view functions which respond to HTTP requests
and return HTTP response objects.
"""

# Create your views here.
import sys
import os.path
import re
import cProfile
import cStringIO
import pprint
import traceback
import datetime
import tarfile
import mimetypes
import tempfile
import shutil
import glob

# from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.shortcuts import render as django_render
from django.http import HttpResponse
from django.template import RequestContext
import django.utils.safestring as safestring

import django.contrib.auth
import django.contrib.auth.models
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.datastructures import DotExpandedDict

import pyfits

from crds import (rmap, utils, certify, timestamp, uses, matches, newcontext, 
                  refactor, checksum, pysh, compat, log)

from crds.timestamp import (is_datetime, DATE_RE_STR, TIME_RE_STR, DATETIME_RE_STR)
from crds import CrdsError

import crds.server.config as config
from crds.server.interactive import (models, database)
from crds.server.interactive.models import FieldError, MissingInputError

import crds.server.jsonapi.views as jsonapi_views

from . import versions

HERE = os.path.dirname(__file__) or "./"

# ===========================================================================
def srepr(obj):
    """Mostly for formatting unicode strings for exceptions,  to get rid of the
    annoying Python-2.x u-prefix on unicode reprs.
    """
    return repr(str(obj))

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

def validate_post(request, variable, pattern):
    """Check a POST `variable` from `request`,  ensuring that it meets the
    check_value() conditions specified by `pattern`.
    """
    value = str(request.POST[variable]).strip()
    return check_value(value, pattern, "Invalid value " + srepr(value) + 
                                        " for " + srepr(variable))
def validate_get(request, variable, pattern):
    """Check a GET `variable` from `request`,  ensuring that it meets the
    check_value() conditions specified by `pattern`.
    """
    value = str(request.GET[variable]).strip()
    return check_value(value, pattern, "Invalid value " + srepr(value) + 
                                        " for " + srepr(variable))

# ===========================================================================

# "pattern" functions for validate_post/get

FILE_RE = r"\w+(\.fits|\.pmap|\.imap|\.rmap|\.r\d[hd])"
DESCRIPTION_RE = r"[A-Za-z0-9._ ]+"
GEIS_HEADER_RE = r"\w+(\.r\dh)"
PERSON_RE = r"[A-Za-z_0-9\.@]*"
DATASET_ID_RE = r"\w+"
URL_RE = r"(/[A-Za-z0-9_]?)+"

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
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise CrdsError("No database entry for " + srepr(filename) + ".")
    assert blob.state != "uploaded", \
        "File " + srepr(filename) + " has not yet been submitted."
    return filename

def is_available_file(filename):
    """Verify that `filename` identifies a file already known to CRDS and
    meets any requirements for distribution.
    """
    if not re.match(FILE_RE, filename):
        raise CrdsError("Invalid filename " + srepr(filename))
    try:
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise CrdsError("No database entry for " + srepr(filename) + ".")
    assert blob.available, \
        "File " + srepr(filename) + " is not yet available."
    assert not blob.blacklisted, \
        "File " + srepr(filename) + " has been blacklisted and should no longer be used."
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
    return validate_post(request, "observatory", models.OBSERVATORIES)

def usernames():
    """Return a list of all the usernames defined in the database."""
    try:
        return [str(x) for x in django.contrib.auth.models.User.objects.filter()]
    except Exception:  # provide a workable choice if it fails.
        return ["*"]

# ===========================================================================

def crds_render(request, template, dict_=None, requires_pmaps=True):
    """Render a template,  making same-named inputs from request available
    for echoing.
    """
    statuses = ["*"] + models.FILE_STATUS_MAP.keys()
    statuses.remove("uploaded")
    
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
        
        "auto_rename" : False,
    }
    
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

    # echo escaped inputs.
    for key, value in request.GET.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.POST.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.FILES.items():
        rdict[key] = safestring.mark_for_escaping(value)

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
            
    # log.write("rendering:", srepr(template), log.PP(rdict))
            
    return django_render(request, template, rdict)

# ===========================================================================

def handle_known_or_uploaded_file(request, modevar, knownvar, uploadvar):
    """Process file variables for a file which is either known to CRDS
    and simply named,  or which is uploaded by the user.
    
    Return (uploaded_flag, name_on_users_system,  temporary_file_path)
    """
    if request.POST[modevar] == knownvar:
        # certified_file is a basename,  but CRDS figures out where it is.
        original_name = validate_post(request, knownvar, is_known_file)
        filepath = get_known_filepath(original_name)
        uploaded = False
    else:
        ufile = get_uploaded_file(request, uploadvar)
        filepath = ufile.temporary_file_path()
        original_name = ufile.name
        uploaded = True
    return uploaded, str(original_name), str(filepath)

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
    returning:   { original_name : file_path }
    """
    file_mode = validate_post(request, "file_mode", ["file_uploaded", "file_local_dir"])
    if file_mode == "file_uploaded":
        files = request.FILES.getlist("file_uploaded")
        if not files:
            raise CrdsError("No files specified.")
        uploads = { f.name : f.temporary_file_path() for f in files }
        remove_dir = None
    else:
        dir = validate_post(request, "file_local_dir", "[A-Za-z0-9_]+")
        dir = os.path.join(config.CRDS_INGEST_DIR, dir)
        uploads = { os.path.basename(f) : f for f in glob.glob(dir + "/*") }
        remove_dir = dir
    for f in uploads:
        if rmap.is_mapping(f):
            checksum.update_checksum(uploads[f])
    if not uploads:
        raise CrdsError("No input files were specified.")
    return remove_dir, uploads

def get_server_ingest_dirs():
    """Return a list of choice tuples of directory names defined under the
    CRDS root ingest directory.
    """
    dirs = sorted(glob.glob(config.CRDS_INGEST_DIR + "/*"))
    dirs = [os.path.basename(d) for d in dirs]
    return zip(dirs,dirs)

def get_known_filepath(filename):
    """Given the basename of a mapping or reference file, `file`,
    determine the full path of the file on the server.
    """
    try:
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise FieldError("CRDS doesn't know about file " + srepr(filename))
    return blob.pathname

def upload_file(ufile, where):
    """Copy the Django UploadedFile to it's permanent location.
    Handle's <input type='file'> part 2.
    """
    utils.ensure_dir_exists(where)
    destination = open(where, 'wb+')
    for chunk in ufile.chunks():
        destination.write(chunk)
    destination.close()

def remove_temporary(filepath):
    """Attempt to remove `filepath`.  Ignore errors."""
    try:
        assert filepath.startswith(config.FILE_UPLOAD_TEMP_DIR), \
            "ERROR -- attempt to delete from Central Store"
        # os.remove(filepath)
    except OSError:
        pass

# ===========================================================================

class ServerError(Exception):
    """Uncaught exception which will be returned as HTTP 500"""
    
def superuser_login_required(func):
    @login_required
    def _inner(request, *args, **keys):
        if not request.user.is_superuser:
            raise CrdsError(str(request.user) + " is not a super user.")
        return func(request, *args, **keys)
    _inner.func_name = func.func_name
    return _inner

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
            except AssertionError, exc:
                return render_error(request, args, keys, exc, template)
            except CrdsError, exc:
                return render_error(request, args, keys, exc, template)
            except FieldError, exc:
                return render_error(request, args, keys, exc, template)
        trap.func_name = func.func_name
        return trap
    return decorator

def render_error(request, args, keys, exc, template):
    """Render `template` with an error message."""
    msg = "ERROR: " + str(exc)
    pars = dict(keys.items() + [("error_message", msg)])
    return crds_render(request, template, pars)

def log_view(func):
    """log() captures view inputs, output, and response to a log file.
    It should be called inside any error_trap() decorator so that it 
    executes before error_trap() absorbs many exceptions.
    """
    def dolog(request, *args, **keys):
        """trap() is bound to the func parameter of decorator()."""        
        log.write() # start with blank line to make concat logs readable
        log.write("REQUEST:", request.path, request.method)
#        log.write("META:", repr(request.META), stdout=None)
        if request.GET:
            log.write("GET:",   repr(request.GET))
        if request.POST:
            log.write("POST:",  repr(request.POST))
#        if request.COOKIES:
#            log.write("COOKIES:", repr(request.COOKIES), stdout=None)
        if request.FILES:
            log.write("FILES:", repr(request.FILES))
        log.write("OUTPUT:")
        try:    
            response = func(request, *args, **keys)
#            log.write("RESPONSE:\n" + response.content, stdout=None)
            return response
        except Exception, exc:
            log.write("EXCEPTION REPR:", repr(exc))
            log.write("EXCEPTION STR:", str(exc))
            log.write("EXCEPTION TRACEBACK:")
            info = sys.exc_info()
            tb_list = traceback.extract_tb(info[2])
            for line in traceback.format_list(tb_list):
                log.write(line.strip(), time=False)
            raise
        finally:
            pass
    dolog.func_name = func.func_name
    return dolog

# ===========================================================================
PROFILE_DECORATOR_RESULT = None
def profile(filename=None):
    """Decorate a view with @profile to run cProfile when the view is accessed.
    """
    def decomaker(func):
        """Decorator function maker
        """
        def profile_core(*args, **keys):
            """profile_request runs the runit() hack under the profiler and
            extracts the function result from a global.
            """
            def runit():
                """executes a function and stores the result globally."""
                global PROFILE_DECORATOR_RESULT
                PROFILE_DECORATOR_RESULT = func(*args, **keys)
            cProfile.runctx("runit()", locals(), locals(), filename=filename)
            return PROFILE_DECORATOR_RESULT
        return profile_core
    return decomaker

# ===================================================================

def capture_output(func):
    """Decorate a function with @capture_output to make it capture and return
    stdout/stderr as part of it's result.   Returns (original_result, outlines)
    """
    def captured(*args, **keys):
        """Temorarily re-assign stdout/stderr to a StringIO, run func,
        return captured output.
        """
        oldout, olderr = sys.stdout, sys.stderr
        out = cStringIO.StringIO()
        sys.stdout, sys.stderr = out, out
        try:
            result = func(*args, **keys)
        finally:
            sys.stdout, sys.stderr = oldout, olderr
        out.seek(0)
        return result, out.read()
    return captured

# ===========================================================================
# ===========================================================================
# ===========================================================================

def index(request):
    """Return the top level page for all of interactive CRDS."""
    return crds_render(request, "index.html", {}, requires_pmaps=False)

# ===========================================================================
from django.contrib.auth.views import login as django_login

@error_trap("base.html")
def login(request):
    if request.method == 'POST':
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
            return django_login(request, "login.html")
        else:
           raise CrdsError("Please enable cookies and try again.")
    else:
        request.session.set_test_cookie()
        return django_login(request, "login.html")


def logout(request):
    """View to get rid of authentication state and become nobody again."""
    django.contrib.auth.logout(request)
    return redirect("/")
        
# ===========================================================================

@error_trap("bestrefs_index2.html")
def bestrefs(request):
    """View to get the instrument context for best references."""
    if request.method == "GET":
        return crds_render(request, "bestrefs_index2.html", {})
    else:
        return bestrefs_post(request)

def bestrefs_post(request):
    """View to get best reference dataset parameters."""
    context = get_recent_or_user_context(request)
    pmap = rmap.get_cached_mapping(context)
    dataset_mode = validate_post(
        request, "dataset_mode", "dataset_archive|dataset_uploaded|dataset_local")
    if dataset_mode == "dataset_uploaded":
        uploaded_file = get_uploaded_file(request, "dataset_uploaded")
        dataset_path = uploaded_file.temporary_file_path()
        dataset_name = uploaded_file.name
        remove_temp_flag = True
        # base on the context and datset,  compute best references
        header = pmap.get_minimum_header(dataset_path, original_name=dataset_name)
    elif dataset_mode == "dataset_local":
        remove_temp_flag = False
        header = header_string_to_header(request.POST["dataset_local"])
        header = pmap.minimize_header(header)
        dataset_name = validate_post(request, "dataset_name", FILE_RE)
    elif dataset_mode == "dataset_archive":
        remove_temp_flag = False
        dataset_name = validate_post(request, "dataset_archive", DATASET_ID_RE)
        try:
            header = database.get_dataset_header(dataset_name, pmap.observatory)
            header = pmap.minimize_header(header)
        except Exception, exc:
            raise CrdsError("Problem getting header for dataset " + 
                            srepr(dataset_name) + ": " + str(exc))
    else:
        raise ValueError("Bad dataset_mode " + srepr(dataset_mode))

    results = bestrefs_results(request, pmap, header, dataset_name)

    if remove_temp_flag:
        remove_temporary(dataset_path)

    return results

def header_string_to_header(hstring):
    header = {}
    for line in cStringIO.StringIO(str(hstring)):
        words = line.split()
        key = words[0]
        value = utils.condition_value(" ".join(words[1:]))
        header[key] = value
    return header

# @profile
@error_trap("bestrefs_explore_index.html")
@log_view
def bestrefs_results(request, pmap, header, dataset_name=""):
    """Render best reference recommendations under context `pmap` for
    critical parameters dictionary `header`.
    """
        
    recommendations = pmap.get_best_references(header)
    
    # organize and format results for HTML display    
    header_items = sorted(header.items())
    bestrefs_items = []
    archive_files = []
    for key, val in sorted(recommendations.items()):
        if val.startswith("NOT FOUND"):
            val = val[len("NOT FOUND"):]
        else:
            archive_files.append(val)
        bestrefs_items.append((key.upper, val))
        
    archive_name = os.path.splitext(dataset_name)[0] + "_bestrefs.tar.gz"
    
    return crds_render(request, "bestrefs_results.html", {
            "observatory" : pmap.observatory,
            "dataset_name" : dataset_name,
            "header_items" : header_items,
            "bestrefs_items" : bestrefs_items,
            "archive_url" : get_archive_url(archive_name, archive_files),
            "archive_name" : archive_name,
        })

# ===========================================================================

@error_trap("bestrefs_explore_index.html")
@log_view
def bestrefs_explore(request):
    """View to get the instrument context for best references."""
    if request.method == "GET":
        return crds_render(request, "bestrefs_explore_index.html", {})
    else:
        return bestrefs_explore_post(request)
    
def get_recent_pmaps(last_n=10):
    """Return a list of option tuples for rendering HTML to choose recent
    pmaps (last 10) from those filtered by `filters`. This defines what users 
    will see for the context HTML drop-down menu.
    """
    files = models.FileBlob.objects.reverse()
    pmaps = []
    for f in files:
        if f.name.endswith(".pmap"):
            f.thaw()
            pmaps.append((f.name, pmap_label(f)))
            if len(pmaps) >= last_n:
                break
    return pmaps
    
def pmap_label(blob):
    """Return the text displayed to users selecting known pmaps."""
    if isinstance(blob, str):
        blob = models.FileBlob.load(blob)
    available = "" if blob.available else "*unavailable*" 
    blacklisted = "*blacklisted*" if blob.blacklisted else ""
    return " ".join([blob.name, str(blob.delivery_date)[:16], available, blacklisted])

def bestrefs_explore_post(request):
    """View to get best reference dataset parameters."""
    context = get_recent_or_user_context(request)
    pmap = rmap.get_cached_mapping(context)
    instrument = validate_post(request, "instrument", models.INSTRUMENTS)
    valid_values = pmap.get_imap(instrument).get_valid_values_map().items()
    return crds_render(request, "bestrefs_explore_input.html", {
            "mapping" : pmap,
            "valid_values" : sorted(valid_values),
            "instrument":instrument,
        })

def is_available_pmap(context):
    is_pmap(context)
    is_available_file(context)
    return context

def get_recent_or_user_context(request):
    """Process standard request parameters for specifying context."""
    pmap_mode = validate_post(
            request, "pmap_mode", "pmap_menu|pmap_text|pmap_edit|pmap_operational")
    if pmap_mode == "pmap_edit":
        context = models.get_default_context()
    elif pmap_mode == "pmap_operational":
        context = models.get_default_context(state="operational")
    else:
        context = validate_post(request, pmap_mode, is_pmap)
    return context

@error_trap("bestrefs_explore_input.html")
@log_view
def bestrefs_explore_compute(request):
    """Validate parameter inputs from the best refs explorer drop-down
    menus and render best reference recommendations.
    """
    context = validate_post(request, "context", is_pmap)
    instrument = validate_post(request, "instrument", models.INSTRUMENTS)
    pmap = rmap.get_cached_mapping(context)
    imap = pmap.get_imap(instrument)
    header = { pmap.instrument_key : instrument.upper() }
    pars = imap.get_parkey_map().keys()
    for par in pars:
        header[par] = utils.condition_value(
            validate_post(request, par, r"[A-Za-z0-9\+\-.,*/;|{}\[\]:]*"))
    header["DATE-OBS"] = validate_post(request, "DATE-OBS", DATE_RE_STR)
    header["TIME-OBS"] = validate_post(request, "TIME-OBS", TIME_RE_STR)
    return bestrefs_results(request, pmap, header, instrument)

# ============================================================================

@error_trap("submit_input.html")
@log_view
@login_required
def submit_file(request, crds_filetype):
    """Handle file submission,  crds_filetype=reference|mapping."""
    if request.method == "GET":
        return crds_render(request, 'submit_input.html', {
            "crds_filetype" :  crds_filetype,
            "file_ingest_dirs" : get_server_ingest_dirs(),
        })
    else:
        return submit_file_post(request, crds_filetype)
    
def file_exists_somehow(filename):
    """Return True IFF `filepath` really exists or CRDS thinks it does."""
    filepath = rmap.locate_file(filename, config.observatory)
    return os.path.exists(filepath) or \
        models.FileBlob.exists(os.path.basename(filepath))

def submit_file_post(request, crds_filetype):
    """Handle the POST case of submit_file, returning dict of template vars."""
    observatory = get_observatory(request)
    if crds_filetype == "reference":
        context = get_recent_or_user_context(request)
    else:
        context = None
    description = validate_post(request, "description", DESCRIPTION_RE)
    creator = validate_post(request, "creator", PERSON_RE)
    auto_rename = "auto_rename" in request.POST    
    change_level = validate_post(request, "change_level", models.CHANGE_LEVELS)
            
    remove_dir, uploaded_files = get_files(request)
    
    # Verify that ALL references certify,  raise CrdsError on first error.
    certify_results = certify_file_list(uploaded_files.items())

    collision_list = []
    new_file_map = {}
    
    for (original_name, uploaded_path) in uploaded_files.items():
        
        new_basename = do_submit_file( observatory, original_name, uploaded_path,
            description, str(request.user), request.user.email, creator, 
            change_level, state="uploaded", auto_rename=auto_rename)
        
        collision_list += get_collision_list([new_basename])
    
        new_file_map[original_name] =  new_basename
    
#    if remove_dir is not None:
#        shutil.rmtree(remove_dir, ignore_errors=True)

    return crds_render(request, 'submit_results.html', {
                "crds_filetype": crds_filetype,
                "baseperm":new_basename,
                "collision_list" : collision_list,

                "generated_files" : [],
                "new_file_map" : sorted(new_file_map.items()),
                "submission_kind" : "submit file",
                "title" : "Submit File",
                "description" : description,
                
                "certify_results" : certify_results,
                "more_submits" : "/submit/" + crds_filetype + "/",
                })
    
def do_submit_file(observatory, original_name, upload_location, description, 
        submitter, submitter_email, creator_name="unknown",
        change_level="SEVERE", creation_method="submit file", auto_rename=True,
        state="uploaded"):
    """Do the core processing of a file submission,  including file
    certification and blacklist checking, naming, upload,  and record
    keeping.
    """
    if rmap.is_mapping(original_name):
        try:
            checksum.update_checksum(upload_location)
        except rmap.MappingError, exc:
            raise CrdsError("Error updating checksum: " + srepr(exc))
    
#    # Check the file,  leaving no server state if it fails.  Give error results.
#    do_certify_file(original_name, upload_location, check_references="exist")
#    
    # Automatically 
    if auto_rename:
        permanent_name = auto_rename_file(observatory, original_name, upload_location)
    else:
        if file_exists_somehow(original_name):
            raise FieldError("File " + srepr(original_name) + " already exists.") 
        else:
            permanent_name = os.path.basename(original_name)   

    # CRDS keeps all new files in a standard layout.   Older files can be
    # grandfathered in by special calls to add_crds_file rather than "submission".
    permanent_location = rmap.locate_file(permanent_name, observatory)

    # Make sure none of the dependencies are blacklisted,  else fail w/o state.
    blacklisted_by = get_blacklists(original_name, upload_location)
    if blacklisted_by:
        raise CrdsError("File " + srepr(original_name) + 
                        " is blacklisted by " + srepr(blacklisted_by))
    
    # Move or copy the temporary file to its permanent location.
    utils.ensure_dir_exists(permanent_location)
    os.link(upload_location, permanent_location)

    # Make a database record for this file.
    blob = models.add_crds_file(observatory, original_name, permanent_location, 
            submitter, submitter_email, description, 
            change_level=change_level, creator_name=creator_name, state=state)
    
    return os.path.basename(permanent_location)

def do_certify_file(basename, certifypath, check_references=False, filemap=None,
                    context=None):
    """Run un-trapped components of crds.certify and re-raise any exception
    as a CrdsError which will be displayed as a form error on the submission
    page.
    
    basename is the name of the file on the user's system,  hopefully with a
    sane extension.   certifypath is a fully qualified path,  but sometimes
    with a temporary filename which is total garbage.
    """
    try:
        certify.certify_files([certifypath], check_references=None,
            trap_exceptions=False, is_mapping = rmap.is_mapping(basename),
            context=context)
    except Exception, exc:
        raise CrdsError("Certifying " + srepr(basename) + ": " + str(exc))

    if check_references and rmap.is_mapping(basename):
        if filemap is None:
            filemap = models.get_fileblob_map(models.OBSERVATORY)
        ctx = rmap.load_mapping(certifypath)
        for ref in ctx.reference_names():
            assert ref in filemap, \
                "Reference " + srepr(ref) + " in " + srepr(basename) + " is not known to CRDS."

def get_blacklists(basename, certifypath, ignore_self=True, files=None):
    """Return a list of the files referenced by `basename` which are
    blacklisted.
    """
    basename = str(basename)
    if rmap.is_mapping(basename):
        blacklisted_by = set()
        try:
            mapping = rmap.load_mapping(certifypath)
        except Exception, exc:
            raise CrdsError("Error loading " + srepr(basename) + 
                            " for blacklist checking:  " + str(exc))
        if files is None:
            files = models.get_fileblob_map(mapping.observatory)
        
        for child in mapping.mapping_names() + mapping.reference_names():       
            if ignore_self and child == os.path.basename(certifypath): 
                continue
            if child not in files:   # Unknown file,  what to do?
                continue   # XXXX TODO blacklist instead?
            if files[child].blacklisted:
                blacklisted_by.add(child)
                
        return sorted(list(blacklisted_by))
    else:
        return []

# ===========================================================================

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
    blacklist_root = validate_post(request, "file_known", is_known_file)
    reject_type = validate_post(request, "reject_type", "reject|blacklist|both")
    badflag = validate_post(request, "badflag", "bad|ok")
    why = validate_post(request, "why", DESCRIPTION_RE)
    
    if reject_type in ["blacklist","both"]:
        affected_files = models.transitive_blacklist(blacklist_root, badflag, observatory)
    else:
        affected_files = [blacklist_root]

    if reject_type in ["reject", "both"]:
        models.set_reject(blacklist_root, badflag=="bad")

    instrument, filekind = utils.get_file_properties(
        observatory, blacklist_root)

    models.AuditBlob.new(
        request.user, "blacklist", blacklist_root, why, 
        "marked as " + srepr(badflag.upper()) + " reject_type=" + srepr(reject_type),
        observatory=observatory, instrument=instrument, filekind=filekind)

    return crds_render(request, "blacklist_results.html", 
                  { "affected_files": affected_files })

# ===========================================================================

@error_trap("certify_input.html")
@log_view
@login_required
# @profile
def certify_file(request):
    """View to return certify input form or process POST."""
    if request.method == "GET":
        return crds_render(request, "certify_input.html")
    else:
        return certify_post(request)

# @profile("certify5.stats")
def certify_post(request):
    """View fragment to process file certification POSTs."""

    uploaded, original_name, certified_file = handle_known_or_uploaded_file(
        request, "filemode", "file_known", "file_uploaded")

    if uploaded and rmap.is_mapping(original_name):
        checksum.update_checksum(certified_file)
            
    all_files = models.get_fileblob_map()

    certify_status, certify_output = captured_certify(
        original_name, certified_file, filemap=all_files, check_references=False)

    try:
        blacklisted_by = get_blacklists(
            original_name, certified_file, ignore_self=False, files=all_files)
    except Exception:
        blacklisted_by = []
        blacklist_status = "Error"
    else:        
        if blacklisted_by:
            blacklist_status = "Blacklisted"
        else:
            blacklist_status = "OK"

    if uploaded:
        remove_temporary(certified_file)

    return crds_render(request, "certify_results.html", 
            {"certify_status":certify_status,
             "blacklist_status":blacklist_status,
             "certify_output":certify_output,
             "blacklisted_by" : blacklisted_by,
             "certified_file":original_name})

def captured_certify(original_name, uploaded_path, check_references=True, filemap=None, context=None):
    
    mapping_switch = "--mapping" if rmap.is_mapping(original_name) else ""
    context_switch = "--context=" + context if context else ""
    
    output = pysh.out(
        "python -m crds.certify ${uploaded_path} ${mapping_switch} ${context_switch} --dump-provenance",
        independent_error=False)
    if "0 errors" in output:
        if "0 warnings" in output:
            status = "OK"
        else:
            status = "Warnings"
    else:
        status = "Failed."
    output = output.replace(uploaded_path, original_name)
    output = output.replace(os.path.basename(uploaded_path), original_name)
    
    if status != "Failed.":
        if check_references and rmap.is_mapping(original_name):
            if filemap is None:
                filemap = models.get_fileblob_map(models.OBSERVATORY)
            ctx = rmap.load_mapping(uploaded_path)
            for ref in ctx.reference_names():
                if ref not in filemap:
                    output += "ERROR: Reference " + srepr(ref) + " in " + \
                            srepr(original_name) + " is not known to CRDS.\n"
                    status = "Failed."
                    
    return status, output

def certify_file_list(upload_tuples, check_references=True, context=None):
    filemap = models.get_fileblob_map(models.OBSERVATORY)
    certify_results = {}
    for (original_name, upload_path) in upload_tuples:
        # In order to capture output easily,  run as subprocess...
        certify_results[original_name] = captured_certify(
            original_name, upload_path, check_references=check_references, filemap=filemap, context=context)
        # Run here as function to fail delivery on first exception.
        do_certify_file(original_name, upload_path, check_references=check_references, filemap=filemap, context=context)
    return certify_results

# ===========================================================================

@error_trap("batch_submit_reference_input.html")
@log_view
@login_required
# @profile("batch_submit_reference.stats")
def batch_submit_reference(request):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        return crds_render(request, "batch_submit_reference_input.html", {
                    "file_ingest_dirs" : get_server_ingest_dirs(),
                })
    else:
        return batch_submit_reference_post(request)
    
def batch_submit_reference_post(request):
    """View fragment to process file batch reference submnission POSTs."""
    context = get_recent_or_user_context(request)
    pmap = rmap.get_cached_mapping(context)
    description = validate_post(request, "description", DESCRIPTION_RE)
    creator = validate_post(request, "creator", PERSON_RE)
    auto_rename = "auto_rename" in request.POST    
    change_level = validate_post(request, "change_level", models.CHANGE_LEVELS)
    remove_dir, uploaded_files = get_files(request)
    
    # creator = validate_post(request, "creator", PERSON_RE)
    # Verify that all have same instrument and filekind
    old_instr, old_filekind = None, None
    for (original_name, uploaded_path) in uploaded_files.items():
        try:
            instrument, filekind = utils.get_file_properties(
                pmap.observatory, uploaded_path)
        except Exception:
            raise CrdsError("Can't determine instrument or file type for " + 
                            srepr(original_name))
        if old_instr is not None:
            assert instrument == old_instr, \
                "More than one instrument submitted at " + srepr(original_name)
            assert filekind == old_filekind, \
                "More than one reference type submitted at " + srepr(original_name)
        old_instr, old_filekind = instrument, filekind

    # Verify that ALL references certify,  raise CrdsError on first error.
    certify_results = certify_file_list(uploaded_files.items(), context=context)

    # Generate a temporary rmap name using "tmp" in place of observatory.
    # Refactor the original rmap inserting temporary references, creating a 
    # temporary rmap to see what actions will occur.
    old_rmap = pmap.get_imap(instrument).get_rmap(filekind).name
    old_rmap_path = rmap.locate_mapping(old_rmap, pmap.observatory)
    tmp_rmap = tempfile.NamedTemporaryFile()

    tmp_actions = refactor.rmap_insert_references(
        old_rmap_path, tmp_rmap.name, uploaded_files.values())

    no_effect = []
    for (original_name, uploaded_path) in uploaded_files.items():
        ref_file = os.path.basename(uploaded_path)
        for action in tmp_actions:
            if action.ref_file == ref_file:
                break
        else:
            no_effect.append(str(original_name))
    if no_effect:
        raise CrdsError("Some files could not be added to " + srepr(old_rmap) 
                        + ": " + srepr(no_effect))

    # Make sure there are no duplicate match tuples / useafter cases.    
    duplicate_matches = set()
    for (original_name, uploaded_path) in uploaded_files.items():
        for action in tmp_actions:
            if action.ref_file != os.path.basename(uploaded_path):
                continue
            for action2 in tmp_actions:
                if action != action2 and \
                    action.rmap_match_tuple == action2.rmap_match_tuple and \
                    action.useafter == action2.useafter:
                    duplicate_matches.add(original_name)
    if duplicate_matches:
        raise CrdsError("Files match same rmap match tuple and useafter: " +
                        ", ".join([srepr(x) for x in duplicate_matches]))

    # Once both references and refactoring checks out,  submit reference files
    # and collect mapping from uploaded names to official names.
    new_references = {}
    for (original_name, uploaded_path) in uploaded_files.items():
        new_basename = do_submit_file( 
            pmap.observatory, original_name, uploaded_path,
            description, str(request.user), request.user.email, creator, 
            change_level, creation_method="batch submit",
            state="uploaded", auto_rename=auto_rename)
        new_references[original_name] = str(new_basename)

    # Get paths for new official CRDS reference files.
    reference_paths = [
        models.FileBlob.load(name).pathname for name in new_references.values()]

    new_rmap = get_new_name(pmap.observatory, instrument, filekind, ".rmap")
    new_rmap_path = rmap.locate_mapping(new_rmap, pmap.observatory)
    
    # refactor inserting references.
    actions = refactor.rmap_insert_references(
        old_rmap_path, new_rmap_path, reference_paths)
    
    if actions:
        # Submit the new rmap with added references
        models.add_crds_file(pmap.observatory, new_rmap, new_rmap_path,  
            str(request.user), request.user.email, description, state="uploaded")
        # Generate a new context referring to the new rmap
        new_name_map = do_create_contexts(pmap.name, [new_rmap], description, 
            request.user, request.user.email, state="uploaded")
        new_mappings = [new_rmap] + new_name_map.values()
        collision_list = get_collision_list(new_mappings)
        rmap_diffs = textual_diff(old_rmap_path, new_rmap_path, old_rmap, new_rmap)
    else:  # XXX WIPE the new references since rmap generation failed!!!
        log.error("No actions performed.")
        actions = []
        new_name_map = {}
        collision_list = []
        rmap_diffs = []
        destroy_file_list(new_references.values())

#    if remove_dir is not None:
#        shutil.rmtree(remove_dir, ignore_errors=True)

    return crds_render(request, "batch_submit_reference_results.html", {
                "new_references" : sorted(new_references.values()),
                "actions" : actions,
                "pmap" : pmap.name,
                "old_rmap" : old_rmap,
                "old_mappings" : sorted(new_name_map.keys()),
                
                "new_file_map" : sorted(new_references.items()),
                "generated_files" : new_mappings, 
                "submission_kind" : "batch submit",
                "title" : "Batch Reference Submit",
                "description" : description,
                
                "collision_list" : collision_list,
                "rmap_diffs" : rmap_diffs,

                "more_submits" : "/batch_submit_reference/",
                "certify_results" : certify_results,
            })
    
@error_trap("base.html")
@login_required
@log_view
def submit_confirm(request):
    """Accept or discard proposed files from various file upload and
    generation mechanisms.
    """

    button = validate_post(request,"button","confirm|discard")
    submission_kind = validate_post(request, "submission_kind", models.AUDITED_ACTIONS)
    description = validate_post(request, "description", DESCRIPTION_RE)
    new_file_map = compat.literal_eval(request.POST["new_file_map"])
    new_files = dict(new_file_map).values()
    generated_files = compat.literal_eval(request.POST["generated_files"])
    user = str(request.user)
    more_submits = validate_post(request, "more_submits", URL_RE)
    
    instrument = filekind = "unknown"
    for filename in new_files + generated_files:
        try:
            blob = models.FileBlob.load(filename)
        except LookupError:
            raise CrdsError("Unknown CRDS file " + srepr(filename))
        assert user == blob.deliverer_user, \
            "User " + srepr(user) + " did not create " + srepr(filename)
        assert blob.state == "uploaded", \
            "File " + srepr(filename) + " is no longer in the 'uploaded' state."
        if blob.instrument != "unknown":
            instrument = blob.instrument
        if blob.filekind != "unknown":
            filekind = blob.filekind

    if button=="confirm":
        for map in generated_files:
            if map.endswith(".pmap"):
                models.set_default_context(map)
        for file in new_files + generated_files:
            models.AuditBlob.new(
                request.user, submission_kind, file, description, 
                str((new_file_map , generated_files)), 
                instrument=instrument, filekind=filekind)    
        deliver_file_list( request.user, config.observatory, 
            new_files + generated_files, description, submission_kind)
    else:
        destroy_file_list(new_files + generated_files)
        
    return crds_render(request, "confirmed.html", {
                "confirmed" : button=="confirm",
                "new_file_map" : new_file_map,
                "generated_files" : generated_files,
            })
    
def change_file_state(files, new_state):
    for filename in files:
        blob = models.FileBlob.load(filename)
        blob.state = new_state
        blob.save()

def destroy_file_list(files):
    for filename in files:
        blob = models.FileBlob.load(filename)
        blob.destroy()

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

    def extension(filename): 
        """Return the file extension of `filename`."""
        return os.path.splitext(filename)[1]
    
    if request.method == "GET":
        file1 = request.GET.get("file1", None)
        file2 = request.GET.get("file2", None)
        if file1 is None and file2 is None:
            return crds_render(request, "difference_input.html")
        else:
            file1_orig = validate_get(request, "file1", is_known_file)
            file2_orig = validate_get(request, "file2", is_known_file)
            file1_path = models.FileBlob.load(file1_orig).pathname
            file2_path = models.FileBlob.load(file2_orig).pathname
            uploaded1 = uploaded2 = None
    else:
        uploaded1, file1_orig, file1_path = handle_known_or_uploaded_file(
            request, "filemode1", "file_known1", "file_uploaded1")
        uploaded2, file2_orig, file2_path = handle_known_or_uploaded_file(
            request, "filemode2", "file_known2", "file_uploaded2")
                
        if uploaded1 and rmap.is_mapping(file1_orig):
            checksum.update_checksum(file1_path)
        if uploaded2 and rmap.is_mapping(file2_orig):
            checksum.update_checksum(file2_path)
        
    logical_diffs = map_text_diff_items = None
    if rmap.is_mapping(file1_orig) and rmap.is_mapping(file2_orig) and \
        extension(file1_orig) == extension(file2_orig):
        logical_diffs = mapping_logical_diffs(
            file1_path, file2_path, file1_orig, file2_orig)
        map_text_diffs = mapping_text_diffs(logical_diffs)
        # Compute root files separately since they may have upload paths.
        diff_lines = textual_diff(
            file1_path, file2_path, file1_orig, file2_orig)
        map_text_diffs[file1_orig, file2_orig] = diff_lines
        map_text_diff_items = sorted(map_text_diffs.items())
    elif file1_orig.endswith(".fits") and file2_orig.endswith(".fits"):
        diff_lines = pysh.lines("fitsdiff ${file1_path} ${file2_path}")
        diff_lines = format_fitsdiffs(diff_lines, file1_path, file2_path,
            file1_orig, file2_orig)
    elif re.match(GEIS_HEADER_RE, file1_orig) and \
        re.match(GEIS_HEADER_RE, file2_orig) and \
        extension(file1_orig) == extension(file2_orig):
        diff_lines = textual_diff(file1_path, file2_path, 
                                  file1_orig, file2_orig)
    else:
        raise CrdsError("Files should be either CRDS mappings "
                        "of the same type or .fits files")
        
    if uploaded1: 
        remove_temporary(file1_path)
    if uploaded2:
        remove_temporary(file2_path)
        
    if not "".join(diff_lines).strip():
        diff_lines = ["no differences"]

    return crds_render(request, "difference_results.html", 
                  {
                   "logical_diffs" : logical_diffs,
                   "map_text_diff_items" : map_text_diff_items,
                   "diff_lines" : diff_lines,
                   "file1" : file1_orig,
                   "file2" : file2_orig,
                   })

def textual_diff(file1_path, file2_path, file1_orig, file2_orig):
    """Return the output of the context diff of two files."""
    diff_lines = pysh.lines("diff -b -u -FUseAfter ${file1_path} ${file2_path}")
    result = []
    for line in diff_lines:
        line = line.rstrip()
        line = line.replace(file1_path, file1_orig)
        line = line.replace(file2_path, file2_orig)
        result.append(line)
    return result

def mapping_logical_diffs(file1, file2, file1_orig, file2_orig):
    """Return the logical differences between two mapping files."""
    try:
        map1 = rmap.load_mapping(file1)
        map2 = rmap.load_mapping(file2)
        # Get logical difference tuples
        ldiffs = map1.difference(map2)
        # Substitute the name of the original file for temp file.
#        for ldiff in ldiffs:
#            ldiff = replace_ldiff_file(ldiff, file1, file1_orig)
#            ldiff = replace_ldiff_file(ldiff, file2, file2_orig)
        return ldiffs
    except Exception, exc:
        return [("Mapping logical difference failed: " + str(exc),)]

def replace_ldiff_file(ldiff, file_temp, file_orig):
    """Replaces name of web temporary file in ldiff tuple with original upload 
    name.
    """ 
    if not len(ldiff):
        return ldiff
    tup = ldiff[0]
    if len(tup) == 2:
        if tup[0] == file_temp:
            tup = (file_orig, tup[1])
        if tup[1] == file_temp:
            tup = (tup[0], file_orig)
    return (tup,) + replace_ldiff_file(ldiff[1:], file_temp, file_orig)

def mapping_text_diffs(logical_diffs):
    """Return a mapping of file pairs to the textual differences between them
    for all of the mappings mentioned in `logical_diffs`.   Skips over the first
    logical difference tuple since that corresponds to the top level files,  
    which might have been uploaded and hence the file paths aren't known here.
    """
    diff_map = {}
    for ldiff in logical_diffs:
        for tup in ldiff[1:]:
            if len(tup) == 2 and tup[0].endswith("map") and tup[1].endswith("map"):
                file1_orig, file2_orig = tup
                file1_path = rmap.locate_mapping(file1_orig)
                file2_path = rmap.locate_mapping(file2_orig)
                if (file1_orig, file2_orig) not in diff_map:
                    try:
                        diffs = textual_diff(
                            file1_path, file2_path, file1_orig, file2_orig)
                    except Exception, exc:
                        diffs = "diffs failed: " + str(exc)
                    diff_map[file1_orig, file2_orig] = diffs
                else:
                    break
    return diff_map

def format_fitsdiffs(lines, file1, file2, file1_orig, file2_orig):
    """Add some colorization to output `lines` from fitsdiff, replacing
    `file1` and `file2` with their basenames.
    """
    for i in range(len(lines)):
        line = clean_path(lines[i], file1, file1_orig)
        line = clean_path(line, file2, file2_orig)
        if "Primary HDU" in line or re.search("Extension \d+ HDU", line):
            line = "<h3>" + line + "</h3>"
        line = re.sub(r"([Kk]eyword)\s*([A-Za-z0-9_]*)",
                      r"\1 <span class='green'>\2</span>", line)
        lines[i] = line
    return lines

def clean_path(line, path, file_orig):
    """Replace occurrences of `path` in `line` with a greyed version of
    the `path`s basename.
    """
    base = "<span class='grey'>" + os.path.basename(file_orig) + "</span>"
    return line.replace(path, base)

# ===========================================================================

@error_trap("browse_known_file_error.html")
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
    else:
        match_paths = []
    
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
    lines = ["<pre class='program'>"] + lines + ["</pre>"]
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
    
    try:
        header = mapping.get_minimum_header(browsed_file)
    except IOError:
        return "<p class='error'>File unavailable.</p>"
    
    output  = "<b>Header Parameters</b>\n"
    output += "<br/>\n"
    output += "<br/>\n"
    output += "<table border='1'>\n"
    for key, value in sorted(header.items()):
        if value != "UNDEFINED":
            output += "<tr><td class='label'>%s</td><td>%s</td></tr>\n" % (key, value)
    output += "</table>\n"
    output += "<br/>\n"
    
    if browsed_file.endswith(".fits"):
        output += "<b>FITS Info</b>\n"
        output += "<pre>\n"
        fits_info = finfo(browsed_file)[1] + "\n"
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
    known_files = models.known_files()
    name = _get_new_name(observatory, instrument, filekind, extension)
    while name in known_files:
        name = _get_new_name(observatory, instrument, filekind, extension)
    return name

def auto_rename_file(observatory, upload_name, upload_path):
    """Generate a CRDS name for an uploaded file."""
    extension = os.path.splitext(upload_name)[-1]
    instrument, filekind = utils.get_file_properties(
        observatory, upload_path)
    return get_new_name(observatory, instrument, filekind, extension)

# ===========================================================================

@error_trap("recent_activity_input.html")
@log_view
# @login_required
def recent_activity(request):
    """recent_activity displays records from the AuditBlob database."""
    if request.method == "GET":
        return crds_render(request, "recent_activity_input.html", {})
    else:
        return recent_activity_post(request)

def recent_activity_post(request):
    """View fragment handling recent_activity POST case."""
    action = validate_post(
        request, "action", models.AUDITED_ACTIONS+[r"\*"])
    observatory = validate_post(
        request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate_post(
        request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate_post(
        request, "filekind", models.FILEKINDS+[r"\*"])
    extension = validate_post(
        request, "extension", models.EXTENSIONS+[r"\*"])
    filename = validate_post(
        request, "filename", r"[A-Za-z0-9_.\*]+")
    deliverer_user = validate_post(
        request, "deliverer_user", r"[A-Za-z0-9_.\*]+")
    filters = {}
    for var in ["action", "instrument", "filekind", "extension",
                "filename", "deliverer_user"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_activities = models.AuditBlob.filter(**filters)[::-1]
    return crds_render(request, "recent_activity_results.html", {
                "filters": filters,
                "filtered_activities" : filtered_activities,
            })

# ===========================================================================

@error_trap("browse_db_input.html")
@log_view
# @login_required
def browse_db(request):
    """browse_db displays records from the FileBlob (subclasses) database."""
    if request.method == "GET":
        return crds_render(request, "browse_db_input.html", {})
    else:
        return browse_db_post(request)

def browse_db_post(request):
    """View fragment handling browse_db POST case."""
    observatory = validate_post(
        request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate_post(
        request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate_post(
        request, "filekind", models.FILEKINDS+[r"\*"])
    extension = validate_post(
        request, "extension", models.EXTENSIONS+[r"\*"])
    filename = validate_post(
        request, "filename", FILE_RE + r"|\*")
    deliverer_user = validate_post(
        request, "deliverer_user", [r"\*"] + usernames())
    status = validate_post(
        request, "status",  r"[A-Za-z0-9_.\*]+")
    filters = {}
    for var in ["instrument", "filekind", "extension",
                "filename", "deliverer_user", "status"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_db = models.FileBlob.filter(**filters)
    return crds_render(request, "browse_db_results.html", {
                "filters": filters,
                "filtered_db" : filtered_db,
                "observatory" : observatory,
            })

# ===========================================================================

@error_trap("create_contexts_input.html")
@log_view
@login_required
def create_contexts(request):
    """create_contexts generates a new pmap and imaps given an existing pmap
    and set of new rmaps.   Note that the "new" rmaps must already be in CRDS.
    """
    if request.method == "GET":
        return crds_render(request, "create_contexts_input.html", {})
    else:
        return create_contexts_post(request)

def create_contexts_post(request):
    """View fragment handling create_contexts POST case."""
    pmap_name = get_recent_or_user_context(request)
    updated_rmaps = validate_post(request, "rmaps", is_list_of_rmaps)
    description = validate_post(request, "description", DESCRIPTION_RE)

    new_name_map = do_create_contexts(pmap_name, updated_rmaps, description,
        request.user, request.user.email, state="uploaded")

    old_mappings = sorted(new_name_map.keys())
    new_mappings = sorted(new_name_map.values())
    
    collision_list = get_collision_list(new_mappings)
    
    return crds_render(request, "create_contexts_results.html", {
                "pmap": pmap_name,
                "old_mappings" : old_mappings,
                "added_rmaps" : updated_rmaps,
                
                "new_file_map" : [],
                "generated_files" : new_mappings, 
                "submission_kind" : "new context",
                "title" : "Create Contexts",
                "description" : description,
                "more_submits" : "/create_contexts/",
                "collision_list" : collision_list,
 
            })
    
def do_create_contexts(pmap_name, updated_rmaps, description, user, email,
                       state="uploaded"):
    """Create new contexts based on `pmap_name` which refer to `updated_rmaps`
    instead of the corresponding old rmaps.  Add the new contexts to the
    CRDS database and return a list of new context mapping names.
    """
    # Get the mapping from old imap to new rmap, basically the imaps that
    # must be updated onto the list of rmap updates to do.
    updates_by_instrument = newcontext.get_update_map(pmap_name, updated_rmaps)
    
    # For each imap being edited,  and the pipeline context,  reserve new
    # official names and return the dictionary { old_mapping : new_mapping }.
    new_name_map = generate_new_names(pmap_name, updates_by_instrument)
    
    # Actually generate the new mappings,  by first copying the old mappings 
    # and then substituting old names with their updated equivalents.
    new_contexts = newcontext.generate_new_contexts(
        pmap_name, updates_by_instrument, new_name_map)
 
#    print "WARNING: skipping context certification for", repr(new_contexts)
    for ctx in new_contexts:
        new_loc = rmap.locate_mapping(ctx)  
        do_certify_file(new_loc, new_loc)

    # Create delivery records for each of the new files
    observatory = rmap.get_cached_mapping(pmap_name).observatory
    for old_ctx, new_ctx in new_name_map.items():
        models.add_crds_file(
            observatory, old_ctx, rmap.locate_mapping(new_ctx),  user, email, 
            description, 
            srepr(pmap_name) + " : " + ",".join([srepr(x) for x in updated_rmaps]),
            state=state)
    
    return new_name_map

def generate_new_names(old_pipeline, updates):
    """Generate a map from old pipeline and instrument context names to the
    names for their replacements.
    """
    new_names = {}
    new_names[old_pipeline] = new_name(old_pipeline)
    for old_imap in updates:
        new_names[old_imap] = new_name(old_imap)
    return new_names

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

# ===========================================================================

@error_trap("edit_rmap_input.html")
@log_view
@login_required
def edit_rmap_browse(request):
    """browse_db displays records from the FileBlob (subclasses) database."""
    if request.method == "GET":    # display rmap filters
        return crds_render(request, "edit_rmap_input.html", {})
    else:   # display filtered rmaps
        return edit_rmap_browse_post(request)

def edit_rmap_browse_post(request):
    """View fragment for listing filtered rmap choices."""
    observatory = validate_post(
        request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate_post(
        request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate_post(
        request, "filekind", models.FILEKINDS+[r"\*"])
    extension = validate_post(
        request, "extension", models.EXTENSIONS+[r"\*"])
    filename = validate_post(
        request, "filename", FILE_RE + r"|\*")
    deliverer_user = validate_post(
        request, "deliverer_user", [r"\*"] + usernames())
    status = validate_post(
        request, "status",  r"[A-Za-z0-9_.\*]+")
    filters = {}
    for var in ["instrument", "filekind", "extension",
                "filename", "deliverer_user", "status"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_db = models.FileBlob.filter(**filters)
    return crds_render(request, "edit_rmap_browse_results.html", {
                "filters": filters,
                "filtered_db" : filtered_db,
                "observatory" : observatory,
            })

@csrf_exempt
@error_trap("base.html")
@log_view
@login_required
def edit_rmap(request, filename=None):
    """Handle all aspects of editing a particular rmap named `filename`."""
    if request.method == "GET":
        return edit_rmap_get(request, filename)  # display editor form
    else:
        return edit_rmap_post(request)   # execute edit actions

# @profile
def edit_rmap_get(request, filename):
    """Return the page used to edit the rmap `filename`."""
    blob = models.FileBlob.load(filename)
    file_contents = browsify_edit_rmap(filename, blob.pathname)
    return crds_render(request, "edit_rmap_editor.html", 
            {"fileblob" : blob,
             "observatory" : blob.observatory,
             "file_contents" : file_contents,
             "browsed_file": filename})

def browsify_edit_rmap(basename, fullpath):
    """Format a CRDS mapping file as colorized HTML for editing."""
    contents = ""
    try:
        linegen = open(fullpath).readlines()
    except OSError:
        return ["<h3 class='error'>File " 
                "<span class='grey'>%s<span> not found</h3>" % (basename,)]
    for line in linegen:
        if line.strip():
            line = browsify_mapping_line(line)
            line = re.sub(r"'(" + FILE_RE + ")',",
                  r"""<span class='filename'>'\1'</span>,""",  #   <a href='/browse/\1'>*</a>
                  line)
            contents += line
    return contents


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

def edit_rmap_post(request):
    """View fragment handling Rmap edit execution POST."""

    expanded, actions = collect_action_tree(request)
    print pprint.pformat(actions)
    if not actions:
        raise CrdsError("No edit actions were found.  Aborted.")
    
    description = validate_post(request, "description", DESCRIPTION_RE)
    original_rmap = validate_post(request, "browsed_file", is_rmap)
    creator     = validate_post(request,  "creator", PERSON_RE)
    observatory = rmap.get_cached_mapping(original_rmap).observatory
    auto_rename = "auto_rename" in request.POST
    
    pmap_name = get_recent_or_user_context(request)

    new_references, certify_results = handle_file_submissions(
        pmap_name, original_rmap, expanded, observatory, request.user, 
        auto_rename=auto_rename, description=description, creator=creator)
    
    new_rmap, new_loc = execute_edit_actions(original_rmap, expanded)
    
    models.add_crds_file(observatory, original_rmap, new_loc, 
            request.user, request.user.email, description, 
            creator_name = creator, state="uploaded")

    new_context_map = do_create_contexts(
        pmap_name, [new_rmap], description,  request.user, request.user.email,
        state="uploaded")
    
    old_mappings = sorted(new_context_map.keys() + [original_rmap])
    new_mappings = sorted(new_context_map.values() + [new_rmap])
    
    collision_list = get_collision_list(new_mappings)
    
    rmap_blob = rmap.load_mapping(original_rmap)
    
    return crds_render(request, "edit_rmap_results.html", {
                "pmap" : pmap_name,
                "new_references" : new_references,
                "old_mappings" : old_mappings,
                "collision_list" : collision_list,
                "actions" : actions,
                
                "generated_files" : new_mappings,
                "new_file_map" : sorted(new_references),
                "submission_kind" : "edit rmap",
                "title" : "Edit Rmap",
                "description" : description,
                
                "more_submits" : "/edit_rmap_browse/",
                "certify_results": certify_results,
            })

def collect_action_tree(request):
    """Loop over post variables gathering add and delete useafter
    action tuples,  validating basic syntax and file existence.   Return both a 
    dotted tree of actions and a list of action tuples.
    """
    action_vars = {}
    for var in request.POST:
        if var.startswith(("add.","delete.")):
            action_vars[str(var)] = str(request.POST[var])
    for var in request.FILES:
        if var.startswith("add."):
            action_vars[str(var)] = uploaded = get_uploaded_file(request, var)
            print "uploaded ", var, uploaded.name
    
    expanded = DotExpandedDict(action_vars)
    actions = []
    for action in expanded:
        for serial in expanded[action]:
            assert re.match("\d+", serial), "invalid action serial no " + srepr(serial)
            pars = expanded[action][serial]
            assert "match_tuple" in pars, "incomplete action parameter set: missing match_tuple"
            match_tuple = pars["match_tuple"] = is_match_tuple(pars["match_tuple"])
            assert "date" in pars, "incomplete action parameter set: missing date"
            date = pars["date"] = is_datetime(pars["date"])
            assert "filename" in pars, "incomplete action parameter set: missing filename"
            uploaded = pars["filename"]
            if action != "add":
                filename = is_reference(uploaded)
            else:
                filename = uploaded.name
            actions.append((action, match_tuple, date, str(filename)))
            
    return expanded, actions

def handle_file_submissions(pmap_name, original_rmap, expanded, observatory, submitter, 
                            auto_rename, description, creator):
    """Certify and submit all of the added files in `expanded`.   Return
    a list of tuples of reference filenames: [(uploaded_name,  crds_name), ...]
    """
    rmap_instrument, rmap_filekind = utils.get_file_properties(observatory, original_rmap)
    for addno in expanded["add"]:
        uploaded_file = expanded["add"][addno]["filename"]
        uploaded_name = str(uploaded_file.name)
        uploaded_path = uploaded_file.temporary_file_path()
        uploaded_instr, uploaded_filekind = utils.get_file_properties(
            observatory, uploaded_path)
        assert uploaded_instr == rmap_instrument, \
            "Uploaded reference " + srepr(uploaded_name) + \
            " has wrong instrument (" + uploaded_instr + ") for " + \
            srepr(original_rmap) + " (" + rmap_instrument + ")"
        assert uploaded_filekind == rmap_filekind, \
            "Uploaded reference " + srepr(uploaded_name) + \
            " has wrong filekind (" + uploaded_filekind + ") for " + \
            srepr(original_rmap) + " (" + rmap_filekind + ")"
        try:
            do_certify_file(uploaded_file.name, uploaded_path, context=pmap_name)
        except Exception, exc:
            raise CrdsError("Reference " + srepr(uploaded_file.name) + 
                            " failed certification: " + str(exc))
    uploaded_files = { }
    for addno in expanded["add"]:
        uploaded_file = expanded["add"][addno]["filename"]
        uploaded_files[uploaded_file.name] = uploaded_file.temporary_file_path()

    certify_results = certify_file_list(uploaded_files.items(), context=pmap_name)

    new_references = []
    for addno in expanded["add"]:
        uploaded_file = expanded["add"][addno]["filename"]
        # description = expanded["add"][addno].get("description","undefined")
        # creator_name = expanded["add"][addno].get("creator_name","undefined")
        change_level = expanded["add"][addno].get("change_level","SEVERE")
        new_basename = do_submit_file(
            observatory, uploaded_file.name, uploaded_file.temporary_file_path(),
            description, str(submitter), submitter.email, creator_name=creator,
            change_level=change_level, creation_method="edit rmap", state="uploaded",
            auto_rename=auto_rename)
        new_references.append((uploaded_file.name, new_basename))
        expanded["add"][addno]["filename"] = new_basename

    return sorted(new_references), certify_results
 
def execute_edit_actions(original_rmap, expanded):
    """Perform each of the `expanded` on `original_rmap` to create a new
    rmap.   Return the (new_name, new_path) for the new rmap.   Don't alter
    `original_rmap`.
    """
    new_rmap = new_name(original_rmap)
    old_loc = rmap.locate_mapping(original_rmap)
    new_loc = rmap.locate_mapping(new_rmap)
    open(new_loc, "w").write(open(old_loc).read())   # copy old to new

    for act in sorted(expanded):   # do adds before deletes
        for edit_no in expanded[act]:
            pars = expanded[act][edit_no]
            if act == "add":
                refactor.rmap_add_useafter( new_loc, new_loc, 
                    pars["match_tuple"], pars["date"], pars["filename"])
            elif act == "delete":
                refactor.rmap_delete_useafter(new_loc, new_loc, 
                    pars["match_tuple"], pars["date"], pars["filename"])
            else:
                raise RuntimeError("Unknown edit action " + repr(act))

    checksum.update_checksum(new_loc)
    
    do_certify_file(new_loc, new_loc)  # mappings only, no context.

    return new_rmap, new_loc
    
# ============================================================================
'''
@error_trap("delivery_options_input.html")
@log_view
@login_required
def deliver_context(request):
    """Based on a pmap, find the list of referenced files which have not yet
    been delivered and present them as candiates for delivery.
    """
    if request.method == "GET":
        raise ServerError("Can't GET from /deliver_context/")
    context = get_recent_or_user_context(request)
    pmap = rmap.load_mapping(context)
    candidates = pmap.mapping_names() + pmap.reference_names()
    allfiles = models.FileBlob.dictionary()
    delivered_files = []
    for cand in candidates:
        if cand in allfiles and allfiles[cand].state == "submitted":
            delivered_files.append(allfiles[cand])
    return crds_render(request, "delivery_options_results.html", {
                "observatory": pmap.observatory,
                "context" : context,
                "prechecked" : "CHECKED",
                "filtered_db" : delivered_files,
            })

@error_trap("delivery_options_input.html")
@log_view
@login_required
def delivery_options(request):
    """Present filtering criteria (GET) and a list of filtered files from
    which to compose a delivery (POST).
    """
    if request.method == "GET":
        return crds_render(request, "delivery_options_input.html", {
            "pmaps": get_recent_pmaps(status="submitted"),
        })
    else:
        return delivery_options_post(request)

def delivery_options_post(request):
    """Execute filtering criteria to present candidates for delivery."""
    observatory = validate_post(
        request, "observatory", models.OBSERVATORIES+[r"\*"])
    instrument = validate_post(
        request, "instrument", models.INSTRUMENTS+[r"\*"])
    filekind = validate_post(
        request, "filekind", models.FILEKINDS+[r"\*"])
    filename = validate_post(
        request, "filename", r"[A-Za-z0-9_.\*]+")
    deliverer_user = validate_post(
        request, "deliverer_user", r"[A-Za-z0-9_.\*]+")
    status = "submitted"
    
    filters = {}
    for var in ["observatory", "instrument", "filekind", 
                "filename", "deliverer_user", "status"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_db = models.FileBlob.filter(**filters)[::-1]

    return crds_render(request, "delivery_options_results.html", {
                "filters": filters,
                "filtered_db" : filtered_db,
            })
'''


def deliver_file_list(user, observatory, delivered_files, description, action):
    """Perform delivery actions for `delivered_files` by setting up the
    catalog file and making links, updating database and audit trail.
    """
    if not len(delivered_files):
        raise CrdsError("No files were selected for delivery.")
    user = str(user)
    delivered_files = sorted(delivered_files)
    catalog = deliver_file_catalog(observatory, delivered_files, "I")
    paths = deliver_file_get_paths(observatory, delivered_files)
    try:
        catalog_link = deliver_make_links(observatory, catalog, paths)
    except Exception, exc:
        deliver_remove_fail(observatory, catalog, paths)
        raise CrdsError("Delivery failed: " + str(exc))
    deliver_file_set_catalog_links(observatory, delivered_files, catalog_link)
    models.AuditBlob.new(
        user, action, os.path.basename(catalog), description, 
        repr([os.path.basename(catalog)] + delivered_files), observatory)        

def deliver_file_get_paths(observatory, files):
    """Adjust the database to account for this delivery.   Returns a list of
    absolute paths to `files`.
    """
    paths = []
    for filename in files:
        blob = models.FileBlob.load(filename)
        paths.append(blob.pathname)
    return paths

def deliver_file_set_catalog_links(observatory, files, catalog_link):
    """Set the `catalog_link` in each FileBlob in `files` and mark each
    blob as state="delivered".   This just means that OPUS now has the
    opportunity to pick up the file.   As long as `catalog_link` exists, it is
    considered to remain in "delivered" state.  When the catalog_link no longer
    exists,  it is assumed OPUS has copied the file, deleted the delivery link,
    and the file transitions from "delivered" to "operational".   Here,
    "operational" means that OPUS and the archives have the context or file 
    available,  not necessarily that the pipeline is currently using the context.
    """
    for filename in files:
        blob = models.FileBlob.load(filename)
        blob.catalog_link = catalog_link
        blob.state = "delivered"
        blob.save()

def deliver_file_catalog(observatory, files, operation="I"):
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
    
    CRDS uses the catalog file name to name the delivery for auditing.
    """
    assert operation in ["I","D"], \
        "Invalid delivery operation " + srepr(operation)
    delivery_id = models.CounterBlob.next(observatory, "delivery_id")
    catalog = "_".join(["opus", str(delivery_id), operation.lower()])+".cat"
    catpath = os.path.join(config.CRDS_CATALOG_DIR, catalog)
    utils.ensure_dir_exists(catpath)
    cat = open(catpath, "w")
    for filename in files:
        if rmap.is_mapping(filename):
            kind = "M"
        else:
            kind = "R"
        cat.write(filename + " " + operation + " " + kind + "\n")
    cat.close()
    return catpath

def deliver_make_links(observatory, catalog, paths):
    """Copy file `paths` of `observatory` to the proper holding area
    for observatory and then make hard links to each file in each
    of the delivery site directories.   Return the path of the of
    the master catalog link;  when the master link is deleted by
    the recipient the entire delivery is considered complete and
    the files transition from "delivered" to "operational".
    """
    dirs = config.CRDS_DELIVERY_DIRS
    for site in dirs:
        utils.ensure_dir_exists(site)
        for filename in paths + [catalog]:
            dest = site +"/" + os.path.basename(filename)
            try:
                os.link(filename, dest)
            except Exception, exc:
                raise CrdsError("failed to link " + srepr(filename) + " to " +
                                srepr(dest) + " : " + str(exc))
    master_catalog_link = os.path.join(dirs[0], os.path.basename(catalog))
    return master_catalog_link

def deliver_remove_fail(observatory, catalog, paths):
    """Delete all the delivery links for a failed but possibly partially
    completed delivery.
    """
    for site in config.CRDS_DELIVERY_DIRS + [os.path.dirname(catalog)]:
        utils.ensure_dir_exists(site)
        for filename in paths + [catalog]:
            dest = site +"/" + os.path.basename(filename)
            try:
                os.remove(dest)
            except Exception:
                pass

# ============================================================================

from django.views.decorators.http import condition

# @condition(etag_func=None)
@error_trap("base.html")
@log_view
def get_file_data(request, filename):
    """Provides a view to serve CRDS mapping and reference files via URL."""
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
            log.write("Yielding", srepr(filename), "chunk #" + str(chunk), "of", 
                      len(data), "bytes.")
            # yield data
            chunk += 1
            total += len(data)
            yield data
    log.write("Finished", srepr(filename), "total bytes", repr(total))

ARCH_MODES = {
    "tar" : "w|",
    "tar.gz" : "w|gz",
    "tar.bz2" : "w|bz2",
}

# @profile
@error_trap("base.html")
@log_view
def get_archive(request, filename):
    """Supports a link for getting an archive of files of the form:
    
    http://get_archive/<filename.tar.gz>?file1=hst.pmap&file2=hst_acs.imap?...
    """
    arch_extension = None
    for arch_extension in ARCH_MODES:
        if filename.endswith(arch_extension):
            break
    assert arch_extension in ARCH_MODES, \
        "Unsupported archive extension " + repr(filename)
    
    files = []
    for var in request.GET:
        if var.startswith("file"):
            filename = validate_get(request, var, is_available_file)
            files.append(filename)
            
    filepaths = []
    for filename in files:
        filepaths.append(models.FileBlob.load(filename).pathname)
        
    response = HttpResponse(mimetype="application/octet-stream")
    
    buffer = cStringIO.StringIO()
    tar = tarfile.open(mode=ARCH_MODES[arch_extension], fileobj=buffer)
    for path in filepaths:
        tar.add(path, arcname=os.path.basename(path))
    tar.close()
    response.write(buffer.getvalue())
    
    return response

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
    
@error_trap("base.html")
@superuser_login_required
def version_info(request):
    """Output a page with a table of software component versions."""
    return crds_render(request, "version_info.html", {
                "version_info" : sorted(versions.get_all_versions().items())
            })

@error_trap("base.html")
@log_view
@superuser_login_required
def set_default_context(request):
    """Change the default context presented to users as the nominal start from
    which to derive new contexts.
    """
    if request.method == "GET":    # display rmap filters
        return crds_render(request, "set_default_context_input.html", {
                "context_map" : models.ContextBlob.get_map(),
            })
    else:   # display filtered rmaps
        new_default = get_recent_or_user_context(request)
        description = validate_post(request, "description", DESCRIPTION_RE)
        context_type = validate_post(request, "context_type", models.CONTEXT_TYPES)
        old_default = models.get_default_context(models.OBSERVATORY, state=context_type)
        if old_default == new_default:
            raise CrdsError(srepr(old_default) + " is already in use for the " + 
                            srepr(context_type) + " context.")
        models.set_default_context(new_default, user=request.user, state=context_type)
        models.AuditBlob.new(request.user, "set default context", 
                             new_default, description, 
                             context_type + " context changed from " +  
                             srepr(old_default) + " to " + srepr(new_default))
        return crds_render(request, "set_default_context_results.html", {
                    "new_default" :  new_default,
                    "old_default" :  old_default,
                    "context_type" : context_type,
                })
    
