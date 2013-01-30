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
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
import django.utils.safestring as safestring
from django.utils import simplejson
from django.core.urlresolvers import reverse

import django.contrib.auth
import django.contrib.auth.models
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.datastructures import DotExpandedDict

import pyfits

from crds import (rmap, utils, certify, timestamp, uses, matches, newcontext, 
                  refactor, checksum, pysh, compat, log, config)

from crds.timestamp import (is_datetime, DATE_RE_STR, TIME_RE_STR, DATETIME_RE_STR)
from crds import CrdsError

import crds.server.config as sconfig
from crds.server.interactive import (models, database)
from crds.server.interactive.models import FieldError, MissingInputError
from crds.server import settings

import crds.server.jsonapi.views as jsonapi_views

from . import versions

HERE = os.path.dirname(__file__) or "./"

# ===========================================================================

log.add_stream_handler(sys.stderr)
log.remove_console_handler()

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

FILE_RE = r"[A-Za-z0-9_]+(\.fits|\.pmap|\.imap|\.rmap|\.r\d[hd])"
DESCRIPTION_RE = r"[A-Za-z0-9._ ]+"
GEIS_HEADER_RE = r"\w+(\.r\dh)"
PERSON_RE = r"[A-Za-z_0-9\.@]*"
DATASET_ID_RE = r"[A-Za-z0-9_]+"
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
#    assert blob.state != "uploaded", \
#        "File " + srepr(filename) + " has not yet been submitted."
    return filename

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
    assert not blob.blacklisted, \
        "File " + srepr(filename) + " has been blacklisted and should no longer be used."
    return blob

def is_available_file(filename):
    """Verify that `filename` identifies a file already known to CRDS and
    meets any requirements for distribution.   Return the filename.
    """
    blob = is_available_file_blob(filename)
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

