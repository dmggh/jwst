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
        submit_file_post(request)
        return render(request, 'submit_results.html')
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

@login_required
def certify_file(request):
    if request.method == "GET":
        return render(request, "certify_input.html")
    else:
        return certify_post(request)

def certify_post(request):
    if request.POST["filemode"] == "file_known":
        # certified_file is a basename,  but CRDS figures out where it is.
        original_name = request.POST["file_known"]
        certified_file = check_value(original_name, 
            "[A-Za-z0-9._]+", 
            "Filename must consist of letters, numbers, periods, "
            "or underscores.")
    else:
        ufile = get_uploaded_file(request, "file_uploaded")
        certified_file = ufile.temporary_file_path()
        original_name = ufile.name
            
    check_references = request.POST.get("check_references", False)
    shallow = "--shallow" if not check_references else ""
    mapping = "--mapping" if rmap.is_mapping(original_name) else ""

    certify_lines = pysh.lines(
        "python -m crds.certify ${certified_file} ${shallow} ${mapping}")
        
    status = "OK" if "0 errors \n" in certify_lines else "certify failed."    

    if request.POST["filemode"] == "file_uploaded":
        try:
            os.path.remove(certified_file)
        except:
            pass
            
    return render(request, "certify_results.html", 
            {"status":status, 
             "certify_lines":certify_lines,
             "certified_file":original_name})

# ===========================================================================

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
        print uses_files
        return render(request, "using_file_results.html", locals())

# ===========================================================================

def difference_files(request):
    if request.method == "GET":
        return render(request, "difference_files_inputs.html")
    else:
        return render(request, "difference_files_results.html")

