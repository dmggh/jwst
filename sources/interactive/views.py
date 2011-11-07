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

# from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import django.utils.safestring as safestring

import django.contrib.auth
import django.contrib.auth.models
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.datastructures import DotExpandedDict

import pyfits

from crds import (rmap, utils, certify, timestamp, uses, matches, newcontext, 
                  checksum, pysh, compat)

import crds.server.config as config
import crds.server.interactive.models as models
from crds.server.interactive.models import FieldError, MissingInputError

import crds.server.jsonapi.views as jsonapi_views

HERE = os.path.dirname(__file__) or "./"

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
            assert "|" not in choice, "Found | in choice " + repr(choice) + \
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
    return check_value(value, pattern, "Invalid value " + repr(value) + 
                                        " for " + repr(variable))
def validate_get(request, variable, pattern):
    """Check a GET `variable` from `request`,  ensuring that it meets the
    check_value() conditions specified by `pattern`.
    """
    value = str(request.GET[variable]).strip()
    return check_value(value, pattern, "Invalid value " + repr(value) + 
                                        " for " + repr(variable))

# ===========================================================================

# "pattern" functions for validate_post/get

FILE_RE = r"\w+(\.fits|\.pmap|\.imap|\.rmap|\.r\d[hd])"
DESCRIPTION_RE = r"[A-Za-z0-9._ ]+"
GEIS_HEADER_RE = r"\w+(\.r\dh)"
PERSON_RE = r"[A-Za-z_0-9\.@]*"

def is_pmap(filename):
    """Verify that `filename` names a known CRDS pipeline mapping.
    Otherwise raise AssertionError.
    """
    return is_mapping(filename, r"\.pmap")

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
        raise CrdsError("Invalid mapping filename " + repr(filename))
    if len(models.FileBlob.filter(filename=filename, type="mapping")) < 1:
        raise CrdsError("No database entry for " + repr(filename) + \
            ".  Must name a known CRDS mapping.")
    return filename

def is_reference(filename, extension=r"\.fits|\.r\dh|\.r\dd"):
    """Verify that `filename` names a known CRDS reference file.
    Otherwise raise AssertionError.
    """
    if not re.match(r"\w+"+extension, filename):
        raise CrdsError("invalid reference filename " + repr(filename))
    if len(models.FileBlob.filter(filename=filename, type="reference")) < 1:
        raise CrdsError("No database entry for " + repr(filename) + \
            ".  Must name a known CRDS reference file.")
    return filename

def is_known_file(filename):
    """Verify that `filename` identifies a file already known to CRDS."""
    if not re.match(FILE_RE, filename):
        raise CrdsError("invalid filename " + repr(filename))
    if len(models.FileBlob.filter(filename=filename)) < 1:
        raise CrdsError("No database entry for " + repr(filename) + 
                        ".  Must name a known CRDS reference or mapping.")
    return filename

def is_deliverable_file(filename):
    """Return `filename` iff `filename` names a file suitable for delivery."""
    try:
        blob = models.FileBlob.load(filename)
    except LookupError:
        raise CrdsError("File " + repr(filename) + " is not known to CRDS.")
    assert blob.status == "submitted", "File " + repr(filename) + \
        " cannot be delivered."
    assert not blob.blacklisted_by, "File " + repr(filename) + \
        " is blacklisted by " + repr(blob.blacklisted_by)
    
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

DATETIME_RE_STR = "(\d\d\d\d\-\d\d\-\d\d\s+\d\d:\d\d:\d\d)"

def is_datetime(datetime_str):
    """Raise an assertion error if `datetime_str` doesn't look like a CRDS date.
    Otherwise return `datetime_str`.
    """
    assert re.match(DATETIME_RE_STR, datetime_str), \
        "Invalid date/time.  Should be YYYY-MM-DD HH:MM:SS"
    try:
        timestamp.parse_date(datetime_str)
    except ValueError, exc:
        raise CrdsError(str(exc))
    return datetime_str

DESCRIPTION_RE = "[^<>]+"

def get_observatory(request):
    return validate_post(request, "observatory", models.OBSERVATORIES)

def usernames():
    try:
        return [str(x) for x in django.contrib.auth.models.User.objects.filter()]
    except Exception:
        return ["*"]

# ===========================================================================

def render(request, template, dict_=None):
    """Render a template,  making same-named inputs from request available
    for echoing.
    """
    rdict = {   # standard template variables
        "observatories":models.OBSERVATORIES,
        "instruments":models.INSTRUMENTS+["*"],
        "filekinds":models.FILEKINDS+["*"],
        "extensions":models.EXTENSIONS+["*"],
        "users": ["*"] + usernames(),
        "current_path" : request.get_full_path()
    }
    
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
    
    # Set up variables required to support django-json-rpc Javacsript
    jsonrpc_vars = jsonapi_views.get_jsonrpc_template_vars()
    for var in jsonrpc_vars:
        if var in rdict:
            raise CrdsError("Template variable collision on " + repr(var))
        else:
            rdict[var] = jsonrpc_vars[var]
            
    return render_to_response(template, RequestContext(request, rdict))

# ===========================================================================

def handle_known_or_uploaded_file(request, name, modevar, knownvar, uploadvar):
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
    return uploaded, original_name, filepath

def get_uploaded_file(request, formvar):
    """Return the DJango UploadedFile associated with `request` and `formvar`,
    raising an exception if it's original name does not end with one of
    `legal_exts` file extensions.   Handles <input type='file'>, part 1.
    """
    try:
        ufile = request.FILES[formvar]
    except KeyError:
        raise MissingInputError("Specify a file to upload for " + repr(formvar))
    if not re.match(FILE_RE, ufile.name):
        raise FieldError("Unexpected ile extension for " + \
                            repr(str(ufile.name)))
    return ufile

def upload_file(ufile, where):
    """Copy the Django UploadedFile to it's permanent location.
    Handle's <input type='file'> part 2.
    """
    utils.ensure_dir_exists(where)
    destination = open(where, 'wb+')
    for chunk in ufile.chunks():
        destination.write(chunk)
    destination.close()

