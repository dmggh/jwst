from __future__ import division

import os
import os.path
import base64
import math
import re

from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import Error

from crds.server.interactive import models as imodels, versions, database
import crds.server.config as config    # server parameters
from crds import rmap, utils, log, timestamp
import crds.config                     # generic client/server

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
    if crds.config.is_mapping(filename):
        url = config.CRDS_MAPPING_URL + filename
    else:
        url = config.CRDS_REFERENCE_URL + filename
    return url

def create_unchecked_url(observatory, filename):
    if crds.config.is_mapping(filename):
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
    
class InvalidInstrumentError(Error):
    """The specified instrument is not supported."""
    
class InvalidReftypesError(Error):
    """The specified reftypes is not a list of strings."""

class UnknownFile(Error):
    """There's no record of a file in the CRDS database."""

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

class InvalidDateFormat(Error):
    """Received a date with an invalid format."""

class InvalidDateBasedContext(Error):
    """Received a data based context with an invalid format."""

def check_known_file(file):
    """Check that `file` is known to CRDS, available, and/or not blacklisted."""
    if not re.match(FILE_RE, file):
        raise BadFilenameError("Invalid filename '%s'" % file)
    blob = imodels.file_exists(file)
    if not blob:
        raise UnknownFile("File '%s' is not known to CRDS."  % file)
    if not blob.available:
        raise UnavailableFile("File '%s' is not yet available."  % file)
    if blob.blacklisted:
        raise BlacklistedFile("File '%s' has been blacklisted and should no longer be used." % file)
    return blob

def check_context(context, observatory=None):
    """Ensure that `context` is either a known literal context or a valid date based context specification.
    Return the name of the corresponding literal context.
    """
    if observatory is None:    # json_rpc wrapper passes None when unspecified, not unspecified
        observatory = config.observatory
    if not crds.config.is_mapping(context):  # this is for speed, to short circuit most checking
        if not crds.config.is_mapping_spec(context):  # this is for more clarity
            raise UnknownContextError("Context parameter '%s' is not a .pmap, .imap, or .rmap file or a valid date based context specification." % context)
        context = _check_date_based_context(context, observatory)
    if config.observatory not in context:
            raise MismatchedContextError(("Requested context '%s' doesn't match the observatory '%s'" + 
                                         " supported by this server.   Switch servers or contexts.") %
                                         (context, config.observatory))
    blob = check_known_file(context)
    if not crds.config.is_mapping(context):
        raise UnknownContextError("Context parameter '%s' is not a known CRDS .pmap, .imap, or .rmap file." % context)
    return context

def _check_date_based_context(context, observatory):
    """Check `context` to see if it is a date based context specification.   If it is,
    translate it into a literal .pmap, .imap, or .rmap name.   Otherwise return `context` unchanged.
    """
    instrument = filekind = None
    m = crds.config.CONTEXT_DATETIME_RE.match(context)
    if m:
        context = _pmap_from_date(context, observatory)
    else:        
        m = crds.config.CONTEXT_RE.match(context)
        if m:
            obs_instr_kind = m.group("context")[:-1]
            parts = obs_instr_kind.split("-")
            assert 1 <= len(parts) <= 3, "Invalid date based context [observatory-[instrument-[reftype]]] specification."
            observatory = check_observatory(parts[0])
            instrument = parts[1] if len(parts) > 1 else None
            filekind = parts[2] if len(parts) > 2 else None
            datestr = m.group("date")
            context = _pmap_from_date(datestr, observatory)
    if instrument:
        pmap = rmap.get_cached_mapping(context)
        try:
            instrument = check_instrument(instrument)
        except Exception:
            raise InvalidDateBasedContext("Bad instrument '%s' in CRDS date based context specification." % instrument)
        imap = pmap.get_imap(instrument)
        context = imap.name
        if filekind:
            try:
                filekind = check_reftype(filekind)
            except Exception:
                raise InvalidDateBasedContext("Bad reftype '%s' in  CRDS date based context specification." % filekind)
            context = imap.get_rmap(filekind).name
    return context

def _pmap_from_date(date, observatory):
    """Using `date` and `observatory` lookup the operational context from that period."""
    dt = check_date(date)
    try:
        return imodels.get_context_by_date(date=date, observatory=observatory)
    except Exception, exc:
        raise UnknownContextError("No CRDS context found corresponding to (prior to) date '%s'" % date)

def check_date(date):
    """Verify the format of simple context datetime string `date` and return a datetime.datetime object."""
    try:
        if not crds.config.CONTEXT_DATETIME_RE.match(date):
            raise Exception("Forced date error")
        return timestamp.parse_date(date)
    except Exception:
        raise InvalidDateBasedContext("Invalid context date/time format '%s' should be YYYY-MM-DDTHH:MM:SS" % date)

def check_mapping(mapping):
    blob = check_known_file(mapping)
    if blob.type != "mapping":
        raise UnknownMappingError("Mapping parameter '%s' is not a known CRDS mapping file." % mapping)
    return blob
    