def crds_render(request, template, dict_=None, requires_pmaps=False):
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
    
    # echo escaped inputs.
    for key, value in request.GET.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.POST.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.FILES.items():
        rdict[key] = safestring.mark_for_escaping(value)

    rdict["old_pmap_edit"] = rdict.get("pmap_edit", "none")  # from request.
    rdict["old_pmap_operational"] = rdict.get("pmap_operational", "none")
    
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
            
    # log.info("rendering:", srepr(template), log.PP(rdict))
            
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
    returning:   remove_dir,   { original_name : file_path }
    """
    dir = os.path.join(sconfig.CRDS_INGEST_DIR, str(request.user))
    uploads = { str(os.path.basename(f)) : str(f) for f in glob.glob(dir + "/*") }
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

def remove_temporary(filepath):
    """Attempt to remove `filepath`.  Ignore errors."""
    try:
        assert not filepath.startswith("/grp/hst/cdbs"), \
            "ERROR -- attempt to delete from Central Store"
        os.remove(filepath)
    except Exception, exc:
        log.warning("Failed to remove temporary", repr(filepath), ":", str(exc))

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
        log.info("REQUEST:", request.path, request.method)
#        log.info("META:", repr(request.META), stdout=None)
        if request.GET:
            log.info("GET:",   repr(request.GET))
        if request.POST:
            log.info("POST:",  repr(request.POST))
#        if request.COOKIES:
#            log.info("COOKIES:", repr(request.COOKIES), stdout=None)
        if request.FILES:
            log.info("FILES:", repr(request.FILES))
        log.info("OUTPUT:")
        try:    
            response = func(request, *args, **keys)
#            log.info("RESPONSE:\n" + response.content, stdout=None)
            return response
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
                profile_core.result = func(*args, **keys)
            cProfile.runctx("runit()", locals(), locals(), filename=filename)
            return profile_core.result
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
        handler = log.add_stream_handler(out)
        try:
            result = func(*args, **keys)
        finally:
            out.flush()
            log.remove_stream_handler(handler)
            sys.stdout, sys.stderr = oldout, olderr
        out.seek(0)
        return result, out.read()
    return captured

# ===========================================================================
# ===========================================================================
# ===========================================================================

def index(request):
    """Return the top level page for all of interactive CRDS."""
    return crds_render(request, "index.html")

# ===========================================================================

@error_trap("base.html")
@login_required
def display_result(request, id):
    id = int(id)
    result = models.RepeatableResultBlob.get(id)
    pars = result.parameters
    pars["results_id"] = id  # needed to implement "disposition", confirmed or cancelled.
    return crds_render(request, result.page_template, pars)

def render_repeatable_result(result, template, rdict):    
    result = models.RepeatableResultBlob.new(template, rdict)    
    return HttpResponseRedirect("/display_result/" + str(result.id))

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

@log_view
@error_trap("base.html")
@login_required
def upload_new(request, template="upload_new_input.html"):
    if request.method == "GET":
        return crds_render(request, template)
    else:
        f = get_uploaded_file(request, 'file')
        file_local_dir = str(request.user)
        assert re.match("[A-Za-z0-9_]+", file_local_dir), \
            "Invalid file_local_dir " + srepr(file_local_dir)
        ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, file_local_dir, f.name)
        with log.warn_on_exception("Failed removing", repr(ingest_path)):
            os.chmod(ingest_path, 0666)
            os.remove(ingest_path)
            log.info("Removed existing", repr(ingest_path))
        utils.ensure_dir_exists(ingest_path)
        log.info("Linking", ingest_path)
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
@log_view
@error_trap("base.html")
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
    try:
        file_local_dir = str(request.user)
        assert re.match("[A-Za-z0-9_]+", file_local_dir), \
            "Invalid file_local_dir " + srepr(file_local_dir)
        ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, file_local_dir)
        ingest_filepath = os.path.join(ingest_path, filename)
        log.info("upload_delete removing file", srepr(ingest_filepath))
        os.remove(ingest_filepath)
    except Exception, exc:
        log.error("upload_delete failed:", str(exc))
   
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
    files = models.FileBlob.objects.all()
    pmaps = []
    for f in files:
        if f.name.endswith(".pmap"):
            f.thaw()
            if f.state == "uploaded":
                continue
            pmaps.append((f.name, pmap_label(f)))
    return list(reversed(pmaps))[:last_n]
    
def pmap_label(blob):
    """Return the text displayed to users selecting known pmaps."""
    if isinstance(blob, basestring):
        blob = models.FileBlob.load(blob)
    available = "" if blob.available else "*unavailable*" 
    blacklisted = "*blacklisted*" if blob.blacklisted else ""
    rejected = "*rejected*" if blob.rejected else ""
    return " ".join([blob.name, str(blob.delivery_date)[:16], available, blacklisted, rejected])

def bestrefs_explore_post(request):
    """View to get best reference dataset parameters."""
    context = get_recent_or_user_context(request)
    pmap = rmap.get_cached_mapping(context)
    instrument = validate_post(request, "instrument", models.INSTRUMENTS)
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
    return str(context)

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
def submit_files(request, crds_filetype):
    """Handle file submission,  crds_filetype=reference|mapping."""
    if request.method == "GET":
        return crds_render(request, "submit_input.html", {
                    "crds_filetype" :  crds_filetype,
                }, requires_pmaps=True)
    else:
        return submit_files_post(request, crds_filetype)
    
def file_exists_somehow(filename):
    """Return True IFF `filepath` really exists or CRDS thinks it does."""
    filepath = rmap.locate_file(filename, sconfig.observatory)
    return os.path.exists(filepath) or \
        models.FileBlob.exists(os.path.basename(filepath))

def submit_files_post(request, crds_filetype):
    """Handle the POST case of submit_files, returning dict of template vars."""
    # crds_filetype constrained by RE in URL to 'mapping' or 'reference'.
    observatory = get_observatory(request)
    compare_old_reference = "compare_old_reference" in request.POST 
    context = get_recent_or_user_context(request)
    description = validate_post(request, "description", DESCRIPTION_RE)
    creator = validate_post(request, "creator", PERSON_RE)
    auto_rename = "auto_rename" in request.POST    
    change_level = validate_post(request, "change_level", models.CHANGE_LEVELS)            
    remove_dir, uploaded_files = get_files(request)
    
    disposition, certify_results, new_file_map, collision_list = submit_files_core(
        observatory, crds_filetype, uploaded_files, context, compare_old_reference, 
        description, str(request.user), request.user.email, creator, change_level, auto_rename)

    return render_repeatable_result(request, 'submit_results.html', {
                "crds_filetype": crds_filetype,
                "collision_list" : collision_list,

                "generated_files" : [],
                "new_file_map" : sorted(new_file_map.items()),
                "submission_kind" : "submit file",
                "title" : "Submit File",
                "description" : description,
                
                "certify_results" : certify_results,
                "more_submits" : "/submit/" + crds_filetype + "/",
                
                "disposition" : disposition,
                })

def submit_files_core(observatory, crds_filetype, uploaded_files, context, compare_old_reference, 
        description, submitter, submitter_email, creator, change_level, auto_rename):
    """Submit simple files to CRDS, literally,  without making automatic rules adjustments."""
    
    restrict_genre(crds_filetype, uploaded_files)

    # Verify that ALL files certify.
    disposition, certify_results = certify_file_list(
        uploaded_files.items(), context=context, compare_old_reference=compare_old_reference)
    
    # Add the files to the CRDS database as "uploaded",  pending confirmation.
    new_file_map = submit_file_list(observatory, uploaded_files, description, 
        submitter, submitter_email, creator_name=creator, change_level=change_level, 
        creation_method="submit file", auto_rename=auto_rename, state="uploaded")

    collision_list = get_collision_list(new_file_map.values())
    
    return disposition, certify_results, new_file_map, collision_list


def restrict_genre(crds_filetype, uploaded_files):
    """Ensure all `uploaded_files` tuples correspond to the genre specified by
    crds_filetype:  mapping or reference.    
    """
    for uploaded in uploaded_files:
        if crds_filetype == "mapping":
            if not rmap.is_mapping(uploaded):
                raise CrdsError("Can't submit non-mapping file: " + repr(uploaded) + " using this page.")
        else:
            if rmap.is_mapping(uploaded):
                raise CrdsError("Can't submit mapping file: " + repr(uploaded) + " using this page.")

def submit_file_list(observatory, uploaded_files, description, submitter, submitter_email, 
        creator_name="unknown", change_level="SEVERE", creation_method="submit file", 
        auto_rename=True, state="uploaded"):
    """Ingest a list of `uploaded_files` tuples into CRDS."""
    new_file_map = {}
    for (original_name, uploaded_path) in uploaded_files.items():
        new_basename = do_submit_file( observatory, original_name, uploaded_path,
            description, submitter, submitter_email, creator_name=creator_name, 
            change_level=change_level, state="uploaded", auto_rename=auto_rename)
        new_file_map[original_name] =  new_basename
    return new_file_map

def do_submit_file(observatory, original_name, upload_location, description, 
        submitter, submitter_email, creator_name="unknown", change_level="SEVERE", 
        creation_method="submit file", auto_rename=True, state="uploaded"):
    """Do the core processing of a file submission,  including file certification 
    and blacklist checking, naming, upload, and record keeping.
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

    # CRDS keeps all new files in a standard layout.  Existing files in /grp/cdbs
    # are currently referenced by standard symlinks in the CRDS server file tree.
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
        return crds_render(request, "certify_input.html", requires_pmaps=True)
    else:
        return certify_post(request)