def get_known_filepath(file):
    """Given the basename of a mapping or reference file, `file`,
    determine the full path of the file on the server.
    """
    try:
        blob = models.FileBlob.load(file)
    except LookupError:
        raise FieldError("CRDS doesn't know about file " + repr(file))
    return blob.pathname


def remove_temporary(filepath):
    """Attempt to remove `filepath`.  Ignore errors."""
    try:
        assert not filepath.startswith("/grp"), \
            "ERROR -- attempt to delete from Central Store"
        os.remove(filepath)
    except OSError:
        pass
    

# ===========================================================================

class CrdsError(Exception):
    """Something bad but understood happened in CRDS processing."""

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
                msg = "ERROR: " + str(exc)
                pars = dict(keys.items() + [("error_message", msg)])
                return render(request, template, pars)
            except CrdsError, exc:
                msg = "ERROR: " + str(exc)
                pars = dict(keys.items() + [("error_message", msg)])
                return render(request, template, pars)
            except FieldError, exc:
                msg = "ERROR: " + str(exc)
                pars = dict(keys.items() + [("error_message", msg)])
                return render(request, template, pars)
        trap.func_name = func.func_name
        return trap
    return decorator


# ===========================================================================
PROFILE_DECORATOR_RESULT = None
def profile(func):
    """Decorate a view with @profile to run cProfile when the view is accessed.
    """
    def profile_request(request, *args, **keys):
        """profile_request runs the runit() hack under the profiler and
        extracts the function result from a global.
        """
        def runit():
            """executes a function and stores the result globally."""
            global PROFILE_DECORATOR_RESULT
            PROFILE_DECORATOR_RESULT = func(request, *args, **keys)
        cProfile.runctx("runit()", locals(), locals())
        return PROFILE_DECORATOR_RESULT
    return profile_request

# ===================================================================

def capture_output(func):
    """Decorate a function with @capture_output to make it capture and return
    stdout/stderr as part of it's result.   Returns (original_result, outlines)
    """
    def captured(*args, **keys):
        """Temorarily re-assign stdout/stderr to a StringIO, run func,
        return captured output.
        """
        out = cStringIO.StringIO()
        oldout, olderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, out
        try:
            result = func(*args, **keys)
        finally:
            sys.stdout, sys.stderr = oldout, olderr
        out.seek(0)
        return result, out.readlines()
    return captured

# ===========================================================================
# ===========================================================================
# ===========================================================================

def index(request):
    """Return the top level page for all of interactive CRDS."""
    return render(request, "index.html", {})

# ===========================================================================

def logout(request):
    """View to get rid of authentication state and become nobody again."""
    django.contrib.auth.logout(request)
    return render(request, "logout.html", {})
        
# ===========================================================================

@error_trap("bestrefs_index2.html")
def bestrefs(request):
    """View to get the instrument context for best references."""
    if request.method == "GET":
        return render(request, "bestrefs_index2.html", {})
    else:
        return bestrefs_post(request)

def bestrefs_post(request):
    """View to get best reference dataset parameters."""

    mapping = get_default_or_user_context(request)
    context = rmap.get_cached_mapping(mapping)
        
    dataset_mode = validate_post(
        request, "dataset_mode", "dataset_archive|dataset_uploaded")
    if dataset_mode == "dataset_uploaded":
        uploaded_file = get_uploaded_file(request, "dataset_uploaded")
        dataset_path = uploaded_file.temporary_file_path()
        dataset_name = uploaded_file.name
        remove_temp_flag = True
    else:
        remove_temp_flag = True   # Assuming temp copy from archive.
        raise CrdsError("Archive interface not yet implemented.")
    
    # base on the context and datset,  compute best references
    header = context.get_minimum_header(dataset_path)
    bestrefs = context.get_best_references(header)
    
#    if remove_temp_flag:
#        remove_temporary(dataset_path)

    # organize and format results for HTML display    
    header_items = sorted(header.items())
    bestrefs_items = []
    for key, val in sorted(bestrefs.items()):
        if val.startswith("NOT FOUND"):
            val = val[len("NOT FOUND"):]
        bestrefs_items.append((key.upper, val))
    
    return render(request, "bestrefs_results.html", {
            "observatory" : context.observatory,
            "dataset_name" : dataset_name,
            "header_items" : header_items,
            "bestrefs_items" : bestrefs_items,
        })

def get_default_or_user_context(request):
    """Process standard request parameters for specifying context."""
    context_mode = validate_post(
        request, "context_mode", "context_default|context_user")
    if context_mode == "context_user":
        context = validate_post(request, "context_user", is_pmap_or_imap)
    else:
        observatory = get_observatory(request)
        context = models.get_default_context(observatory)
    return context    

# ============================================================================

@error_trap("submit_input.html")
@login_required
def submit_file(request, crds_filetype):
    """Handle file submission,  crds_filetype=reference|mapping."""
    if request.method == "GET":
        return render(request, 'submit_input.html', {
            "crds_filetype" :  crds_filetype,
        })
    else:
        return submit_file_post(request, crds_filetype)
    
def file_exists_somehow(filename):
    """Return True IFF `filename` really exists or CRDS thinks it does."""
    return os.path.exists(filename) or \
        models.FileBlob.exists(os.path.basename(filename))

def submit_file_post(request, crds_filetype):
    """Handle the POST case of submit_file,   returning dict of template vars.
    """
    observatory = get_observatory(request)
    uploaded_file = get_uploaded_file(request, "submitted_file")    
    description = validate_post(request, "description", DESCRIPTION_RE)
    creator = validate_post(request, "description", PERSON_RE)
    
    if crds_filetype == "reference":
        change_level = validate_post(
            request, "change_level", models.CHANGE_LEVELS)
        comparison_file = validate_post(
            request, "comparison_file", is_known_file)
    else:
        change_level = "SEVERE"
        comparison_file = None
        
    new_name = submit_file_doit( observatory, uploaded_file, description,
        str(request.user), request.user.email, creator, 
        change_level, comparison_file, )
        
    return render(request, 'submit_results.html', {
                "crds_filetype": crds_filetype,
                "baseperm":new_name,
                })
    
