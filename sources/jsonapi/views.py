import os.path
import base64

from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import Error

import crds.server.interactive.versions as versions
import crds.server.interactive.models as imodels
import crds.server.config as config
from crds import rmap, utils

# =============================================================================

from jsonrpc._json import dumps
from jsonrpc.site import jsonrpc_site

def get_jsonrpc_template_vars():
    """Return the dictionary of template variables required to instantiate
    the django-json-rpc Javascript template code.   Presently this info is used
    by the browser side code of the "interactive" app to define jsonrpc
    proxy objects which can be called like local Javascript functions.
    """
    desc = jsonrpc_site.service_desc()
    return {
            'methods': desc['procs'],
            'method_names_str': dumps([m['name'] for m in desc['procs']])
    }

# ===========================================================================

def get_url(observatory, filename):
    if rmap.is_mapping(filename):
        url = config.CRDS_MAPPING_URL + filename
    else:
        url = config.CRDS_REFERENCE_URL + filename
    return url

# ===========================================================================

class UnknownContextError(Error):
    """The specified context is not a known CRDS mapping."""
    
class UnknownMappingError(Error):
    """The specified mapping parameter is not a known CRDS mapping file."""
    
class UnknownReferenceError(Error):
    """The specified reference parameter is not a known CRDS reference file."""
    
class InvalidHeaderError(Error):
    """The specified header parameter is not suitable."""

class InvalidObservatoryError(Error):
    """The specified observatory is not supported."""
    
class InvalidReftypesError(Error):
    """The specified reftypes is not a list of strings."""

class UnavailableFile(Error):
    """A known file is not available for download,  either because it is waiting
    for archiving or not yet generally available.
    """

class BlacklistedFile(Error):
    """A known file has been blacklisted and should no longer be used."""

def _standard_file_checks(file):
    blob = imodels.file_exists(file)
    if not blob:
        return blob
    if not blob.available:
        raise UnavailableFile("File '%s' is not yet available."  % file)
    if blob.blacklisted:
        raise BlacklistedFile("File '%s' has been blacklisted and should no longer be used.")
    return blob

def check_context(context):
    blob = _standard_file_checks(context)
    if not blob or not rmap.is_mapping(context):
        raise UnknownContextError("Context parameter '%s' is not a known CRDS mapping file." % context)

def check_mapping(mapping):
    blob = _standard_file_checks(mapping)
    if not blob or not blob.type == "mapping":
        raise UnknownMappingError("Mapping parameter '%s' is not a known CRDS mapping file." % mapping)
    
def check_reference(reference):
    blob = _standard_file_checks(reference)
    if not blob or not blob.type == "reference":
        raise UnknownReferenceError("Reference parameter '%s' is not a known CRDS reference file." % reference)
    
def check_header(header):
    if not isinstance(header, dict):
        raise InvalidHeaderError("Header parameter is not a dictionary.")
    for key, value in header.items():
        if not isinstance(key, (str, unicode)):
            raise InvalidHeaderError("Bad key in header... not a string.")
        if not isinstance(value, (str, unicode, int, float, bool)):
            raise InvalidHeaderError("Bad value in header... not a str, int, float, or bool.")

def check_observatory(obs):
    if obs not in ["hst","jwst"]:
        raise InvalidObservatoryError("Unknown observatory " + repr(obs))
    
def check_reftypes(reftypes):
    if not isinstance(reftypes, (list, type(None))):
        raise InvalidReftypesError("reftypes parameter should be a list of reftype/filekind strings or None.")
    if reftypes is not None:
        for reftype in reftypes:
            if not isinstance(reftype, (str, unicode)):
                raise InvalidReftypesError("Non-string reftype: " + repr(reftype))
            if reftype not in imodels.FILEKINDS:
                raise InvalidReftypesError("Reftype '%s' is not a known reference type." % imodels.FILEKINDS)

# ===========================================================================

@jsonrpc_method('list_mappings(String, String)')
def list_mappings(request, observatory, glob_pattern):
    if observatory is None:
        observatory = config.observatory
    check_observatory(observatory)
    assert glob_pattern.count("/") == 0, "Illegal glob pattern, / not permitted."
    return rmap.list_mappings(glob_pattern, observatory)

@jsonrpc_method('get_best_references(String, Object, Object)')
def get_best_references(request, context, header, reftypes):
    check_context(context)
    check_header(header)
    check_reftypes(reftypes)
    conditioned = utils.condition_header(header)
    return rmap.get_best_references(context, conditioned, include=reftypes)

@jsonrpc_method('get_mapping_names(String)')
def get_mapping_names(request, context):
    check_context(context)
    ctx = rmap.get_cached_mapping(context)
    return ctx.mapping_names()

@jsonrpc_method('get_reference_names(String)')
def get_reference_names(request, context):
    check_context(context)
    ctx = rmap.get_cached_mapping(context)
    return ctx.reference_names()

@jsonrpc_method('get_mapping_data(String, String)')
def get_mapping_data(request, context, mapping):
    check_context(context)
    check_mapping(mapping)
    where = rmap.locate_mapping(mapping)
    return open(where).read()

@jsonrpc_method('get_mapping_url(String, String)')
def get_mapping_url(request, context, mapping):
    check_context(context)
    check_mapping(mapping)
    ctx = rmap.get_cached_mapping(context)
    return get_url(ctx.observatory, mapping)

@jsonrpc_method('get_reference_data(String, String)')
def get_reference_data(request, context, reference):
    check_context(context)
    check_reference(reference)
    blob = imodels.FileBlob.load(reference)
    where = blob.pathname
    refdata = open(where).read()
    return base64.b64encode(refdata)

@jsonrpc_method('get_reference_url(String, String)')
def get_reference_url(request, context, reference):
    check_context(context)
    check_reference(reference)
    ctx = rmap.get_cached_mapping(context)
    return get_url(ctx.observatory, reference)

@jsonrpc_method('file_exists(String)')
def file_exists(request, filename):
    return bool(imodels.file_exists(filename))

@jsonrpc_method('get_default_context(String)')
def get_default_context(request, observatory):
    if observatory is None:
        observatory = config.observatory
    observatory = observatory.lower()
    check_observatory(observatory)
    return imodels.get_default_context(observatory)
    
@jsonrpc_method('get_server_info()')
def get_server_info(request):
    info = {
        "edit_context" : imodels.get_default_context(config.observatory),
        "operational_context" : imodels.get_default_context(
            config.observatory, state="operational"),
        "observatory" : config.observatory,
        "crds_version" : versions.get_version("crds")
        }
    return info
    
#@jsonrpc_method('jsonapi.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('jsonapi.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