# @profile("certify5.stats")
def certify_post(request):
    """View fragment to process file certification POSTs."""

    context = get_recent_or_user_context(request)
    compare_old_reference = "compare_old_reference" in request.POST
    comparison_context = context if compare_old_reference else None

    all_files = models.get_fileblob_map()

    remove_dir, uploaded_files = get_files(request)
    
    _disposition, certify_results = certify_file_list(uploaded_files.items(), context=comparison_context, 
        compare_old_reference=compare_old_reference)

    blacklist_results = get_blacklist_file_list(uploaded_files.items(), all_files=all_files)

    return crds_render(request, "certify_results.html", {
             "certify_results":certify_results,
             "blacklist_results":blacklist_results,
    })

def get_blacklist_file_list(upload_tuples, all_files):
    """Return the mapping of blacklist status and blacklisted_by list for the
    given `uploaded_tuples` with respect to `all_files`.
    
    Returns { original_name :  (blacklist_status, blacklisted_by), ... }
    """
    blacklist_results = {}
    for (original_name, upload_path) in upload_tuples:
        try:
            blacklisted_by = get_blacklists(
                original_name, upload_path, ignore_self=False, files=all_files)
        except Exception:
            blacklisted_by = []
            blacklist_status = "Error"
        else:        
            if blacklisted_by:
                blacklist_status = "Blacklisted"
            else:
                blacklist_status = "OK"
        blacklist_results[original_name] = (blacklist_status, blacklisted_by)
    return blacklist_results