def submit_file_doit(observatory, uploaded_file, description, 
        submitter, submitter_email, creator_name="unknown",
        change_level="SEVERE", comparison_file=None, 
        creation_method="submit file", auto_rename=True):
    """Do the core processing of a file submission,  including file
    certification and blacklist checking, naming, upload,  and record
    keeping.
    """
    # Determine the temporary and permanent file paths, not yet copying.
    original_name = uploaded_file.name
    upload_location = uploaded_file.temporary_file_path()    
    
    # Check the file,  leaving no server state if it fails.  Give error results.
    do_certify_file(original_name, upload_location, check_references="exist")
    
    # Automatically 
    if auto_rename:
        permanent_name = auto_rename_file(
            observatory, uploaded_file.name, upload_location)
    else:
        if file_exists_somehow(original_name):
            raise FieldError("File " + repr(original_name) + " already exists.")    

    # CRDS keeps all new files in a standard layout.   Older files can be
    # grandfathered in by special calls to add_crds_file rather than "submission".
    permanent_location = rmap.locate_file(permanent_name, observatory)

    # Make sure none of the dependencies are blacklisted,  else fail w/o state.
    blacklisted_by = get_blacklists(original_name, upload_location)
    if blacklisted_by:
        raise CrdsError("File " + repr(original_name) + 
                        " is blacklisted by " + repr(blacklisted_by))
    
    # Copy the temporary file to its permanent location.
    upload_file(uploaded_file, permanent_location)
    
    # Make a database record for this file.
    blob = models.add_crds_file(observatory, original_name, permanent_location, 
            submitter, submitter_email, description, 
            creation_method=creation_method, audit_details="", 
            change_level=change_level, creator_name=creator_name)
    
    return os.path.basename(permanent_location)

def do_certify_file(basename, certifypath, check_references=None):
    """Run un-trapped components of crds.certify and re-raise any exception
    as a CrdsError which will be displayed as a form error on the submission
    page.
    
    basename is the name of the file on the user's system,  hopefully with a
    sane extension.   certifypath is a fully qualified path,  but sometimes
    with a temporary filename which is total garbage.
    """
    try:
        certify.certify_files([certifypath], check_references=None,
            trap_exceptions=False, is_mapping = rmap.is_mapping(basename))
    except Exception, exc:
        raise CrdsError(str(exc))
    if check_references in ["exist","contents"] and rmap.is_mapping(basename):
        ctx = rmap.load_mapping(certifypath)
        index = models.FileIndexBlob.load(ctx.observatory)
        for ref in ctx.reference_names():
            assert index.exists(ref), \
                "Reference " + repr(ref) + " is not known to CRDS."             
    
def get_blacklists(basename, certifypath, ignore_self=True):
    """Raise an exception if any of the child mappings or references of
    `basename` are blacklisted,  i.e. don't allow submissions which reference
    blacklisted files.
    """
    basename = str(basename)
    if rmap.is_mapping(basename):
        blacklisted_by = set()
        try:
            mapping = rmap.load_mapping(certifypath)
        except Exception, exc:
            raise CrdsError("Error loading " + repr(basename) + 
                            " for blacklist checking:  " + str(exc))
        
        blblob = models.BlacklistBlob.load(mapping.observatory)
        
        for child in mapping.mapping_names() + mapping.reference_names():       
            if ignore_self and child == os.path.basename(certifypath): 
                continue
            blby = blblob.is_blacklisted(child)
            if blby:
                blacklisted_by = blacklisted_by.union(set(blby))
                
        return sorted(list(blacklisted_by))
    else:
        return []

# ===========================================================================

@error_trap("blacklist_input.html")
@login_required
def blacklist_file(request):
    """Serve the blacklist input form or process the POST."""
    if request.method == "GET":
        return render(request, "blacklist_input.html")
    else:
        return blacklist_file_post(request)

# XXX Add "archive/catalog" action resulting from blacklisting

def blacklist_file_post(request):
    """View fragment to process the blacklist POST."""
    observatory = get_observatory(request)
    blacklist_root = validate_post(request, "file_known", is_known_file)
    badflag = validate_post(request, "badflag", "bad|ok")
    why = validate_post(request, "why", DESCRIPTION_RE)
    
    # Determine files which indirectly or directly reference `blacklist_root`
    uses_files = uses.uses([blacklist_root], observatory)

    all_blacklisted = [blacklist_root] + uses_files

    for also_blacklisted in all_blacklisted:
        if badflag == "bad":
            models.blacklist(also_blacklisted, blacklist_root)
        else:
            models.unblacklist(also_blacklisted, blacklist_root)
    
    instrument, filekind = utils.get_file_properties(
        observatory, blacklist_root)

    models.AuditBlob.new(
        request.user, "blacklist", blacklist_root, why, 
        "marked as " + repr(badflag.upper()),
        observatory=observatory, instrument=instrument, filekind=filekind)

    return render(request, "blacklist_results.html", 
                  { "all_blacklisted": all_blacklisted })

        
# ===========================================================================

@error_trap("certify_input.html")
# @profile
def certify_file(request):
    """View to return certify input form or process POST."""
    if request.method == "GET":
        return render(request, "certify_input.html")
    else:
        return certify_post(request)

