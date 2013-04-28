from __future__ import division

import os
import os.path
import base64
import math
import re

from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import Error

from crds.server.interactive import models as imodels, versions, database
import crds.server.config as config
from crds import rmap, utils, log

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

def create_url(observatory, filename):
    if rmap.is_mapping(filename):
        url = config.CRDS_MAPPING_URL + filename
    else:
        url = config.CRDS_REFERENCE_URL + filename
    return url

def create_unchecked_url(observatory, filename):
    if rmap.is_mapping(filename):
        url = config.CRDS_UNCHECKED_MAPPING_URL + filename
    else:
        url = config.CRDS_UNCHECKED_REFERENCE_URL + filename
    return url

# ===========================================================================

FILE_RE = r"[A-Za-z0-9_]+(\.fits|\.pmap|\.imap|\.rmap|\.r\d[hd])"
LIST_GLOB_RE = r"[A-Za-z0-9_\.\*\+\(\)\-\[\]]+"

class UnknownContextError(Error):
    """The specified context is not a known CRDS mapping."""
    
class MismatchedContextError(Error):
    """The specified context's observatory doesn't match this server."""
    
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

class InvalidChunk(Error):
    """The data chunk number requested from a file was invalid."""
    
class BadFilenameError(Error):
    """A filename uses characters prohibited to prevent SQL injection."""

class BadListGlobError(Error):
    """A list search pattern uses characters prohibited to prevent SQL injection."""

class InvalidDatasetIds(Error):
    """Expected a list of dataset id strings but got something else."""

def check_known_file(file):
    """Check that `file` is known to CRDS, available, and/or not blacklisted."""
    if not re.match(FILE_RE, file):
        raise BadFilenameError("Invalid filename '%s'" % file)
    blob = imodels.file_exists(file)
    if not blob:
        return blob
    if not blob.available:
        raise UnavailableFile("File '%s' is not yet available."  % file)
    if blob.blacklisted:
        raise BlacklistedFile("File '%s' has been blacklisted and should no longer be used." % file)
    return blob

def check_context(context):
    if imodels.OBSERVATORY not in context:
            raise MismatchedContextError(("Requested context '%s' doesn't match the observatory '%s'" + 
                                         " supported by this server.   Switch servers or contexts.") %
                                         (context, imodels.OBSERVATORY))                
    blob = check_known_file(context)
    if blob is None or not rmap.is_mapping(context) or not context.endswith((".imap", ".pmap")):
        raise UnknownContextError("Context parameter '%s' is not a known CRDS .pmap or .imap file." % context)
    return blob

def check_mapping(mapping):
    blob = check_known_file(mapping)
    if not blob or not blob.type == "mapping":
        raise UnknownMappingError("Mapping parameter '%s' is not a known CRDS mapping file." % mapping)
    return blob
    
def check_reference(reference):
    blob = check_known_file(reference)
    if not blob or not blob.type == "reference":
        raise UnknownReferenceError("Reference parameter '%s' is not a known CRDS reference file." % reference)
    return blob

def check_header(header):
    if not isinstance(header, dict):
        raise InvalidHeaderError("Header parameter is not a dictionary.")
    for key, value in header.items():
        if not isinstance(key, (str, unicode)):
            raise InvalidHeaderError("Bad key in header... not a string.")
        if not isinstance(value, (str, unicode, int, float, bool)):
            raise InvalidHeaderError("Bad value in header... not a str, int, float, or bool.")

def check_observatory(obs):
    if obs != imodels.OBSERVATORY:
        raise InvalidObservatoryError("Mismatch between requested observatory " + 
                                      repr(obs) + " and server observatory " + 
                                      repr(imodels.OBSERVATORY))

def check_instrument(instr):
    if instr not in imodels.INSTRUMENTS:
        raise InvalidInstrumentError("Mismatch between requested instrument " + 
                                     repr(instr) + " and server instruments " + 
                                     repr(imodels.INSTRUMENTS))

