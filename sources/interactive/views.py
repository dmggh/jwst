"""This module defines the Django view functions which respond to HTTP requests
and return HTTP response objects.
"""

# Create your views here.
import sys
import os.path
import re
import cStringIO
import traceback
import tarfile
import glob

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
from django.contrib.auth.decorators import login_required

import pyfits

from crds import (rmap, utils, timestamp, uses, matches, checksum, compat, log, config)
from crds import CrdsError

from crds.timestamp import (DATE_RE_STR, TIME_RE_STR)

from . import (models, database, web_certify, web_difference, submit, versions)
from .models import FieldError, MissingInputError
from .common import capture_output, srepr, profile

import crds.server.generic_config as sconfig
from crds.server.jsonapi import views as jsonapi_views

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
    
    # Generate a first pass of the response HTML.
    loaded_template = loader.get_template(template)
    context = RequestContext(request, rdict)
    response = loaded_template.render(context)
    
    # Remove file paths and fix temporary names with client side names
    uploaded_pairs = rdict.get("uploaded_file_names", get_uploaded_filepaths(request))
    response = scrub_file_paths(response, uploaded_pairs)
    
    return HttpResponse(response)
            
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
    response = response.replace(config.get_crds_mappath() + "/" + observatory + "/", "")
    response = response.replace(config.get_crds_refpath() + "/" + observatory + "/", "")
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
        original_name = validate_post(request, knownvar, is_known_file)
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
    log.info("Scanning", srepr(dir), "for uploaded files.")
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
# ===========================================================================
# ===========================================================================

def index(request):
    """Return the top level page for all of interactive CRDS."""
    return crds_render(request, "index.html")

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

def render_repeatable_result(request, template, rdict):
    """Create a repeatable results model instance and redirect to it."""
    rdict["user"] = str(request.user)
    rdict["uploaded_file_names"] = get_uploaded_filepaths(request)
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
    """Support adding new files to the upload area."""
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
        log.info("upload_delete", srepr(ingest_filepath))
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
        # base on the context and datset,  compute best references
        header = pmap.get_minimum_header(dataset_path, original_name=dataset_name)
    elif dataset_mode == "dataset_local":
        header = header_string_to_header(request.POST["dataset_local"])
        header = pmap.minimize_header(header)
        dataset_name = validate_post(request, "dataset_name", FILE_RE)
    elif dataset_mode == "dataset_archive":
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
            log.warning("Dropping illegal keyword '%s' with value '%s'." % (key,value))
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
    remove_dir, uploaded_files = get_files(request)
    
    all_files = models.get_fileblob_map()

    _disposition, certify_results = web_certify.certify_file_list(uploaded_files.items(), context=comparison_context, 
        compare_old_reference=compare_old_reference)

    blacklist_results = web_certify.get_blacklist_file_list(uploaded_files.items(), all_files=all_files)

    return crds_render(request, "certify_results.html", {
             "certify_results":certify_results,
             "blacklist_results":blacklist_results,
    })

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
    
    bsr = submit.BatchReferenceSubmission(pmap_name, uploaded_files, description, user=request.user, creator=creator, 
        change_level=change_level, auto_rename=auto_rename, compare_old_reference=compare_old_reference)
    
    disposition, new_references_map, new_mappings_map, reference_certs, mapping_certs, mapping_diffs, collision_list = bsr.submit()
    
    # Map from old filenames to new filenames,  regardless of origin / purpose
    new_file_map = new_mappings_map.items() + new_references_map.items()
    
    bsr_results = {
                "pmap" : pmap_name,

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

                "more_submits" : "/batch_submit_references/",
                "disposition": disposition,                
            }
    
    return render_repeatable_result(request, "batch_submit_reference_results.html", bsr_results)

# ============================================================================