def certify_post(request):
    """View fragment to process file certification POSTs."""
    uploaded, original_name, certified_file = handle_known_or_uploaded_file(
        request, "File", "filemode", "file_known", "file_uploaded")
            
    mapping = "--mapping" if rmap.is_mapping(original_name) else ""

    certify_lines = pysh.lines(
        "python -m crds.certify ${certified_file} ${mapping} --dump-provenance")
    certify_status = "OK" if "0 errors" in \
        [ x.strip() for x in certify_lines] else "Failed."    
    
    if not rmap.is_mapping(original_name):
        fitscheck_lines = [x.strip() for x in pysh.lines(
            "fitscheck --ignore-missing ${certified_file}")]
        fitscheck_status = "OK" if (not fitscheck_lines) or \
                ("0 errors" in fitscheck_lines) else "Failed."
    else:
        fitscheck_status = ""
        fitscheck_lines = []
        
    try:
        blacklisted_by = get_blacklists(
            original_name, certified_file, ignore_self=False)
    except:
        blacklisted_by = []
        blacklist_status = "Error"
    else:        
        if blacklisted_by:
            blacklist_status = "Blacklisted"
        else:
            blacklist_status = "OK"
    
    if uploaded:
        remove_temporary(certified_file)
        
    return render(request, "certify_results.html", 
            {"certify_status":certify_status,
             "fitscheck_status":fitscheck_status, 
             "blacklist_status":blacklist_status,
             "is_reference": not rmap.is_mapping(original_name),
             "certify_lines":certify_lines,
             "fitscheck_lines":fitscheck_lines,
             "blacklisted_by" : blacklisted_by,
             "certified_file":original_name})

# ===========================================================================

@error_trap("using_file_inputs.html")
def using_file(request):
    """View to return using_file input form or process POST."""
    if request.method == "GET":
        return render(request, "using_file_inputs.html")
    else:
        return using_file_post(request)
    
def using_file_post(request):
    """View fragment to process using_file POSTs."""
    observatory = get_observatory(request)
    referred_file = validate_post(request, "referred_file", is_known_file)
    uses_files = [x for x in uses.uses([referred_file], observatory) if x]    
    return render(request, "using_file_results.html", {
            'uses_files' : uses_files,
        })

# ===========================================================================

@error_trap("file_matches_inputs.html")
def file_matches(request):
    """View to return file_matches input form or process POST."""
    if request.method == "GET":
        return render(request, "file_matches_inputs.html")
    else:
        return file_matches_post(request)
    
def file_matches_post(request):
    """View fragment to process file_matches POSTs."""
    
    known_context = get_default_or_user_context(request)

    matched_reference = validate_post(request, "matched_reference", is_known_file)

    match_paths = matches.find_match_tuples(known_context, matched_reference)
    
    match_paths = [flatten(path) for path in match_paths]
    
    return render(request, "file_matches_results.html", {
            'match_paths' : match_paths,
            'known_context' : known_context,
        })

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
def difference_files(request):
    """Compare two files,  either known or uploaded,  and display the diffs."""

    def extension(filename): 
        """Return the file extension of `filename`."""
        return os.path.splitext(filename)[1]
    
    if request.method == "GET":
        return render(request, "difference_input.html")
    else:
        uploaded1, file1_orig, file1_path = handle_known_or_uploaded_file(
            request, "File1", "filemode1", "file_known1", "file_uploaded1")
        uploaded2, file2_orig, file2_path = handle_known_or_uploaded_file(
            request, "File2", "filemode2", "file_known2", "file_uploaded2")
        
        if rmap.is_mapping(file1_orig) and rmap.is_mapping(file2_orig) and \
            extension(file1_orig) == extension(file2_orig):
            diff_lines = pysh.lines("diff -b -c ${file1_path} ${file2_path}")
            diff_lines = format_mappingdiffs(diff_lines, file1_path, file2_path)
        elif file1_orig.endswith(".fits") and file2_orig.endswith(".fits"):
            diff_lines = pysh.lines("fitsdiff ${file1_path} ${file2_path}")
            diff_lines = format_fitsdiffs(diff_lines, file1_path, file2_path)
        elif re.match(GEIS_HEADER_RE, file1_orig) and \
            re.match(GEIS_HEADER_RE, file2_orig) and \
            extension(file1_orig) == extension(file2_orig):
            diff_lines = pysh.lines("diff -b -c ${file1_path} ${file2_path}")
        else:
            raise CrdsError("Files should be either CRDS mappings "
                            "of the same type or .fits files")
            
        if uploaded1: 
            remove_temporary(file1_path)
        if uploaded2:
            remove_temporary(file2_path)
            
        if not "".join(diff_lines).strip():
            diff_lines = ["no differences"]

        return render(request, "difference_results.html", 
                      {
                       "diff_lines" : diff_lines,
                       "file1" : file1_orig,
                       "file2" : file2_orig,
                       })

def format_fitsdiffs(lines, file1, file2):
    """Add some colorization to output `lines` from fitsdiff, replacing
    `file1` and `file2` with their basenames.
    """
    for i in range(len(lines)):
        line = clean_path(lines[i], file1)
        line = clean_path(line, file2)
        if "Primary HDU" in line or re.search("Extension \d+ HDU", line):
            line = "<h3>" + line + "</h3>"
        line = re.sub(r"([Kk]eyword)\s*([A-Za-z0-9_]*)",
                      r"\1 <span class='green'>\2</span>", line)
        lines[i] = line
    return lines

def format_mappingdiffs(lines, file1, file2):
    return [line.rstrip() for line in lines]

def clean_path(line, path):
    """Replace occurrences of `path` in `line` with a greyed version of
    the `path`s basename.
    """
    base = "<span class='grey'>" + os.path.basename(path) + "</span>"
    return line.replace(path, base)

# ===========================================================================

@error_trap("browse_input.html")
def browse_files(request):
    """View to return browse input form or process browse POSTs."""
    if request.method == "GET":
        return render(request, "browse_input.html")
    else:
        return browse_files_post(request)
    
def browse_files_post(request):
    """View fragment to process browse_files POSTs."""
    uploaded, original_name, browsed_file = handle_known_or_uploaded_file(
        request, "File", "filemode", "file_known", "file_uploaded")
    response = browse_files_post_guts(
        request, uploaded, original_name, browsed_file)
    if uploaded:
        remove_temporary(browsed_file)
    return response

# @profile
def browse_files_post_guts(request, uploaded, original_name, browsed_file):
    filename = os.path.basename(browsed_file)
    try:
        blob = models.FileBlob.load(filename)
        related_actions = models.AuditBlob.related_to(filename)
    except LookupError:
        blob = None
        related_actions = []
    
    if rmap.is_mapping(original_name):
        file_contents = browsify_mapping(original_name, browsed_file)
    else:
        file_contents = browsify_reference(original_name, browsed_file)
    
    return render(request, "browse_results.html", 
            { "uploaded" : uploaded,
             "fileblob" : blob,
             "observatory" : blob.observatory,
             "related_actions":related_actions,
             "file_contents":file_contents,
             "browsed_file":original_name})