def check_reftypes(reftypes):
    if not isinstance(reftypes, (list, tuple, type(None))):
        raise InvalidReftypesError("reftypes parameter should be a list of reftype/filekind strings or None.")
    if reftypes is not None:
        for reftype in reftypes:
            if not isinstance(reftype, (str, unicode)):
                raise InvalidReftypesError("Non-string reftype: " + repr(reftype))
            if reftype not in imodels.FILEKINDS:
                raise InvalidReftypesError("Reftype '%s' is not a known reference type." % imodels.FILEKINDS)

def check_dataset_ids(datasets):
    if not isinstance(datasets, list):
        raise InvalidDatasetIds("Expected list of dataset ids.")
    for dataset in datasets:
        if not isinstance(dataset, basestring):
            raise InvalidDatasetIds("Expected datasets to be id strings.")

# ===========================================================================

@jsonrpc_method('list_mappings(String, String)')
def list_mappings(request, observatory, glob_pattern):
    if observatory is None:
        observatory = config.observatory
    check_observatory(observatory)
    if not re.match(LIST_GLOB_RE, glob_pattern):
        raise BadListGlobError("Illegal glob pattern, / not permitted '%s'" % glob_pattern)
    return rmap.list_mappings(glob_pattern, observatory)

@jsonrpc_method('get_best_references(String, Object, Array)')
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

CRDS_JSONRPC_CHUNK_SIZE = 2**23    # 8M

@jsonrpc_method('get_file_chunk(String, String, Number)')
def get_file_chunk(request, context, filename, chunk):
    check_context(context)
    blob = check_known_file(filename)
    chunks = int(math.ceil(blob.size / CRDS_JSONRPC_CHUNK_SIZE))
    if int(chunk) != chunk:
        raise InvalidChunk("the specified chunk must be an integer index.")
    if not (0 <= chunk < chunks):
        raise InvalidChunk("the specified data chunk " + repr(chunk) + " is invalid.")
    with open(blob.pathname, "rb") as infile:
        infile.seek(chunk*CRDS_JSONRPC_CHUNK_SIZE)
        data = infile.read(CRDS_JSONRPC_CHUNK_SIZE)
    edata = base64.b64encode(data)
    return [chunks, edata]

@jsonrpc_method('get_url(String, String)')
def get_url(request, context, file):
    check_context(context)
    check_known_file(file)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, file)

@jsonrpc_method('get_file_info(String, String)')
def get_file_info(request, context, file):
    check_context(context)
    blob = check_known_file(file)
    return blob.info

@jsonrpc_method('get_dataset_headers(String, Array)')
def get_dataset_headers(request, context, dataset_ids):
    check_context(context)
    check_list_of_strings(dataset_ids)
    pmap = rmap.get_cached_mapping(context)
    return database.get_dataset_headers(dataset_ids=dataset_ids, observatory=pmap.observatory)

@jsonrpc_method('get_dataset_ids(String, String)')
def get_dataset_ids(request, context, instrument):
    check_context(context)
    check_instrument(instrument)
    pmap = rmap.get_cached_mapping(context)
    return database.get_dataset_ids(instrument, observatory=pmap.observatory)

# ===============================================================

#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_mapping_data(String, String)')
def get_mapping_data(request, context, mapping):
    check_context(context)
    check_mapping(mapping)
    where = rmap.locate_mapping(mapping)
    return open(where).read()

#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_mapping_url(String, String)')
def get_mapping_url(request, context, mapping):
    check_context(context)
    check_mapping(mapping)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, mapping)

#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_reference_data(String, String)')
def get_reference_data(request, context, reference):
    check_context(context)
    check_reference(reference)
    blob = imodels.FileBlob.load(reference)
    where = blob.pathname
    refdata = open(where).read()
    return base64.b64encode(refdata)

#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_reference_url(String, String)')
def get_reference_url(request, context, reference):
    check_context(context)
    check_reference(reference)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, reference)

# ===============================================================

@jsonrpc_method('file_exists(String)')
def file_exists(request, filename):
    return bool(imodels.file_exists(filename))

@jsonrpc_method('get_default_context(String)')
def get_default_context(request, observatory):
    if observatory is None:
        observatory = config.observatory
    observatory = observatory.lower()
    check_observatory(observatory)
    return imodels.get_default_context(observatory, state="operational")
    
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