@capture_output
def _captured_certify(original_name, uploaded_path, filemap=None, context=None, compare_old_reference=False):
    """Configure certify and capture it's stdout/stderr."""
    certify.certify_files([uploaded_path], context=context, dump_provenance=True, check_references=False, 
                          is_mapping=rmap.is_mapping(original_name), trap_exceptions=True)

def captured_certify(original_name, uploaded_path, check_references=True, filemap=None, context=None,
                     compare_old_reference=False):
    output = _captured_certify(original_name, uploaded_path, filemap, context, compare_old_reference)[1]
    if ": ERROR" not in output:
        if ": WARNING" not in output:
            status = "OK"
        else:
            status = "Warnings"
    else:
        status = "Failed."
    output = output.replace(uploaded_path, original_name)
    output = output.replace(os.path.basename(uploaded_path), original_name)
    
    if status != "Failed.":    # if OK the rmap should load...
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

def certify_file_list(upload_tuples, check_references=True, context=None, compare_old_reference=False):
    """Certify the list of `upload_tuples` specifying uploaded files.
    
    If `check_references` is True,  make sure references referred to by mappings exist.
    
    If `context` is specified, verify references and mappings relative to the corresponding
    files in that context.
    
    If `compare_old_references` is True,  compare references to the corresponding files in the context.
    
    Returns disposition,  sorted({uploaded_name :  (status, <certify_output>) }.items())
    
    where disposition is either "" or "bad files" and used to suppress confirmation.
    """
    filemap = models.get_fileblob_map(models.OBSERVATORY)
    certify_results = {}
    disposition = ""
    for (original_name, upload_path) in upload_tuples:
        # In order to capture output easily,  run as subprocess...
        status, output = captured_certify(original_name, upload_path, 
            check_references=check_references, filemap=filemap, context=context, 
            compare_old_reference=compare_old_reference)
        certify_results[original_name] = status, output
        if status == "Failed.":
            disposition = "bad files"
    return disposition, sorted(certify_results.items())

# ===========================================================================

@error_trap("batch_submit_reference_input.html")
@log_view
@login_required
# @profile("batch_submit_reference.stats")
def batch_submit_references(request):
    """View to return batch submit reference form or process POST."""
    if request.method == "GET":
        return crds_render(request, "batch_submit_reference_input.html", requires_pmaps=True)
    else:
        return batch_submit_references_post(request)
    
def batch_submit_references_post(request):
    """View fragment to process file batch reference submnission POSTs."""
    pmap_name = get_recent_or_user_context(request)
    description = validate_post(request, "description", DESCRIPTION_RE)
    creator = validate_post(request, "creator", PERSON_RE)
    change_level = validate_post(request, "change_level", models.CHANGE_LEVELS)
    auto_rename = "auto_rename" in request.POST
    compare_old_reference = "compare_old_reference" in request.POST 
    remove_dir, uploaded_files = get_files(request)
    
    disposition, new_references_map, new_mappings_map, reference_certs, mapping_certs, mapping_diffs, collision_list = bsr_core(
        pmap_name, uploaded_files, description, str(request.user), str(request.user.email), 
        creator, change_level, auto_rename, compare_old_reference)
    
    # Map from old filenames to new filenames,  regardless of origin / purpose
    new_file_map = new_mappings_map.items() + new_references_map.items()
    
    bsr_results = {
                "pmap" : pmap_name,

                "new_file_map" : new_file_map,
                
                "generated_files" : sorted(new_mappings_map.values()), 
                "submission_kind" : "batch submit",
                "title" : "Batch Reference Submit",
                "description" : description,
                
#                "reference_certs" : reference_certs,
#                "mapping_certs" : mapping_certs, 
                "certify_results" : reference_certs + mapping_certs,
                "collision_list" : collision_list,
                
                "diff_results" : mapping_diffs,

                "more_submits" : "/batch_submit_references/",
                "disposition": disposition,                
            }
    
    return render_repeatable_result(request, "batch_submit_reference_results.html", bsr_results)