def browsify_mapping(original_name, browsed_file):
    """Format a CRDS mapping file as colorized and cross-linked HTML."""
    contents = ""
    try:
        linegen = open(browsed_file).readlines()
    except OSError:
        return ["<h3 class='error'>File " 
                "<span class='grey'>%s<span> not found</h3>" % (original_name,)]

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
    # Tabs -->   4 spaces
    line = re.sub(r"\t", r"&nbsp;"*4, line)
    
    # HACK:  replace any sequence of whitespace with one "tab"
    line = re.sub(r"^\s+", r"&nbsp;"*4, line)
    
    # HACK:  add an extra level of indentation to any line ending with .fits',
    line = re.sub(r"('.*\.(fits|r\dh)',)$",
                  r"&nbsp;"*4 + r"\1",
                  line)

    # '2011-02-07 08:21:00' : 'v3b1842dj_drk.fits',
    if re.search(r"'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d'\s*:", line):
        line = "<p class='useafter'>" + line.strip() + "</p>\n"
    elif re.search(r"UseAfter", line):
        line = "<p class='match'>" + line.strip() + "</p>\n"        
    else:
        line = "<p>" + line.strip() + "</p>\n"

    # useafter date
    line = re.sub(r"('\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d')",
                  r"<span class='datetime'>\1</span>",
                  line)
    
    # Match, UseAfter  ({    --> <div> <span>
    line = re.sub(r".*header</span>.*",
                  r"<br/><div class='header'>" + line,
                  line)

    line = re.sub(r"(.*)(Match)(\(.*)",
                  r"<br/><div class='selector'>\1<span class='green'>\2</span>\3\n",
                  line)

    line = re.sub(r"(.*)(UseAfter)(\(.*)",
                  r"<div class='match'>\1<span class='green'>\2</span>\3",
                  line)
    
    # }  -->  } </div>
    line = re.sub(r"(.*\}.*)",  r"\1\n</div>\n", line)
    
    return line


def browsify_reference(original_name, browsed_file):
    """Format a CRDS reference file for HTML display.   Return HTML lines.
    """
    ref_blob = models.FileBlob.load(os.path.basename(browsed_file))
    default_context = models.get_default_context(ref_blob.observatory)
    mapping = rmap.get_cached_mapping(default_context)
    
    try:
        header = mapping.get_minimum_header(browsed_file)
    except IOError:
        return "<p class='error'>File unavailable.</p>"
    
    lines = ["<b>Header Parameters</b>",
             "<br/>",
             "<br/>",
             "<table border='1'>"]
    for key, value in sorted(header.items()):
        lines.append("<tr><td class='label'>%s</td><td>%s</td></tr>" % (key, value))
    lines.append("</table>")
    lines.append("<br/>")
    
    if browsed_file.endswith(".fits"):
        info = ["<b>FITS Info</b>", 
                "<pre>"]
        info += [x.rstrip() for x in finfo(browsed_file)[1][1:]]
        info.extend(["</pre>"])
    else:
        info = []
        
    lines.extend(info)
    
    return "\n".join(lines)


@capture_output
def finfo(filename):
    """Capture the output from the pyfits info() function."""
    pyfits.info(filename)

@error_trap("browse_known_file_error.html")
def browse_known_file(request, original_name):
    """special view which accepts browse file from a URL parameter,  required
    by cross links like /browse/some_file.rmap
    """
    browsed_file = get_known_filepath(original_name)
    uploaded = False
    return browse_files_post_guts(
        request, uploaded, original_name, browsed_file)

# ===========================================================================

@error_trap("reserve_name_input.html")
@login_required
def reserve_name(request):
    """reserve_name is a view to get officially registered CRDS filenames."""
    if request.method == "GET":
        return render(request, "reserve_name_input.html", {
        "observatories":models.OBSERVATORIES,
        "instruments":[""]+models.INSTRUMENTS,
        "filekinds":[""]+models.FILEKINDS,
        "extensions":models.EXTENSIONS,
        "observatory":"hst",
        "instrument":"",
        "filekind":"",
        "extension":".pmap",
        })
    else:
        return reserve_name_post(request)

def reserve_name_post(request):
    """View fragment handling reserve_name POST."""
    observatory = get_observatory(request)
    mode = validate_post(request, "filemode", ["file_known","by_parts"])

    if mode == "file_known":  # Use the user's name exactly if unknown.
        reserved_name = validate_post(request, "file_known", FILE_RE)
        known_files = models.FileIndexBlob.load(observatory).known_files
        audits = models.AuditBlob.filter(filename=reserved_name)
        assert (reserved_name not in known_files) and len(audits) == 0, \
            "Name " + repr(reserved_name) + " is already reserved in CRDS."
        models.AuditBlob.new(
            request.user, "reserve name", reserved_name, "none", "none",
            observatory=observatory)

    else:  # Make up the next name based on properties.
        instrument = validate_post(request, "instrument", models.INSTRUMENTS+[""])
        filekind = validate_post(request, "filekind", models.FILEKINDS+[""])
        extension = validate_post(request, "extension", models.EXTENSIONS)
        try:
            if extension == ".pmap":
                assert instrument == "", "Instrument must be blank for .pmap"
                assert filekind == "", "File kind must be blank for .pmap"
            elif extension == ".imap":
                assert filekind == "", "File kind must be blank for .imap"
            elif extension in [".rmap",".fits"]:
                assert instrument != "", "Instrument required for .rmap, .fits"
                assert filekind != "", "Filekind required for .rmap, .fits"
        except AssertionError, exc:
            raise CrdsError(str(exc))
        reserved_name = get_new_name(
            observatory, instrument, filekind, extension)

        models.AuditBlob.new(
            request.user, "reserve name", reserved_name, "none", "none",
            observatory=observatory, instrument=instrument, filekind=filekind)

    return render(request, "reserve_name_results.html",
                  {"reserved_name" : reserved_name})
    
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
    known_files = models.FileIndexBlob.load(observatory).known_files

    name = _get_new_name(observatory, instrument, filekind, extension)
    while name in known_files:
        name = _get_new_name(observatory, instrument, filekind, extension)
    
    return name

