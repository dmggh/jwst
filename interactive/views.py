# Create your views here.
import os.path
import re
import hashlib
import xml.sax.saxutils as saxutils

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import django.utils.safestring as safestring

import django.contrib.auth
from django.contrib.auth.decorators import login_required

from crds import (rmap, utils, certify, timestamp, uses)

import crds.server.config as config
import crds.server.interactive.models as models
import crds.pysh as pysh

from crds.server.interactive.models import FieldError, MissingInputError

# ===========================================================================

def _get_imap(request):
    """Convert a request into an instrument context name."""
    post = request.POST
    try:
        mode = post["context-mode"]
        print mode
    except KeyError:
        return post["instrument-context"]
    else:
        return post["context-user"] if mode == "user" else post["context-default"]

def _get_ctx(request):
    """Convert a request into an instrument context object."""
    imap = _get_imap(request)
    ctx = rmap.get_cached_mapping(imap)
    assert isinstance(ctx, rmap.InstrumentContext), "Invalid instrument context " + repr(imap)
    return ctx

def check_value(value, pattern, msg):
    value = str(value)
    if not re.match(pattern, value):
        raise FieldError(msg)
    return value

def render(request, template, dict_=None):
    """Top level index page."""
    rdict = {}
    for key, value in request.GET.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.POST.items():
        rdict[key] = safestring.mark_for_escaping(value)
    for key, value in request.FILES.items():
        rdict[key] = safestring.mark_for_escaping(value)
    if dict_ is not None:
        for key, value in dict_.items():
            rdict[key] = value
    rdict["is_authenticated"] = request.user.is_authenticated()
    return render_to_response(template, RequestContext(request, rdict))

def handle_known_or_uploaded_file(request, name, modevar, knownvar, uploadvar):
    """Process file variables for a file which is either known to CRDS
    and simply named,  or which is uploaded by the user.
    
    Return (uploaded_flag, name_on_users_system,  temporary_file_path)
    """
    if request.POST[modevar] == knownvar:
        # certified_file is a basename,  but CRDS figures out where it is.
        original_name = check_value(request.POST[knownvar],
            "[A-Za-z0-9._]+", 
            "Filename " + name + " must consist of letters, numbers, periods, "
            "or underscores.")
        if rmap.is_mapping(original_name):
            try:
                filepath = models.MappingBlob.load(original_name).pathname
            except LookupError:
                try:
                    loc = utils.get_locator_module("hst")
                    filepath = loc.locate_server_mapping(original_name)
                except Exception, exc:
                    raise FieldError(
                        "Couldn't find mapping " + original_name)
        elif original_name.endswith(".fits"):
            try:
                filepath = models.ReferenceBlob.load(original_name).pathname
            except LookupError:
                try:
                    loc = utils.get_locator_module("hst")
                    filepath = loc.locate_server_reference(original_name)
                except Exception, exc:
                    print repr(exc) + " : " + str(exc)
                    raise FieldError(
                        "Couldn't find reference file " + original_name)
        else:
            raise FieldError(
                name + " should have .pmap, .imap, .rmap, or .fits extension.")
        uploaded = False
    else:
        ufile = get_uploaded_file(request, uploadvar)
        filepath = ufile.temporary_file_path()
        original_name = ufile.name
        uploaded = True
    return uploaded, original_name, filepath

def remove_temporary(filepath):
    """Attempt to remove `filepath`.  Ignore errors."""
    try:
        os.remove(filepath)
    except OSError:
        pass
    

# ===========================================================================

class CrdsError(Exception):
    """Something bad but understood happened in CRDS processing."""

def error_trap(template):
    """error_trap() is a 'decorator maker' which returns a decorator which traps 
    exceptions in views and re-issues the input `template` with an 
    appropriate error message so the user can try again.
    """
    def decorator(func):
        def trap(request, *args, **keys):
            try:
                return func(request, *args, **keys)
            except CrdsError, exc:
                return render(request, template, {"error_message" : str(exc)})
            except FieldError, exc:
                return render(request, template, {"error_message" : str(exc)})
        trap.func_name = func.func_name
        return trap
    return decorator