def bsr_core(pmap_name, uploaded_files, description, user_name, user_email, creator, 
             change_level, auto_rename, compare_old_reference):
    """bsr_core implements batch submit reference functionality independently of 
    web requests and responses.  bsr_core does however interact with Django models.
    """
    pmap = rmap.get_cached_mapping(pmap_name)

    # Verify that ALL references certify,  raise CrdsError on first error.
    comparison_context = pmap_name if compare_old_reference else None
    reference_disposition, reference_certs = certify_file_list(uploaded_files.items(), 
        context=comparison_context, compare_old_reference=compare_old_reference)

    # Refactor with temporary rmap files and refrerences to support detecting 
    # problems with refactoring prior to generating official names.
    old_rmaps = bsr_temporary_refactor(pmap, uploaded_files)
    
    # name the references and get them into CRDS.
    new_references_map = bsr_submit_references(pmap, uploaded_files, 
        description, user_name, user_email, creator, change_level, auto_rename)
    
    # Generate modified rmaps using real reference names and
    new_mappings_map = bsr_generate_real_rmaps(pmap, old_rmaps, new_references_map,
        description, user_name, user_email, creator, change_level)
    
    rmap_disposition, rmap_certs = bsr_certify_new_mapping_list(new_mappings_map, context=comparison_context)
    
    # Generate a new context referring to the new rmap
    higher_level_mapping_map = do_create_contexts(pmap.name, new_mappings_map.values(), 
        description, user_name, user_email, state="uploaded")
    
    new_mappings_map.update(higher_level_mapping_map)

    collision_list = get_collision_list(new_mappings_map.values())
    
    # Just display the .pmap,  which recursively captures the others and sorts first.
    diff_results = mass_differences(sorted(new_mappings_map.items())[:1])
    
    disposition = rmap_disposition or reference_disposition
    
    return (disposition, new_references_map, new_mappings_map, reference_certs, rmap_certs, diff_results, collision_list)

def bsr_certify_new_mapping_list(rmap_replacement_map, context):
    """Certify the new rmaps from `rmap_replacement_map` relative to .pmap `context`.
    Return { old_rmap : certify_output_for_new_rmap,  ... }
    """
    files = [(mapping, rmap.locate_mapping(mapping)) for mapping in rmap_replacement_map.values()]
    new_to_old = utils.invert_dict(rmap_replacement_map)
    disposition, certify_results = certify_file_list(files, context=context, check_references=False)
    certify_results = { new_to_old[mapping]: results for (mapping, results) in certify_results }
    return disposition, sorted(certify_results.items())

# .............................................................................

def bsr_temporary_refactor(pmap, uploaded_files):
    """Try out refactoring,  filekind-by-filekind,  and return a list of the affected rmaps.
    Returns [ replaced_rmaps... ]
    """
    instr_filekind_groups = bsr_group_references(pmap, uploaded_files)
    return [ bsr_temporary_refactor_filekind(pmap, uploaded_references, instrument, filekind)
            for ((instrument, filekind), uploaded_references) in instr_filekind_groups.items() ]

def bsr_group_references(pmap, uploaded_files):
    """Groups uploaded files by instrument and type.
    Returns {(instrument,filekind) : [part_of_uploaded_files...]}
    """
    old_instr = None
    groups = {}
    for (original_name, uploaded_path) in uploaded_files.items():
        try:
            instrument, filekind = utils.get_file_properties(pmap.observatory, uploaded_path)
        except Exception:
            raise CrdsError("Can't determine instrument or file type for " + srepr(original_name))
        if old_instr is not None:
            assert instrument == old_instr, "More than one instrument submitted at " + srepr(original_name) + \
            " " + srepr(old_instr) + " vs. " + srepr(instrument)
        old_instr = instrument
        if (instrument, filekind) not in groups:
            groups[(instrument, filekind)] = {}
        groups[(instrument, filekind)][original_name] = uploaded_path 
    return groups

def bsr_temporary_refactor_filekind(pmap, uploaded_files, instrument, filekind):
    """Refactor the original rmap inserting temporary references, creating a 
    temporary rmap to see what actions will occur.   Raise an exception if 
    any of the submitted files are duds.
    """
    old_rmap = pmap.get_imap(instrument).get_rmap(filekind).name
    old_rmap_path = rmap.locate_mapping(old_rmap, pmap.observatory)
    tmp_rmap = tempfile.NamedTemporaryFile()
    refactor.rmap_insert_references(old_rmap_path, tmp_rmap.name, uploaded_files.values())
    # XXX TODO unhandled files,  references resulting in no change.
    # XXX TODO duplicate matches,  references changing the same path.    
    return old_rmap

# .............................................................................