@error_trap("base.html")
@login_required
@log_view
def submit_confirm(request):
    """Accept or discard proposed files from various file upload and
    generation mechanisms.
    """
    button = validate_post(request, "button", "confirm|cancel")
    results_id = validate_post(request, "results_id", "\d+")
    try:
        result = models.RepeatableResultBlob.get(int(results_id)).parameters
    except Exception, exc:
        raise CrdsError("Error fetching result: " + results_id + " : " + str(exc))

    usr = str(request.user)
    assert usr == result.user, "User mismatch between submit and confirmation: " + repr(usr) + " vs. " + repr(result.user)

    confirmed = (button == "confirm")
    new_file_map = dict(result.new_file_map)
    new_files = new_file_map.values()

    context_map = submit.submit_confirm_core( confirmed, result.submission_kind, result.description, new_files, 
                                              result.context_rmaps, result.user,  result.pmap)

    new_file_map = sorted(new_file_map.items() + context_map.items())
    generated_files = sorted([(old, new) for (old,new) in new_file_map if old not in result.uploaded_basenames])
    uploaded_files = [(old, new) for (old, new) in new_file_map if (old, new) not in generated_files]
    
    # rmaps specified for context generation but not uploaded or generated
    context_rmaps = [filename for filename in result.context_rmaps if filename not in dict(generated_files).values() + result.uploaded_basenames]
    
    confirm_results = dict(
        uploaded_files=uploaded_files,
        context_rmaps=context_rmaps,
        generated_files=generated_files,
        new_file_map=new_file_map,
        more_submits=result.more_submits,
        confirmed=confirmed)
    
    if confirmed:
        clear_uploads(request, result.uploaded_basenames)
        models.RepeatableResultBlob.set_parameter(results_id, "disposition" , "confirmed")
    else:
        models.RepeatableResultBlob.set_parameter(results_id, "disposition" , "cancelled")
    
    return render_repeatable_result(request, "confirmed.html", confirm_results)
    
# ===========================================================================

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
    updated_rmaps = validate_post(request, "rmaps", is_list_of_rmaps)
    description = validate_post(request, "description", DESCRIPTION_RE)
    return render_repeatable_result(request, "create_contexts_results.html", {
                "pmap": pmap_name,
                "new_file_map" : [],
                "uploaded_basenames": [],
                "context_rmaps" : updated_rmaps, 
                "submission_kind" : "new context",
                "title" : "Create Contexts",
                "description" : description,
                "more_submits" : "/create_contexts/",
                "collision_list" : [],
            })
    
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
    
def submit_files_post(request, crds_filetype):
    """Handle the POST case of submit_files, returning dict of template vars."""
    # crds_filetype constrained by RE in URL to 'mapping' or 'reference'.
    observatory = get_observatory(request)
    compare_old_reference = "compare_old_reference" in request.POST
    generate_contexts = "generate_contexts" in request.POST
    pmap_name = get_recent_or_user_context(request)
    description = validate_post(request, "description", DESCRIPTION_RE)
    creator = validate_post(request, "creator", PERSON_RE)
    auto_rename = "auto_rename" in request.POST    
    change_level = validate_post(request, "change_level", models.CHANGE_LEVELS)            
    remove_dir, uploaded_files = get_files(request)
    
    simple = submit.SimpleFileSubmission(pmap_name, uploaded_files, description, user=request.user,  
        creator=creator, change_level=change_level, auto_rename=auto_rename, compare_old_reference=compare_old_reference)
    
    disposition, certify_results, new_file_map, collision_list, context_rmaps = simple.submit(crds_filetype, generate_contexts)    

    return render_repeatable_result(request, 'submit_results.html', {
                "crds_filetype": crds_filetype,
                "collision_list" : collision_list,

                "context_rmaps" : context_rmaps,
                "new_file_map" : sorted(new_file_map.items()),
                "uploaded_basenames" : uploaded_files.keys(),
                "submission_kind" : "submit file",
                "title" : "Submit File",
                "description" : description,
                "pmap" : pmap_name,
                
                "certify_results" : certify_results,
                "more_submits" : "/submit/" + crds_filetype + "/",
                
                "disposition" : disposition,
                })

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
        file1_orig, file1_path = handle_known_or_uploaded_file(
            request, "filemode1", "file_known1", "file_uploaded1")
        file2_orig, file2_path = handle_known_or_uploaded_file(
            request, "filemode2", "file_known2", "file_uploaded2")
                
    diff_results = web_difference.mass_differences([(file1_orig, file2_orig, file1_path, file2_path)])

    return crds_render(request, "difference_results.html", { 
            "file1" : file1_orig,
            "file2" : file2_orig,
            "diff_results" : diff_results 
        })

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
            certify_results = web_certify.captured_certify(filename, blob.pathname, check_references=True, context=context)
        except Exception, exc:
            log.warning("certify failed for", blob.pathname)
            certify_results = None
    else:
        match_paths = []
        certify_results = web_certify.captured_certify(filename, blob.pathname, check_references=False, context=context)

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
        tar = tarfile.open(mode=ARCH_MODES[arch_extension], fileobj=cache_file, dereference=True)
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
    