# ===========================================================================

def index(request):
    return render(request, "index.html", {})

# ===========================================================================

def logout(request):
    django.contrib.auth.logout(request)
    return render(request, "logout.html", {})
        
# ===========================================================================

def bestrefs_index(request):
    return render(request, "bestrefs_index.html", {})

def bestrefs_input(request):
    """Prompt for best ref inputs."""
    ctx = _get_ctx(request)
    required_keys = list(ctx.get_required_parkeys())
    parkey_map_items = sorted(ctx.get_parkey_map().items())
    return render(request, "bestrefs_input.html", locals())

def bestref_link(ctx, reference):
    """Return an appropriate anchor tag for `reference`."""
    if not reference.startswith("NOT FOUND"):
        try:
            url = ctx.locate.reference_url(config.CRDS_REFERENCE_URL, reference)
            return '<a href="%s">%s</a>' % (url, reference)
        except:
            return reference
    else:
        return reference[len("NOT FOUND "):]
    
def bestrefs_compute(request):
    """Compute and display best reference results."""
    ctx = _get_ctx(request)
    header = {}
    needed_keys = list(ctx.get_required_parkeys())
    needed_keys.remove("REFTYPE")
    for key in needed_keys:
        if key.startswith("*"):
            key = key[1:]
        header[str(key)] = str(request.POST[key])
    bestrefs = ctx.get_best_references(header)
    header_items = sorted(header.items())
    bestrefs_items = [ (key.upper(), bestref_link(ctx, val)) for (key, val) in sorted(bestrefs.items())]
    return render(request, "bestrefs_results.html", locals())

# ============================================================================

@error_trap("submit_input.html")
@login_required
def submit_file(request):
    """Handle file submission."""
    if request.method == 'POST':
        baseperm = submit_file_post(request)
        return render(request, 'submit_results.html', {"baseperm":baseperm})
    else: # GET
        return render(request, 'submit_input.html')
    
def submit_file_post(request):
    """Handle the POST case of submit_file,   returning dict of template vars.
    """
    observatory = check_value(request.POST["observatory"], 
            "hst|jwst", "Invalid value for observatory.")
    
    # Get the UploadedFile object
    ufile = get_uploaded_file(request, "filename")

    # Determine the temporary and permanent file paths, keeping file temporary.
    upload_location, permanent_location = handle_crds_locations(ufile)

    # Check the file,  leaving no server state if it fails.  Give error results.
    do_certify_file(ufile.name, upload_location)
    
    # Copy the temporary file to its permanent location.
    upload_file(ufile, permanent_location)

    # Make a database record of this delivery.
    create_delivery_blob(request, observatory, ufile.name, permanent_location)
    
    return os.path.basename(permanent_location)
    
def do_certify_file(basename, certifypath, check_references=False):
    try:
        if rmap.is_mapping(basename):
            certify.certify_mapping(
                certifypath, check_references=check_references)
        else:
            certify.certify_fits(certifypath)
    except Exception, exc:
        raise CrdsError(repr(exc))

def get_uploaded_file(
    request, formvar, legal_exts=(".fits", ".pmap", ".imap", ".rmap")):
    """Return the DJango UploadedFile associated with `request` and `formavar`,
    raising an exception if it's original name does not end with one of
    `legal_exts` file extensions.
    """
    try:
        ufile = request.FILES[formvar]
    except KeyError:
        raise MissingInputError("Specify a file to upload.")
    if not ufile.name.endswith(legal_exts):
        raise FieldError("File extension for " + repr(str(ufile.name)) + \
                 " not one of: " + ", ".join(legal_exts))
    return ufile