def bsr_submit_references(pmap, uploaded_files, description, user_name, user_email,
                          creator, change_level, auto_rename):
    """Add the uploaded references to CRDS with the supplied metadata.
    Returns { uploaded_name :  official_name, ... }
    """
    # Once both references and refactoring checks out,  submit reference files
    # and collect mapping from uploaded names to official names.
    new_references = {}
    for (original_name, uploaded_path) in sorted(uploaded_files.items()):
        new_basename = do_submit_file( 
            pmap.observatory, original_name, uploaded_path,
            description, user_name, user_email, creator, 
            change_level, creation_method="batch submit",
            state="uploaded", auto_rename=auto_rename)
        new_references[original_name] = str(new_basename)
    return new_references

# .............................................................................

def bsr_generate_real_rmaps(pmap, old_rmaps, new_references_map,
        description, user_name, user_email, creator, change_level):
    """Generate and submit official rmaps correspending to `old_rmaps` in 
    derivation context `pmap`,  inserting references from `new_references_map`.
    
    Now that we know that refactoring works and what the new references will be
    named,  allocate new supporting rmap names and refactor again for real.
    
    Return { old_rmap : new_rmap, ...}
    """
    observ = pmap.observatory
    # Dig these out of the database rather than passing them around.
    reference_paths = [ models.FileBlob.load(new_reference).pathname
                        for new_reference in new_references_map.values() ]
    rmap_replacement_map = {}
    for old_rmap in old_rmaps:
        (instrument, filekind) = utils.get_file_properties(pmap.observatory, old_rmap)
        these_ref_paths = [ refpath for refpath in reference_paths 
            if (instrument, filekind) == utils.get_file_properties(pmap.observatory, refpath) ]
        new_rmap = get_new_name(pmap.observatory, instrument, filekind, ".rmap")
        rmap_replacement_map[old_rmap] = new_rmap
        new_rmap_path = rmap.locate_mapping(new_rmap)
        old_rmap_path = rmap.locate_mapping(old_rmap)
        # refactor inserting references.
        refactor.rmap_insert_references(old_rmap_path, new_rmap_path, these_ref_paths)
        # Submit the new rmap with added references
        models.add_crds_file(pmap.observatory, new_rmap, new_rmap_path,  
                         user_name, user_email, description, 
                         change_level=change_level, creator_name=creator, state="uploaded")
    return rmap_replacement_map

# ============================================================================

