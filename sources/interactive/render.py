"""This module contains functions related to rendering interactive views,  including
repeatable results and rendering a JPOLL result.
"""
import os.path
import json
import time

## ===========================================================================

# from django.http import HttpResponse
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import conditional_escape
import django.contrib.auth.models

# ===========================================================================
from crds.core import config, utils
from crds.core.exceptions import CrdsError

from . import models
from . import locks
from .common import srepr
from .. import config as sconfig

from ..jsonapi import views as jsonapi_views

# ===========================================================================

def usernames():
    """Return a list of all the usernames defined in the database."""
    try:
        return [str(x) for x in django.contrib.auth.models.User.objects.filter()]
    except Exception:  # provide a workable choice if it fails.
        return ["*"]


def crds_render(request, template, dict_=None, requires_pmaps=False):
    """Render an HttpReponse object.    Return HttpResponse."""
    html_str = crds_render_html(request=request, template=template, dict_=dict_, requires_pmaps=requires_pmaps)
    return HttpResponse(html_str)

def crds_render_html(request, template, dict_=None, requires_pmaps=False):
    """Render a template,  making same-named inputs from request available
    for echoing,  scrubbing file paths.   Return HTML.
    """
    rdict = get_rendering_dict(request, dict_=dict_, requires_pmaps=requires_pmaps)
    
    # Generate a first pass of the response HTML.
    loaded_template = loader.get_template(template)
    html_str = loaded_template.render(rdict, request)

    # Remove file paths and fix temporary names with client side names
    uploaded_pairs = rdict.get("uploaded_file_names", get_uploaded_filepaths(request))
    html_str = squash_file_paths(html_str, uploaded_pairs)
    return html_str

def get_rendering_dict(request, dict_=None, requires_pmaps=False):
    """Render a template,  making same-named inputs from request available
    for echoing.
    """
    if dict_ is None:
        dict_ = {}

    statuses = ["*"] + list(models.FILE_STATUS_MAP.keys())
    statuses.remove("uploaded")

    try:
        live_params = sconfig.ARCHIVE_PARAMETER_SERVICE_URL.split(":")[1][2:].split(".")[0]
    except Exception:
        live_params = "unknown"

    rdict = {   # standard template variables
        "observatory" : models.OBSERVATORY,

        "instrument" : "*",
        "instruments" : ["*"] + models.INSTRUMENTS,

        "filekind" : "*",
        "filekinds" : models.FILEKIND_TEXT_DESCR,

        "extensions" : [".pmap"] + ["*"] + list(sorted(set(models.EXTENSIONS)-set([".pmap"]))),
        "users": ["*"] + usernames(),

        "status" : "*",
        "statuses": statuses,

        "action" : "*",
        "actions" : ["*"] + models.AUDITED_ACTIONS,

        "filename" : "*",
        "deliverer_user" : "*",
        "current_path" : request.get_full_path(),

        "locked_instrument" : locks.get_locked_instrument(request),

        "username" : str(request.user),

        "auto_rename" : models.OBSERVATORY == "jwst",
        "server_usecase" :  sconfig.server_usecase.lower(),
        "mock_params" : sconfig.CRDS_MOCK_ARCHIVE_PARAMETERS,
        "live_params" : live_params,
    }

    # echo escaped inputs.
    for key, value in list(request.GET.items()):
        rdict[key] = conditional_escape(value)
    for key, value in list(request.POST.items()):
        rdict[key] = conditional_escape(value)
    for key, value in list(request.FILES.items()):
        rdict[key] = conditional_escape(value)

    if requires_pmaps:
        rdict.update(get_pmap_template_vars(dict_))

    # include view outputs
    if dict_ is not None:
        for key, value in list(dict_.items()):
            rdict[key] = value

    # Set up variables required to support django-json-rpc Javacsript
    jsonrpc_vars = jsonapi_views.get_jsonrpc_template_vars()
    for var in jsonrpc_vars:
        if var in rdict:
            raise CrdsError("Template variable collision on " + srepr(var))
        else:
            rdict[var] = jsonrpc_vars[var]

    # This is only for the purpose of showing/hiding logout, super user options.
    # Still,  do it last making it harder to trick.
    rdict["is_authenticated"] = request.user.is_authenticated
    rdict["is_superuser"] = request.user.is_superuser

    return rdict