def handle_crds_locations(uploaded_file, clobber=False):
    """Given a Django `uploaded_file` object, determine where it should reside
    permanently.  If `clobber` is False ensure that the permanent filename does
    not already exist on the file system or in the database,  raising an
    exception if it does exist.   Return both the temporary upload path and
    the location the file should reside permanently.
    """
    # determine where to store
    upload_location = uploaded_file.temporary_file_path()
    permanent_location = create_crds_name(upload_location, uploaded_file.name)
    baseperm = os.path.basename(str(permanent_location))
    if not clobber and \
       (os.path.exists(permanent_location) or models.FileBlob.exists(baseperm)):
        raise FieldError("File " + repr(baseperm) + " already exists.")    
    return upload_location, permanent_location

def upload_file(ufile, where):
    """Copy the Django UploadedFile to it's permanent location."""
    utils.ensure_dir_exists(where)
    destination = open(where, 'wb+')
    for chunk in ufile.chunks():
        destination.write(chunk)
    destination.close()
    
def create_crds_name(upload_location, upload_name):
    """Determine where a file should be stored on a permanent basis,  assigning
    it both an appropriate path and (possibly) a unique name.  `upload_location`
    is the file's temporary upload path.  upload_name is how the file was named
    on the user's computer,  not the temporary file.
    """
    return upload_name   # XXX Fake for now

def create_delivery_blob(request, observatory, upload_name, permanent_location):
    """Make a record of this delivery in the CRDS database.
    """
    if upload_name.endswith(".fits"):
        blob = models.ReferenceBlob()
    elif upload_name.endswith((".pmap", ".imap", ".rmap")):
        blob = models.MappingBlob()
    blob.uploaded_as = upload_name
    blob.pathname = permanent_location
    blob.delivery_date = timestamp.now()
    blob.sha1sum = blob.checksum()
    blob.deliverer_user = request.user
    blob.deliverer_email = request.user.email
    blob.modifier_name = request.POST["modifier_name"]
    blob.description = request.POST["description"]
    instrument, filekind, serial = utils.get_file_properties(
            observatory, permanent_location)
    blob.observatory = observatory
    blob.instrument = instrument
    blob.filekind= filekind
    blob.serial = serial
    blob.save()

# ===========================================================================

@error_trap("blacklist_input.html")
@login_required
def blacklist_file(request):
    if request.method == "GET":
        return render(request, "blacklist_input.html")
    else:
        return blacklist_file_post(request)

def blacklist_file_post(request):
    observatory = check_value(request.POST["observatory"], 
            "hst|jwst", "Invalid value for observatory.")
    blacklisted = check_value(request.POST["file_known"],
            "[A-Za-z0-9._]+", 
            "Filename must consist of letters, numbers, periods, "
            "or underscores.")
    badflag = check_value(request.POST["badflag"], "bad|ok",
            "badflag must be either 'bad' or 'ok'")
    why = request.POST["why"]
    try: 
        if rmap.is_mapping(blacklisted):
            blob = models.MappingBlob.load(blacklisted)
        elif blacklisted.endswith(".fits"):
            blob = models.ReferenceBlob.load(blacklisted)
        else:
            raise FieldError("Bad file extension for file " + repr(blacklisted))
    except LookupError:
        raise FieldError("Unknown file " + repr(blacklisted))
    blob.blacklisted = badflag == "bad"
    models.AuditBlob.create_record(request.user, "blacklist", blacklisted, why, 
                                   "marked as" + badflag)
    blob.save()
    return render(request, "blacklist_results.html")
    
        
# ===========================================================================

@error_trap("certify_input.html")
@login_required
def certify_file(request):
    """Check for the existence and validity
    """
    if request.method == "GET":
        return render(request, "certify_input.html")
    else:
        return certify_post(request)