def check_reference(reference):
    blob = check_known_file(reference)
    if blob.type != "reference":
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
    obs = obs.lower()
    if obs != imodels.OBSERVATORY:
        raise InvalidObservatoryError("Mismatch between requested observatory " + 
                                      repr(obs) + " and server observatory " + 
                                      repr(imodels.OBSERVATORY))
    return obs

def check_instrument(instr):
    instr = instr.lower()
    if instr not in imodels.INSTRUMENTS:
        raise InvalidInstrumentError("Mismatch between requested instrument " + 
                                     repr(instr) + " and server instruments " + 
                                     repr(imodels.INSTRUMENTS))
    return instr

def check_reftypes(reftypes):
    if not isinstance(reftypes, (list, tuple, type(None))):
        raise InvalidReftypesError("reftypes parameter should be a list of reftype/filekind strings or None.")
    if reftypes is not None:
        for reftype in reftypes:
            check_reftype(reftype)

def check_reftype(reftype):
    reftype = reftype.lower()
    if not isinstance(reftype, (str, unicode)):
        raise InvalidReftypesError("Non-string reftype: " + repr(reftype))
    if reftype not in imodels.FILEKINDS:
        raise InvalidReftypesError("Reftype '%s' is not a known reference type." % imodels.FILEKINDS)
    return reftype

def check_dataset_ids(datasets):
    if not isinstance(datasets, list):
        raise InvalidDatasetIds("Expected list of dataset ids.")
    for dataset in datasets:
        if not isinstance(dataset, basestring):
            raise InvalidDatasetIds("Expected datasets to be official id strings.")

def check_header_map(header_map):
    if not isinstance(header_map, dict):
        raise InvalidDatasetIds("Expected object mapping dataset ids to headers: { dataset_id : { header } }.")
    for dataset, header in header_map.items():
        if not isinstance(dataset, basestring):
            raise InvalidDatasetIds("Bad dataset id: " + repr(dataset))
        try:
            check_header(header)
        except Exception as exc:
            raise InvalidHeaderError("Invalid header at dataset id '{}' : '{}'".format(dataset, str(exc)))

def check_file_list(files):
    if not isinstance(files, (list, tuple, type(None))):
        raise InvalidFileList("Expected list of filenames or None.")
    if files:
        for name in files:
            if not isinstance(name, basestring):
                raise InvalidFileList("Expected list of filenames or None.")

def check_string_list(strings):
    if not isinstance(strings, (list, tuple, type(None))):
        raise Invalid("Expected list of strings or None.")
    if strings:
        for name in strings:
            if not isinstance(name, basestring):
                raise InvalidFileList("Expected list of strings or None.")

# ===========================================================================

@jsonrpc_method('list_mappings(observatory=String, glob_pattern=String)')
def list_mappings(request, observatory, glob_pattern):
    if observatory is None:
        observatory = config.observatory
    check_observatory(observatory)
    if not re.match(LIST_GLOB_RE, glob_pattern):
        raise BadListGlobError("Illegal glob pattern, / not permitted '%s'" % glob_pattern)
    return rmap.list_mappings(glob_pattern, observatory)

@jsonrpc_method('get_best_references(context=String, header=Object, reftypes=Array)')
def get_best_references(request, context, header, reftypes):
    context = check_context(context)
    check_header(header)
    check_reftypes(reftypes)
    conditioned = utils.condition_header(header)
    return rmap.get_best_references(context, conditioned, include=reftypes)

'''
These are commented out mainly because they have unbounded runtimes.

@jsonrpc_method('get_best_references_by_ids(context=String, dataset_ids=Array, reftypes=Array)')
def get_best_references_by_ids(request, context, dataset_ids, reftypes):
    context = check_context(context)
    check_dataset_ids(dataset_ids)
    check_reftypes(reftypes)
    pmap = rmap.get_cached_mapping(context)
    headers = database.get_dataset_headers_by_id(dataset_ids=dataset_ids, observatory=pmap.observatory)
    result = {}
    for id, header in headers.items():
        try:
            result[id] = (True, rmap.get_best_references(context, header, include=reftypes, condition=True))
        except Exception as exc:
            result[id] = (False, "FAILED: " + str(exc))
    return result

@jsonrpc_method('get_best_references_by_header_map(context=String, headers=Object, reftypes=Array)')
def get_best_references_by_header_map(request, context, headers, reftypes):
    context = check_context(context)
    check_header_map(headers)
    check_reftypes(reftypes)
    result = {}
    for id, header in headers.items():
        try:
            result[id] = (True, rmap.get_best_references(context, header, include=reftypes, condition=True))
        except Exception as exc:
            result[id] = (False, "FAILED: " + str(exc))
    return result
'''

@jsonrpc_method('get_mapping_names(context=String)')
def get_mapping_names(request, context):
    context = check_context(context)
    ctx = rmap.get_cached_mapping(context)
    return ctx.mapping_names()