def auto_rename_file(observatory, upload_name, upload_path):
    extension = os.path.splitext(upload_name)[-1]
    instrument, filekind = utils.get_file_properties(
        observatory, upload_path)
    return get_new_name(observatory, instrument, filekind, extension)

# ===========================================================================

@error_trap("recent_activity_input.html")
# @login_required
def recent_activity(request):
    """recent_activity displays records from the AuditBlob database."""
    if request.method == "GET":
        return render(request, "recent_activity_input.html", {
            "actions":["*"]+models.AUDITED_ACTIONS,
            "observatories":["*"]+models.OBSERVATORIES,
            "instruments":["*"]+models.INSTRUMENTS,
            "filekinds":["*"]+models.FILEKINDS,
            "extensions":["*"]+models.EXTENSIONS,
            })
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
    user = validate_post(
        request, "user", r"[A-Za-z0-9_.\*]+")
    filters = {}
    for var in ["action", "observatory", "instrument", "filekind", "extension",
                "filename", "user"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_activities = models.AuditBlob.filter(**filters)[::-1]
    return render(request, "recent_activity_results.html", {
                "filters": filters,
                "filtered_activities" : filtered_activities,
            })

# ===========================================================================

@error_trap("browse_db_input.html")
# @login_required
def browse_db(request):
    """browse_db displays records from the FileBlob (subclasses) database."""
    if request.method == "GET":
        return render(request, "browse_db_input.html", {
            "observatories":["*"]+models.OBSERVATORIES,
            "instruments":["*"]+models.INSTRUMENTS,
            "filekinds":["*"]+models.FILEKINDS,
            "extensions":["*"]+models.EXTENSIONS,
            "status":["*"]+models.FILE_STATUS_MAP.keys(),
            "deliverer_user" : "*",
            })
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
    for var in ["observatory", "instrument", "filekind", "extension",
                "filename", "deliverer_user", "status"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_db = models.FileBlob.filter(**filters)
    return render(request, "browse_db_results.html", {
                "filters": filters,
                "filtered_db" : filtered_db,
                "observatory" : observatory,
            })

# ===========================================================================

@error_trap("create_contexts_input.html")
@login_required
def create_contexts(request):
    """create_contexts generates a new pmap and imaps given an existing pmap
    and set of new rmaps.   Note that the "new" rmaps must already be in CRDS.
    """
    if request.method == "GET":
        return render(request, "create_contexts_input.html")
    else:
        return create_contexts_post(request)

def create_contexts_post(request):
    """View fragment handling create_contexts POST case."""
    pmap = validate_post(request, "pipeline", is_pmap)
    updated_rmaps = validate_post(request, "rmaps", is_list_of_rmaps)
    description = validate_post(request, "description", DESCRIPTION_RE)

    new_contexts = do_create_contexts(pmap, updated_rmaps, description,
                                      request.user, request.user.email)

    return render(request, "create_contexts_results.html", {
                "new_contexts" : new_contexts,
            })
    
def do_create_contexts(pmap, updated_rmaps, description, user, email):
    """Create new contexts based on `pmap` which refer to `updated_rmaps`
    instead of the corresponding old rmaps.  Add the new contexts to the
    CRDS database and return a list of new context mapping names.
    """
    # Get the mapping from old imap to new rmap, basically the imaps that
    # must be updated onto the list of rmap updates to do.
    updates_by_instrument = newcontext.get_update_map(pmap, updated_rmaps)
    
    # For each imap being edited,  and the pipeline context,  reserve new
    # official names and return the dictionary { old_mapping : new_mapping }.
    new_name_map = generate_new_names(pmap, updates_by_instrument)
    
    # Actually generate the new mappings,  by first copying the old mappings 
    # and then substituting old names with their updated equivalents.
    new_contexts = newcontext.generate_new_contexts(
        pmap, updates_by_instrument, new_name_map)
 
    print "WARNING: skipping context certification for", repr(new_contexts)
#    for ctx in new_contexts:
#        new_loc = rmap.locate_mapping(ctx)  
#        do_certify_file(new_loc, new_loc, check_references=None)

    # Create delivery records for each of the new files
    observatory = rmap.get_cached_mapping(pmap).observatory
    for ctx in new_contexts:
        models.add_crds_file(
            observatory, ctx, rmap.locate_mapping(ctx),  user, email, 
            description, "new context",
            repr(pmap) + " : " + ",".join([repr(x) for x in updated_rmaps]))
        
    return sorted(new_contexts)

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
        "Program error.  New mapping " + repr(new_map) + " already exists."
    return new_map

# ===========================================================================

@error_trap("edit_rmap_input.html")
@login_required
def edit_rmap_browse(request):
    """browse_db displays records from the FileBlob (subclasses) database."""
    if request.method == "GET":    # display rmap filters
        return render(request, "edit_rmap_input.html", {
            "observatories":["*"]+models.OBSERVATORIES,
            "instruments":["*"]+models.INSTRUMENTS,
            "filekinds":["*"]+models.FILEKINDS,
            "extensions":["*"]+models.EXTENSIONS,
            "status":["*"]+models.FILE_STATUS_MAP.keys(),
            "deliverer_user" : "*",
            })
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
    for var in ["observatory", "instrument", "filekind", "extension",
                "filename", "deliverer_user", "status"]:
        value = locals()[var].strip()
        if value not in ["*",""]:
            filters[var] = value
    filtered_db = models.FileBlob.filter(**filters)
    return render(request, "edit_rmap_browse_results.html", {
                "filters": filters,
                "filtered_db" : filtered_db,
                "observatory" : observatory,
            })

@csrf_exempt
@login_required
@error_trap("base.html")
def edit_rmap(request, filename=None):
    """Handle all aspects of editing a particular rmap named `filename`."""
    if request.method == "GET":
        return edit_rmap_get(request, filename)  # display editor form
    else:
        return edit_rmap_post(request)   # execute edit actions

# @profile
def edit_rmap_get(request, filename):
    blob = models.FileBlob.load(filename)
    file_contents = browsify_edit_rmap(filename, blob.pathname)    
    return render(request, "edit_rmap_editor.html", 
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

def edit_rmap_post(request):
    """View fragment handling Rmap edit execution POST."""
    new_mappings = []
    actions = []

    expanded, actions = collect_action_tree(request)
    print pprint.pformat(actions)
    
    if not actions:
        raise CrdsError("No edit actions were found.   Aborted.")
    
    original_rmap = validate_post(request, "browsed_file", is_rmap)
    # description = validate_post(request, "description", DESCRIPTION_RE)
    description = "routine update"
    observatory = rmap.get_cached_mapping(original_rmap).observatory
    
    pmap = models.get_default_context(observatory)

    new_references = handle_file_submissions(expanded, observatory, request.user)
    
    new_rmap, new_loc = execute_edit_actions(original_rmap, expanded)
    
    models.add_crds_file(observatory, new_rmap, new_loc, 
            request.user, request.user.email, description, 
            creator_name = "crds",
            creation_method="edit rmap", audit_details=repr(actions))
    new_mappings.append(new_rmap)
    
    new_mappings += do_create_contexts(
        pmap, [new_rmap], description,  request.user, request.user.email)
    
    new_mappings = sorted(new_mappings)
    
    models.set_default_context(observatory, new_mappings[0], "crds-edit-rmap")

    return render(request, "edit_rmap_results.html", {
                "original_pipeline" : pmap,
                "new_references" : new_references,
                "new_mappings" : new_mappings,
                "actions" : actions,
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
            assert re.match("\d+", serial), "invalid action serial no " + repr(serial)
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
            actions.append((action, match_tuple, date, filename))
            
    return expanded, actions

def handle_file_submissions(actions, observatory, submitter):
    """Certify and submit all of the added files in `actions`.   Return
    a list of tuples of reference filenames: [(uploaded_name,  crds_name), ...]
    """
    for id in actions["add"]:
        uploaded_file = actions["add"][id]["filename"]
        try:
            do_certify_file(
                uploaded_file.name, uploaded_file.temporary_file_path())
        except Exception, exc:
            raise CrdsError("Reference " + repr(uploaded_file.name) + 
                            " failed certification: " + str(exc))
    new_references = []
    for id in actions["add"]:
        uploaded_file = actions["add"][id]["filename"]
        upload_name = uploaded_file.name
        description = actions["add"][id].get("description","undefined")
        creator_name = actions["add"][id].get("creator_name","undefined")
        change_level = actions["add"][id].get("change_level","SEVERE")
        new_name = submit_file_doit(
            observatory, uploaded_file, description,
            str(submitter), submitter.email, creator_name=creator_name,
            change_level=change_level, comparison_file=None,
            creation_method="edit rmap")
        new_references.append((upload_name, new_name))
        actions["add"][id]["filename"] = new_name
    return sorted(new_references)
        
def execute_edit_actions(original_rmap, actions):
    """Perform each of the `actions` on `original_rmap` to create a new
    rmap.   Return the (new_name, new_path) for the new rmap.   Don't alter
    `original_rmap`.
    """
    new_rmap = new_name(original_rmap)
    old_loc = rmap.locate_mapping(original_rmap)
    new_loc = rmap.locate_mapping(new_rmap)
    open(new_loc, "w").write(open(old_loc).read())   # copy old to new

    for act in sorted(actions):   # do adds before deletes
        for id in actions[act]:
            pars = actions[act][id]
            if act == "add":
                make_add_useafter_rmap( new_loc, new_loc, 
                    pars["match_tuple"], pars["date"], pars["filename"])
            elif act == "delete":
                make_delete_useafter_rmap(new_loc, new_loc, 
                    pars["match_tuple"], pars["date"], pars["filename"])
            else:
                raise RuntimeError("Unknown edit action " + repr(act))

    checksum.update_checksum(new_loc)
    
    do_certify_file(new_loc, new_loc)

    return new_rmap, new_loc
    
def make_add_useafter_rmap(old_location, new_location, match_tuple, 
                           useafter_date, useafter_file):
    """Add one new useafter date / file to the `match_tuple` case of
    `old_mapping`,  writing the modified rmap out to `new_location`.   If
    `match_tuple` doesn't exist in `old_mapping`,  add `match_tuple` as well.
    """
    # print "adding useafter", old_location, new_location, match_tuple, useafter_date, useafter_file
    new_mapping_file = cStringIO.StringIO()
    state = "find tuple"
    for line in open(old_location):
        if state == "find tuple":
            if "UseAfter" in line:
                #     ('HRC', 'CLEAR1S', 'F435W') : UseAfter({ 
                index = line.index(": UseAfter({")
                tuple_str = line[:index]
                line_tuple = compat.literal_eval(tuple_str.strip())
                if match_tuple == line_tuple:
                    state = "find useafter"
            elif line.strip() == "})":   # end of rmap
                # Never found match,  report an error.
                raise CrdsError("Couldn't find match tuple " + repr(match_tuple))
        elif state == "find useafter":
            if line.strip().endswith(".fits',"):
                # Handle a standard useafter clause
                # '2002-03-01 00:00:00' : 'oai16328j_cfl.fits', 
                line_date = re.search(DATETIME_RE_STR, line)
                if useafter_date < line_date.group(1):
                    # Found useafter insertion point inside existing match case
                    new_mapping_file.write("\t'%s' : '%s',\n" % \
                        (useafter_date, useafter_file))
                    state = "copy remainder"
                    modification = "Inserted useafter into existing match case."
            elif line.strip() == "}),":
                # Never found < useafter before next Match tuple
                new_mapping_file.write("\t'%s' : '%s',\n" % \
                                           (useafter_date, useafter_file))
                state = "copy remainder"
                modification = "Appended useafter to existing match case."
        new_mapping_file.write(line)
    assert state == "copy remainder", "no useafter insertion performed"
    new_mapping_file.seek(0)
    open(new_location, "w+").write(new_mapping_file.read())

def make_delete_useafter_rmap(old_location, new_location, match_tuple, 
                              useafter_date, useafter_file):
    """Add one new useafter date / file to the `match_tuple` case of
    `old_mapping`,  writing the modified rmap out to `new_location`.   If
    `match_tuple` doesn't exist in `old_mapping`,  add `match_tuple` as well.
    """
    new_mapping_file = cStringIO.StringIO()
    state = "find tuple"
    for line in open(old_location):
        if state == "find tuple":
            if "UseAfter" in line:
                #     ('HRC', 'CLEAR1S', 'F435W') : UseAfter({ 
                index = line.index(": UseAfter({")
                tuple_str = line[:index]
                line_tuple = compat.literal_eval(tuple_str.strip())
                if match_tuple == line_tuple:
                    state = "find useafter"
            elif line.strip() == "})":   # end of rmap
                # Never found match,  report an error.
                raise CrdsError("Couldn't find match tuple " + repr(match_tuple))
        elif state == "find useafter":
            if line.strip().endswith(".fits',"):
                # Handle a standard useafter clause
                # '2002-03-01 00:00:00' : 'oai16328j_cfl.fits', 
                line_date = re.search(DATETIME_RE_STR, line)
                if useafter_date == line_date.group(1):
                    filename = re.search("'.*' : '(.*)'", line).group(1)
                    if filename == useafter_file:
                        # Found useafter delete point.
                        state = "copy remainder"
                        continue
            elif line.strip() == "}),":
                raise CrdsError("Couldn't find useafter " + repr(useafter) + 
                                " in match tuple " + repr(match_tuple))
        new_mapping_file.write(line)
    assert state == "copy remainder", "no useafter insertion performed"
    new_mapping_file.seek(0)
    open(new_location, "w+").write(new_mapping_file.read())

# ============================================================================

@error_trap("delivery_options_input.html")
@login_required
def delivery_options(request):
    if request.method == "GET":
        return render(request, "delivery_options_input.html", {
            "observatories":models.OBSERVATORIES,
            "instruments":["*"]+models.INSTRUMENTS,
            "filekinds":["*"]+models.FILEKINDS,
            "deliverer_user": str(request.user),
            "observatory" : "*",
            "instrument" : "*",
            "filekind" : "*",
            "filename" : "*",
        })
    else:
        return delivery_options_post(request)

def delivery_options_post(request):
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

    return render(request, "delivery_options_results.html", {
                "filters": filters,
                "filtered_db" : filtered_db,
            })


@error_trap("delivery_process_results.html")
@login_required
def delivery_process(request):
    if request.method == "GET":
        raise CrdsError("Invalid delivery processing request.  POST only.")
    else:
        return delivery_process_post(request)

def delivery_process_post(request):    
    description = validate_post(request, "description", DESCRIPTION_RE)
    observatory = get_observatory(request)

    delivered_files = []
    for key in request.POST:
        if key.startswith("deliver_"):
            filename = str(key[len("deliver_"):])
            check_value(filename, is_deliverable_file, 
                "File " + repr(filename) + " is not deliverable.")
            delivered_files.append(filename)
    delivered_files.sort()
    
    catalog = deliver_file_catalog(observatory, delivered_files, "I")
    
    paths = deliver_file_get_paths(observatory, delivered_files)
                        
    try:
        catalog_link = deliver_make_links(observatory, catalog, paths)
    except Exception, exc:
        deliver_remove_fail(observatory, catalog, paths)
        raise CrdsError("Delivery failed: " + str(exc))

    deliver_file_set_catalog_links(observatory, delivered_files, catalog_link)
    
    models.AuditBlob.new(
        request.user, "deliver", os.path.basename(catalog), description, 
        repr([os.path.basename(catalog)] + delivered_files), observatory)        

    return render(request, "delivery_process_results.html", {
        "delivered_files" : delivered_files,
    })

def deliver_file_get_paths(observatory, files):
    """Adjust the database to account for this delivery.   Returns a list of
    absolute paths to `files`.
    """
    paths = []
    for file in files:
        blob = models.FileBlob.load(file)
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
    for file in files:
        blob = models.FileBlob.load(file)
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
        "Invalid delivery operation " + repr(operation)
    id = models.CounterBlob.next(observatory, "delivery_id")
    catalog = "_".join(["opus",str(id),operation.lower()])+".cat"
    catdir = os.environ.get("CRDS_SERVER_DATA", HERE) + "/catalogs"
    catpath = os.path.join(catdir, catalog)
    utils.ensure_dir_exists(catpath)
    cat = open(catpath, "w")
    for file in files:
        if rmap.is_mapping(file):
            kind = "M"
        else:
            kind = "R"
        cat.write(file + " " + operation + " " + kind + "\n")
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
    dirs = deliver_link_dirs(observatory)
    for site in dirs:
        utils.ensure_dir_exists(site)
        for file in paths + [catalog]:
            dest = site +"/" + os.path.basename(file)
            try:
                os.link(file, dest)
            except Exception:
                raise CrdsError("failed to link " + repr(dest))
    master_catalog_link = os.path.join(dirs[0], os.path.basename(catalog))
    return master_catalog_link

def deliver_remove_fail(observatory, catalog, paths):
    """Delete all the delivery links for a failed but possibly partially
    completed delivery.
    """
    dirs = deliver_link_dirs(observatory)
    for site in dirs + [catalog]:
        utils.ensure_dir_exists(site)
        for file in paths + [catalog]:
            dest = site +"/" + os.path.basename(file)
            try:
                os.remove(dest)
            except Exception:
                pass

def deliver_link_dirs(observatory):
    """Return a list of directories into which all the files in a delivery
    are hard linked.   Load list from file, .e.g. ${HERE}/deliver_dirs_hst.dat,
    where one directory is listed per line.
    """
    return [x.strip() for x in \
            open(HERE + "/deliver_dirs_" + observatory + ".dat") if x]