def certify_post(request):

    uploaded, original_name, certified_file = handle_known_or_uploaded_file(
        request, "File", "filemode", "file_known", "file_uploaded")
            
    check_references = request.POST.get("check_references", False)
    shallow = "--shallow" if not check_references else ""
    mapping = "--mapping" if rmap.is_mapping(original_name) else ""

    certify_lines = ["<h3>CRDS Certify</h3>"]
    certify_lines += pysh.lines(
        "python -m crds.certify ${certified_file} ${shallow} ${mapping}")
    status = "OK" if "0 errors \n" in certify_lines else "Failed."    
    
    if not rmap.is_mapping(original_name):
        fitscheck_lines = pysh.lines("fitscheck ${certified_file}")
        certify_lines += ["<h3>Fitscheck</h3>"] + fitscheck_lines
        status = "OK" if (status=="OK") and \
            "0 errors \n" in fitscheck_lines else "Failed."

    if uploaded:
        remove_temporary(certified_file)

    return render(request, "certify_results.html", 
            {"status":status, 
             "certify_lines":certify_lines,
             "certified_file":original_name})

# ===========================================================================

@error_trap("using_file_inputs.html")
def using_file(request):
    if request.method == "GET":
        return render(request, "using_file_inputs.html")
    else:
        observatory = check_value(request.POST["observatory"], 
            "hst|jwst", "Invalid value for observatory.")
        referred_file = check_value(request.POST["referred_file"], 
            "[A-Za-z0-9._]+", 
            "Filename must consist of letters, numbers, periods, "
            "or underscores.")
        uses_files = uses.uses([referred_file], observatory)
        if not "".join(uses_files).strip():
            uses_files = ["no files"]
        return render(request, "using_file_results.html", locals())

# ===========================================================================

def extension(filename): 
    """Return the file extension of `filename`."""
    return os.path.splitext(filename)[1]

@error_trap("difference_input.html")
def difference_files(request):
    """Compare two files,  either known or uploaded,  and display the diffs."""
    if request.method == "GET":
        return render(request, "difference_input.html")
    else:
        uploaded1, file1_orig, file1_path = handle_known_or_uploaded_file(
            request, "File1", "filemode1", "file_known1", "file_uploaded1")
        uploaded2, file2_orig, file2_path = handle_known_or_uploaded_file(
            request, "File2", "filemode2", "file_known2", "file_uploaded2")
        
        if rmap.is_mapping(file1_orig) and rmap.is_mapping(file2_orig) and \
            extension(file1_orig) == extension(file2_orig):
            diff_lines = pysh.lines("diff ${file1_path} ${file2_path}")
            diff_lines = format_mappingdiffs(diff_lines, file1_path, file2_path)
        elif file1_orig.endswith(".fits") and file2_orig.endswith(".fits"):
            diff_lines = pysh.lines("fitsdiff ${file1_path} ${file2_path}")
            diff_lines = format_fitsdiffs(diff_lines, file1_path, file2_path)
        else:
            raise CrdsError("Files should be either CRDS mappings of the same type or .fits files")
        
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
        lines[i] = clean_path(lines[i], file1)
        lines[i] = clean_path(lines[i], file2)
        if "Primary HDU" in lines[i] or re.search("Extension \d+ HDU", lines[i]):
            lines[i] = "<h3>" + lines[i] + "</h3>"
        lines[i] = re.sub(r"([Kk]eyword)\s*([A-Za-z0-9_]*)",
                          r"\1 <span class='green'>\2</span>",
                          lines[i])
    return lines

def format_mappingdiffs(lines, file1, file2):
    return lines

def clean_path(line, path):
    """Replace occurrences of `path` in `line` with a greyed version of
    the `path`s basename.
    """
    base = "<span class='grey'>" + os.path.basename(path) + "</span>"
    return line.replace(path, base)

# ===========================================================================

@error_trap("browse_input.html")
def browse_files(request):
    if request.method == "GET":
        return render(request, "browse_input.html")
    else:
        return render(request, "browse_results.html")

