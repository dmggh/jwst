# Create your views here.
import os.path
import hashlib
import xml.sax.saxutils as saxutils

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from crds import (rmap, utils, certify, timestamp)

import crds.server.config as config
import crds.server.interactive.models as models

def _get_imap(request):
    """Convert a request into an instrument context name."""
    post = dict([(str(key), str(val)) for (key,val) in request.POST.items()])
    print post
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

def render(request, template, dict_=None):
    """Top level index page."""
    dict_ = {} if dict_ is None else dict_
    return render_to_response(template, RequestContext(request, dict_))

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
    elif blob.endswith((".pmap", ".imap", ".rmap")):
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
    
def submit_failed(request, message, permanent_location=None):
    """Handle cleanup and results formatting when a submission fails.
    """
    return render(request, "submit_results.html", 
        {"status" : "Failed: " + message})
    

def submit_file(request):
    """Handle file submission."""
    if request.method == 'POST':
        ufile = request.FILES['filename']
        legal_exts = (".fits",".pmap",".imap",".rmap")
        if not ufile.name.endswith(legal_exts):
            return submit_failed(request, 
                "file extension for " + repr(str(ufile.name)) + 
                " not one of " + repr(legal_exts))

        # determine where to store
        permanent_location = create_crds_path(
                ufile.temporary_file_path, ufile.name)
        baseperm = os.path.basename(permanent_location)
        if os.path.exists(permanent_location) or \
            models.FileBlob.exists(baseperm):
            return submit_failed(
                request, "file " + repr(baseperm) + " already exists.",
                permanent_location)
        upload_file(ufile, permanent_location)
        try:
            certify.certify(permanent_location)
        except Exception, exc:
            return submit_failed(
                request, 
                "certification error(s): " + repr(exc) + " " + str(exc),
                permanent_location)        
        create_blob(request, ufile.name, permanent_location)
        
        return render(request, 'submit_results.html',
                      {"status" : "Succeeded."})
    else: # GET
        return render(request, 'submit_input.html')