@error_trap("base.html")
@login_required
@log_view
def submit_confirm(request):
    """Accept or discard proposed files from various file upload and
    generation mechanisms.
    """
    button = validate_post(request, "button", "confirm|cancel")
    
    submission_kind = validate_post(request, "submission_kind", models.AUDITED_ACTIONS)
    description = validate_post(request, "description", DESCRIPTION_RE)
    new_file_map = compat.literal_eval(str(request.POST["new_file_map"]))
    new_files = dict(new_file_map).values()
    generated_files = compat.literal_eval(str(request.POST["generated_files"]))
    user = str(request.user)
    more_submits = validate_post(request, "more_submits", URL_RE)
    results_id = validate_post(request, "results_id", "\d+")
    
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

    if button == "confirm":
        for file in set(new_files + generated_files):
            models.AuditBlob.new(
                request.user, submission_kind, file, description, 
                str(new_file_map), 
                instrument=instrument, filekind=filekind)    
        deliver_file_list( request.user, sconfig.observatory, 
            set(new_files + generated_files), description, submission_kind)
        disposition = "confirmed"
        for map in generated_files:
            if map.endswith(".pmap"):
                models.set_default_context(map)
    else:
        destroy_file_list(set(new_files + generated_files))
        disposition = "cancelled"
        
    models.RepeatableResultBlob.set_parameter(results_id, "disposition" , disposition)

    return crds_render(request, "confirmed.html", {
                "confirmed" : button == "confirm",
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
                
    diff_results = mass_differences([(file1_orig, file2_orig, file1_path, file2_path)])

    if uploaded1: 
        remove_temporary(file1_path)
    if uploaded2:
        remove_temporary(file2_path)
        
    return crds_render(request, "difference_results.html", { "diff_results" : diff_results })

def mass_differences(pair_or_quad_tuples, connector=" --> "):
    """Get the differences info for each tuple in `pair_or_quad_tuples`,  where
    a pair is a tuple of two known file basenames,  and a quad adds full paths
    corresponding to the basenames,  which are probably file temporaries not in
    the official file tree. Used for file submission and multiple generated files.
    """
    # key must be a string to json encode as a repeatable result.
    diffs = { tup[0] +  connector + "<span class='blue'>" + tup[1] + "</span>" : 
                difference_core(*tup) for tup in pair_or_quad_tuples }
    return sorted(diffs.items())

def difference_core(file1_orig, file2_orig, file1_path=None, file2_path=None):
    """Compute the rendering dictionary for the differences include file."""

    if file1_path is None:
        file1_path = rmap.locate_mapping(file1_orig)
    if file2_path is None:
        file2_path = rmap.locate_mapping(file2_orig)
    
    def extension(filename): 
        """Return the file extension of `filename`."""
        return os.path.splitext(filename)[1]
    
    logical_diffs = map_text_diff_items = None
    if rmap.is_mapping(file1_orig) and rmap.is_mapping(file2_orig) and \
        extension(file1_orig) == extension(file2_orig):
        logical_diffs = mapping_logical_diffs(file1_path, file2_path, file1_orig, file2_orig)
        map_text_diffs = mapping_text_diffs(logical_diffs)
        # Compute root files separately since they may have upload paths.
        difference = textual_diff(file1_orig, file2_orig, file1_path, file2_path)
        map_text_diffs[str((file1_orig, file2_orig))] = difference
        map_text_diff_items = sorted(map_text_diffs.items())
        logical_diffs = [[ str(tup) for tup in diff] for diff in logical_diffs]
    elif file1_orig.endswith(".fits") and file2_orig.endswith(".fits"):
        diff_lines = pysh.lines("fitsdiff ${file1_path} ${file2_path}")
        diff_lines = format_fitsdiffs(diff_lines, file1_path, file2_path,
            file1_orig, file2_orig)
        difference = ''.join(diff_lines)
    elif re.match(GEIS_HEADER_RE, file1_orig) and re.match(GEIS_HEADER_RE, file2_orig) and \
        extension(file1_orig) == extension(file2_orig):
        difference = textual_diff(file1_orig, file2_orig, file1_path, file2_path)
    else:
        raise CrdsError("Files should be either CRDS mappings "
                        "of the same type or .fits files")        
    if not difference.strip():
        difference = "no differences"
    return {
       "logical_diffs" : logical_diffs,
       "map_text_diff_items" : map_text_diff_items,
       "difference" : difference,
       "file1" : file1_orig,
       "file2" : file2_orig,
    }

def textual_diff(file1_orig, file2_orig, file1_path=None, file2_path=None):
    """Return the output of the context diff of two files."""
    if file1_path is None:
        file1_path = rmap.locate_mapping(file1_orig)
    if file2_path is None:
        file2_path = rmap.locate_mapping(file2_orig)
    diff_lines = pysh.lines("diff -b -u -FUseAfter ${file1_path} ${file2_path}")
    result = []
    for line in diff_lines:
        line = line.replace(file1_path, file1_orig)
        line = line.replace(file2_path, file2_orig)
        result.append(line)
    return ''.join(result)

def mapping_logical_diffs(file1, file2, file1_orig, file2_orig):
    """Return the logical differences between two mapping files."""
    try:
        map1 = rmap.load_mapping(file1, ignore_checksum=True)
        map2 = rmap.load_mapping(file2, ignore_checksum=True)
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
        for tup in ldiff:
            if isinstance(tup, tuple) and len(tup) == 2 and \
                tup[0].endswith("map") and tup[1].endswith("map"):
                file1_orig, file2_orig = tup
                file1_path = rmap.locate_mapping(file1_orig)
                file2_path = rmap.locate_mapping(file2_orig)
                if (file1_orig, file2_orig) not in diff_map:
                    try:
                        diffs = textual_diff(
                            file1_orig, file2_orig, file1_path, file2_path)
                    except Exception, exc:
                        diffs = "diffs failed: " + str(exc)
                    diff_map[str((file1_orig, file2_orig))] = diffs
    return diff_map

def format_fitsdiffs(lines, file1, file2, file1_orig, file2_orig):
    """Add some colorization to output `lines` from fitsdiff, replacing
    `file1` and `file2` with their basenames.
    """
    for i in range(len(lines)):
        line = clean_path(lines[i], file1, file1_orig)
        line = clean_path(line, file2, file2_orig)
        if "Primary HDU" in line or re.search("Extension HDU \d+", line):
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
        
    context = models.get_default_context(blob.observatory)
    used_by_files = list(uses.uses([filename], blob.observatory))
    
    if blob and blob.type == "reference":
        match_paths = matches.find_full_match_paths(context, filename)
        match_paths = [flatten(path) for path in match_paths]
        try:
            certify_results = captured_certify(filename, blob.pathname, check_references=True, context=context)
        except Exception, exc:
            log.warning("certify failed for", blob.pathname)
            certify_results = None
    else:
        match_paths = []
        certify_results = captured_certify(filename, blob.pathname, check_references=False, context=context)

    return crds_render(request, "browse_results.html", { 
             "fileblob" : blob,
             "observatory" : blob.observatory,
             "related_actions": related_actions,
             "used_by_files" : used_by_files,
             "match_paths" : match_paths,
             "file_contents": file_contents,
             "certify_results" : certify_results,
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
    
    try:
        header = mapping.get_minimum_header(browsed_file)
    except Exception, exc:
        output = "<p class='error'>File header unavailable: '%s'</p>" % str(exc)
    else:
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
            already_in_use = models.FileBlob.load(name)
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
    filtered_activities = [blob for blob in filtered_activities if not blob.filename.endswith((".cat",))]
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
        return crds_render(request, "browse_db_input.html")
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
        return crds_render(request, "create_contexts_input.html", requires_pmaps=True)
    else:
        return create_contexts_post(request)

def create_contexts_post(request):
    """View fragment handling create_contexts POST case."""
    pmap_name = get_recent_or_user_context(request)
    updated_rmaps = validate_post(request, "rmaps", is_list_of_rmaps)
    description = validate_post(request, "description", DESCRIPTION_RE)
    
    existing_names = rmap.get_cached_mapping(pmap_name).mapping_names()
#    for updated in updated_rmaps:
#        assert updated not in existing_names, "Rmap " + repr(updated) + " is already in context " + repr(pmap_name)
        

    new_name_map = do_create_contexts(pmap_name, updated_rmaps, description,
        request.user, request.user.email, state="uploaded")

    old_mappings = sorted(new_name_map.keys())
    new_mappings = sorted(new_name_map.values())
    
    collision_list = get_collision_list(new_mappings)
    
    return render_repeatable_result(request, "create_contexts_results.html", {
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
    new_contexts = newcontext.generate_new_contexts(pmap_name, updates_by_instrument, new_name_map)
 
    new_pmap = [ctx for ctx in new_contexts if ctx.endswith(".pmap")][0]
    new_loc = rmap.locate_mapping(new_pmap)  
    do_certify_file(new_loc, new_loc, context=pmap_name)

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
    return { old:new_name(old) for old in [old_pipeline] + updates.keys() }

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
    delivered_files = [str(x) for x in sorted(delivered_files)]
    catalog = str(deliver_file_catalog(observatory, delivered_files, "I"))
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
    catpath = os.path.join(sconfig.CRDS_CATALOG_DIR, catalog)
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
    dirs = sconfig.CRDS_DELIVERY_DIRS
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
    for site in sconfig.CRDS_DELIVERY_DIRS + [os.path.dirname(catalog)]:
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

@profile("get_archive.stats")
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

    response = HttpResponse(mimetype="application/octet-stream")
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
                blob = validate_get(request, var, is_available_file_blob)
                total_size += blob.size
                if total_size >= sconfig.MAX_ARCHIVE_SIZE:
                    raise CrdsError("Archive request is too large.   Request bundled mappings only.")
                files[blob.name] = blob.pathname
        utils.ensure_dir_exists(bundle_path)    
        cache_file = open(bundle_path, "wb")
        tar = tarfile.open(mode=ARCH_MODES[arch_extension], fileobj=cache_file,
                           dereference=True)
        for filename, path in files.items():
            tar.add(path, arcname=filename)
        tar.close()
        cache_file.close()
    return bundle_path
    
def cached_bundle_path(request, arch_extension):
    """Compute the sha1sum of the filenames requested for a bundle to see
    if a bundle is already cached.
    """
    names = arch_extension # archive format is important,  download filename isn't
    for var in request.GET:
        if var.startswith("file"):
            name = validate_get(request, var, FILE_RE)
            names += name
    checksum = utils.str_checksum(names)
    path = sconfig.CRDS_ARCHIVE_CACHE_DIR + "/" + checksum + "."+ arch_extension
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
            }, requires_pmaps=True)
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
    