def get_pmap_template_vars(dict_):
    """Get the template variables required for the pmap selection accordion."""
    pmap_edit = models.get_default_context(models.OBSERVATORY, "edit")
    pmap_edit_label = pmap_label(pmap_edit)
    pmap_operational = models.get_default_context(models.OBSERVATORY, "operational")
    pmap_operational_label = pmap_label(pmap_operational, pmap_edit)
    if dict_.get("pmap_initial_mode", "edit") == "edit":
        pmap_edit_checked = "checked"
        pmap_operational_checked = ""
    else:
        pmap_edit_checked = ""
        pmap_operational_checked = "checked"
    recent_pmaps = get_recent_pmaps(10, pmap_edit)
    pmap_labels = dict(recent_pmaps)
    pmap_labels[pmap_edit] = pmap_edit_label
    pmap_labels[pmap_operational] = pmap_operational_label
    pmap_labels_json = json.dumps(pmap_labels)
    return {
        "pmap_edit" : pmap_edit,
        "pmap_edit_checked" : pmap_edit_checked,
        "edit_context_label" : pmap_edit_label,
        "pmap_operational" : pmap_operational,
        "pmap_operational_checked" : pmap_operational_checked,
        "operational_context_label" : pmap_operational_label,
        "pmaps" : recent_pmaps,
        "pmap_labels_json" : pmap_labels_json,
        }

def squash_file_paths(response, uploaded_pairs):
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
    response = response.replace(config.get_crds_cfgpath(observatory) + "/", "")
    response = response.replace(config.get_crds_mappath(observatory) + "/", "")
    response = response.replace(config.get_crds_refpath(observatory) + "/", "")
    response = response.replace("/ifs/crds/"+sconfig.observatory+"/ops",sconfig.storage_path)
    response = response.replace(sconfig.storage_path + "/server_files/ingest", "")
    response = response.replace(sconfig.install_root, "")
    response = response.replace(sconfig.storage_path, "")
    response = response.replace("/ifs/crds/", "")
    response = response.replace("/crds/data1/server_local", "")
    response = response.replace("/crds/data1/", "")
    response = response.replace("/home/crds/", "")
    response = response.replace(config.get_crds_path(), "")
    return response

def get_uploaded_filepaths(request):
    """Return [ (original_name, temporary_path), ...] for uploaded files in `request`."""
    pairs = []
    for ufile in list(request.FILES.values()):
        filepath = str(ufile.temporary_file_path())
        original_name = str(ufile.name)
        config.check_filename(original_name)
        pairs.append((original_name, filepath))
    return pairs

def redirect_repeatable_result(request, template, rdict, jpoll_handler=None, requires_authentication=True):
    """Create a repeatable results model instance and redirect to it."""
    result = render_repeatable_result(request, template, rdict, requires_authentication=requires_authentication)
    return redirect_jpoll_result(result, jpoll_handler)

def render_repeatable_result(request, template, rdict, requires_authentication=True):
    """Create a repeatable results model instance and redirect to it."""
    rdict["user"] = request.user.username
    rdict["uploaded_file_names"] = get_uploaded_filepaths(request)
    rdict["requires_authentication"] = requires_authentication
    result = models.RepeatableResultBlob.new(template, rdict)
    return result

def redirect_jpoll_result(result, jpoll_handler):
    """Send the done message to `jpoll_handler` and redirect to the URL in `result`."""
    if jpoll_handler:
        jpoll_handler.done(0, result.abs_repeatable_url)
        time.sleep(10.0)  # wait 10 seconds to give jpoll done processing consistent behavior. 2x jpoll poll rate
    return HttpResponseRedirect(result.repeatable_url)   # secure


# ===========================================================================

@utils.cached
@models.crds_cached
def get_recent_pmaps(last_n, pmap_edit):
    """Return a list of option tuples for rendering HTML to choose recent
    pmaps (last 10). This defines what users will see for the context HTML
    drop-down menu.
    """
    files = models.FileBlob.objects.filter(name__endswith=".pmap")
    pmaps = []
    for file_ in files:
        file_.thaw()
        if file_.state == "uploaded":
            continue
        pmaps.append((file_.name, pmap_label(file_, pmap_edit)))
    return list(reversed(pmaps))[:last_n]

def pmap_label(blob, pmap_edit=None):
    """Return the text displayed to users selecting known pmaps."""
    if isinstance(blob, str):
        try:
            blob = models.FileBlob.load(blob)
        except LookupError:
            return "FILE LOOKUP FAILED -- invalid context"

    try:
        if pmap_edit is None:
            reversion = ""
        else:
            reversion = "*reversion*" if blob.name < pmap_edit else ""
    except Exception:
        reversion= "*reversion* check failed"

    available = "" if blob.available else "*unavailable*"
    bad = "*bad*" if blob.is_bad_file else ""
    #     blacklisted = "*blacklisted*" if blob.blacklisted else ""
    #     rejected = "*rejected*" if blob.rejected else ""
    return " ".join([blob.name, str(blob.delivery_date)[:16], available, bad, reversion])  #, blacklisted, rejected])


