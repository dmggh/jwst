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
    if not re.match(pattern, value):
        raise IllegalValueError(msg)
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
            rdict[key] = safestring.mark_for_escaping(value)
    rdict["is_authenticated"] = request.user.is_authenticated()
    return render_to_response(template, RequestContext(request, rdict))

# ===========================================================================

def error_trap(template):
    """A 'decorator maker' returning a decorator which traps exceptions in POST
    views and re-issues the input `template` with an appropriate error message
    so the user can try again.
    
    So `template` is an HTML template which is initially rendered and submitted
    by the user.    When the form is processed,  if an error is encountered
    the POST view just raises an exception which is trapped by `trap` which
    re-issues the input form with an error message and the current values.
    """
    def decorator(func):
        def trap(request, *args, **keys):
            try:
                return func(request, *args, **keys)
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
        return reference[len("NOT FOUND "):][1:-1]
    
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
        submit_vars = submit_file_post(request)
        return render(request, 'submit_results.html', submit_vars)
    else: # GET
        return render(request, 'submit_input.html')

def submit_file_post(request):
    """Handle the POST case of submit_file,   returning dict of template vars.
    """
    status = "succeeded."
    certification_lines = []
    
    try:
        ufile = request.FILES['filename']
    except KeyError:
        raise MissingInputError("Specify a file to upload and submit.")
    
    legal_exts = (".fits",".pmap",".imap",".rmap")
    if not ufile.name.endswith(legal_exts):
        raise FieldError("File extension for " + repr(str(ufile.name)) + \
                 " not one of " + ", ".join(legal_exts))

    # determine where to store
    permanent_location = create_crds_path(ufile.temporary_file_path(), ufile.name)
    baseperm = os.path.basename(str(permanent_location))
    if os.path.exists(permanent_location) or models.FileBlob.exists(baseperm):
        raise FieldError("File " + repr(baseperm) + " already exists.")
    
    upload_location = ufile.temporary_file_path()
    try:
        if rmap.is_mapping(ufile.name):
            certify.certify_mapping(upload_location, check_references=False)
        else:
            certify.certify_fits(upload_location)
    except Exception, exc:
        certification_lines = [repr(exc)]
        status = "failed: certification error(s)"
        return locals()
           
    upload_file(ufile, permanent_location)

    create_blob(request, ufile.name, permanent_location)
    
    return locals()

def upload_file(ufile, where):
    """Copy the Django UploadedFile to it's permanent location.
    """
    utils.ensure_dir_exists(where)
    destination = open(where, 'wb+')
    for chunk in ufile.chunks():
        destination.write(chunk)
    destination.close()
    
def create_crds_path(temp_path, upload_name):
    """Given the temporary upload path and filename,  determine where the file 
    should be stored on a permanent basis,  assigning it both an appropriate 
    path and (possibly) a unique name.
    """
    return upload_name   # XXX Fake for now

def create_blob(request, upload_name, permanent_location):
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
    blob.deliverer_name = request.POST["deliverer_name"]
    blob.deliverer_email = request.POST["deliverer_email"]
    blob.modifier_name = request.POST["modifier_name"]
    blob.description = request.POST["description"]
    blob.save()

# ===========================================================================
@login_required
def blacklist_file(request):
    if request.method == "GET":
        return render(request, "blacklist_file_inputs.html")
    else:
        return render(request, "blacklist_file_results.html")

# ===========================================================================

@login_required
def certify_file(request):
    if request.method == "GET":
        return render(request, "certify_input.html")
    else:
        certified_file = check_value(request.POST["certified_file"], 
            "[A-Za-z0-9._]+", 
            "Filename must consist of letters, numbers, periods, "
            "or underscores.")
        check_references = request.POST.get("check_references", False)
        shallow = "--shallow" if not check_references else ""
        certify_lines = pysh.lines(
                "python -m crds.certify ${certified_file} ${shallow}" )
        status = "OK" if "0 errors \n" in certify_lines else "certify failed."
        certify_lines = [line for line in certify_lines if \
            line.startswith("ERROR") or line.startswith("WARNING")]
        return render(request, "certify_results.html", locals())

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
        return render(request, "using_file_results.html", locals())

# ===========================================================================

def difference_files(request):
    if request.method == "GET":
        return render(request, "difference_files_inputs.html")
    else:
        return render(request, "difference_files_results.html")