@jsonrpc_method('get_reference_names(context=String)')
def get_reference_names(request, context):
    context = check_context(context)
    ctx = rmap.get_cached_mapping(context)
    return ctx.reference_names()

CRDS_JSONRPC_CHUNK_SIZE = 2**23    # 8M

@jsonrpc_method('get_file_chunk(context=String, filename=String, chunk=Number)')
def get_file_chunk(request, context, filename, chunk):
    context = check_context(context)
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

@jsonrpc_method('get_url(context=String, file=String)')
def get_url(request, context, file):
    context = check_context(context)
    check_known_file(file)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, file)

@jsonrpc_method('get_file_info(context=String, file=String)')
def get_file_info(request, context, file):
    context = check_context(context)
    blob = check_known_file(file)
    blob.thaw()
    return blob.info

@jsonrpc_method('get_file_info_map(observatory=String, files=Array, fields=Array)')
def get_file_info_map(request, observatory, files, fields):
    """Return { filename : { field_info, ...} } for filenames in `files` with field_info defined by 
    listed FileBlob `fields`.
    
    If `files` is None return for all files.
    If `fields` is None return for all fields.
    """
    check_observatory(observatory)
    check_file_list(files)
    check_string_list(fields)
    filemap = imodels.get_fileblob_map(observatory=observatory)
    if files is None:
        files = filemap.keys()
    if fields is None:
        blob0 = filemap.values()[0]
        blob0.thaw()
        fields = blob0.info.keys()
    result = {}
    for name in files:
        try:
            blob = filemap[name]
        except KeyError:
            result[name] = "NOT FOUND"
            continue
        blob.thaw()
        result[name] = { field:value for (field, value) in blob.info.items() if field in fields }
    return result

@jsonrpc_method('get_dataset_headers_by_id(context=String, dataset_ids=Array)')
def get_dataset_headers_by_id(request, context, dataset_ids):
    context = check_context(context)
    check_dataset_ids(dataset_ids)
    pmap = rmap.get_cached_mapping(context)
    return database.get_dataset_headers_by_id(dataset_ids=dataset_ids, observatory=pmap.observatory)

@jsonrpc_method('get_dataset_headers_by_instrument(context=String, instrument=Array)')
def get_dataset_headers_by_instrument(request, context, instrument):
    context = check_context(context)
    check_instrument(instrument)
    pmap = rmap.get_cached_mapping(context)
    return database.get_dataset_headers_by_instrument(instrument, observatory=pmap.observatory)

@jsonrpc_method('get_dataset_ids(context=String, instrument=String)')
def get_dataset_ids(request, context, instrument):
    context = check_context(context)
    check_instrument(instrument)
    pmap = rmap.get_cached_mapping(context)
    return database.get_dataset_ids(instrument, observatory=pmap.observatory)

# ===============================================================
# ===============================================================

@jsonrpc_method('file_exists(filename=String)')
def file_exists(request, filename):
    return bool(imodels.file_exists(filename))

@jsonrpc_method('get_default_context(observatory=String)')
def get_default_context(request, observatory):
    if observatory is None:
        observatory = config.observatory
    observatory = observatory.lower()
    check_observatory(observatory)
    return imodels.get_default_context(observatory, state="operational")

@jsonrpc_method('get_context_by_date(date=String, observatory=String)')
def get_context_by_date(request, date, observatory):
    return check_context(date, observatory)

@jsonrpc_method('get_server_info()')
def get_server_info(request):
    info = {
        "edit_context" : imodels.get_default_context(config.observatory),
        "operational_context" : imodels.get_default_context(
            config.observatory, state="operational"),
        "observatory" : config.observatory,
        "crds_version" : versions.get_version("crds"),
        "reference_url": {
            "checked" : {
                config.observatory : config.CRDS_REFERENCE_URL,
                },
            "unchecked" : {
                config.observatory : config.CRDS_UNCHECKED_REFERENCE_URL,
                },
            },
        "mapping_url": {
            "checked" : {
                config.observatory : config.CRDS_MAPPING_URL,
                },
            "unchecked" : {
                config.observatory : config.CRDS_UNCHECKED_MAPPING_URL,
                },
            },
        }
    return info


#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_mapping_data(String, String)')
def get_mapping_data(request, context, mapping):
    context = check_context(context)
    check_mapping(mapping)
    where = rmap.locate_mapping(mapping)
    return open(where).read()

#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_mapping_url(String, String)')
def get_mapping_url(request, context, mapping):
    context = check_context(context)
    check_mapping(mapping)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, mapping)

#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_reference_data(String, String)')
def get_reference_data(request, context, reference):
    context = check_context(context)
    check_reference(reference)
    blob = imodels.FileBlob.load(reference)
    where = blob.pathname
    refdata = open(where).read()
    return base64.b64encode(refdata)

#  XXXX Deprecated XXXXXXX <---------------------------------

@jsonrpc_method('get_reference_url(String, String)')
def get_reference_url(request, context, reference):
    context = check_context(context)
    check_reference(reference)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, reference)

#@jsonrpc_method('jsonapi.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('jsonapi.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
