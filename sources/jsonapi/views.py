"""This module defines JSON-RPC views and checking functions in the django-json-rpc paradigm."""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
# from builtins import str

import sys
import base64
import math
import re
import zlib
import gzip
import os.path
import glob
import json
import traceback

# ===========================================================================

from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import Error
from jsonrpc._json import dumps
from jsonrpc.site import jsonrpc_site

# ===========================================================================

from django.utils import html
from django.contrib.auth.models import User

# ===========================================================================

from . import crds_db

from crds.server.interactive import models as imodels
from crds.server.interactive import versions
from crds.server.interactive.common import DATASET_ID_RE, FITS_KEY_RE, FITS_VAL_RE, LIST_GLOB_RE
from crds.server.interactive.common import INSTRUMENT_RE, FIELD_RE
from crds.server.interactive.common import verbose, profile, log_view
from crds.server import config as sconfig    # server config file

from crds.server.jpoll import views as jviews
from crds.server.interactive import submit

# ===========================================================================

from crds.client import proxy
from crds.core import rmap, utils, log, timestamp, pysh, python23, heavy_client, exceptions
from crds.core import config                     # client config file
from crds.core.config import FILE_RE, check_filename
import crds

# ===========================================================================

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
    """Create a CRDS server URL for a filename,  i.e. a URL including possible checking."""
    if config.is_mapping(filename):
        url = sconfig.CRDS_MAPPING_URL + filename
    else:
        url = sconfig.CRDS_REFERENCE_URL + filename
    return url

def create_unchecked_url(observatory, filename):
    """Create an archive URL for a filename.   Simple file download URL."""
    if config.is_mapping(filename):
        url = sconfig.CRDS_UNCHECKED_MAPPING_URL + filename
    else:
        url = sconfig.CRDS_UNCHECKED_REFERENCE_URL + filename
    return url

# ===========================================================================

class EncError(Error):
    """HTML encode the error message to prevent script injection in error messages."""
    def __init__(self, *args, **keys):
        # self.__msg = html.format_html(*args, **keys)
        self.__msg = args[0].format(*args[1:], **keys)
        super(EncError, self).__init__(self.__msg)
    
    def __repr__(self):
        return self.__class__.__name__ + "(" + repr(self.__msg) + ")"
        
    def __str__(self):
        return self.__msg

class UnknownContextError(EncError):
    """The specified context is not a known CRDS mapping."""
    
class MismatchedContextError(EncError):
    """The specified context's observatory doesn't match this server."""
    
class UnknownMappingError(EncError):
    """The specified mapping parameter is not a known CRDS mapping file."""
    
class UnknownReferenceError(EncError):
    """The specified reference parameter is not a known CRDS reference file."""
    
class InvalidHeaderError(EncError):
    """The specified header parameter is not suitable."""

class InvalidObservatoryError(EncError):
    """The specified observatory is not supported."""
    
class InvalidInstrumentError(EncError):
    """The specified instrument is not supported."""
    
class InvalidReftypesError(EncError):
    """The specified reftypes is not a list of strings."""

class UnknownFile(EncError):
    """There's no record of a file in the CRDS database."""

class UnavailableFile(EncError):
    """A known file is not available for download,  either because it is waiting
    for archiving or not yet generally available.
    """
class BlacklistedFile(EncError):
    """A known file has been blacklisted and should no longer be used."""

class InvalidChunk(EncError):
    """The data chunk number requested from a file was invalid."""
    
class BadFilenameError(EncError):
    """A filename uses characters prohibited to prevent SQL injection."""

class BadListGlobError(EncError):
    """A list search pattern uses characters prohibited to prevent SQL injection."""

class InvalidDatasetIds(EncError):
    """Expected a list of dataset id strings but got something else."""

class InvalidDateFormat(EncError):
    """Received a date with an invalid format."""

class InvalidDateBasedContext(EncError):
    """Received a data based context with an invalid format."""

class InvalidFileList(EncError):
    """Not a list of file names."""

class InvalidFieldList(EncError):
    """Not a list of database field names."""
    
class UnpushableContextKind(EncError):
    """The specified context kind is invalid for pushing from client to server."""
    
class InvalidKey(EncError):
    """The specified authentication key has an invalid format or bad value."""

class InvalidPipelineName(EncError):
    """The specified remote pipeline has an invalid format or bad value."""

def check_known_file(filename):
    """Check that `filename` is known to CRDS, available, and/or not blacklisted."""
    check_filename(filename)
    blob = imodels.file_exists(filename)
    if blob is None:
        raise UnknownFile("File '{0}' is not known to CRDS.", filename)
    if not blob.available: 
        raise UnavailableFile("File '{0}' is not yet available.", filename)
    return blob

def check_context(context, observatory=None):
    """Ensure that `context` is either a known literal context or a valid date based context specification.
    Return the name of the corresponding literal context.
    """
    if observatory is None:    # json_rpc wrapper passes None when unspecified, not unspecified
        observatory = sconfig.observatory
    else:
        observatory = check_observatory(observatory)
    if not config.is_mapping(context):  # this is for speed, to short circuit most checking
        if not config.is_mapping_spec(context):  # this is for more clarity
            raise UnknownContextError("Context parameter '{0}' is not a .pmap, .imap, or .rmap file"
                                      " or a valid date based context specification.", context)
        context = _check_date_based_context(context, observatory)
    if sconfig.observatory not in context:
        raise MismatchedContextError("Requested context '{0}' doesn't match the observatory '{1}'" \
                                     " supported by this server.   Switch servers or contexts.", 
                                     context, sconfig.observatory)
    _blob = check_known_file(context)
    if not config.is_mapping(context):
        raise UnknownContextError("Context parameter '{0}' is not a known CRDS .pmap, .imap, or .rmap file.", context)
    return context

def _check_date_based_context(context, observatory):
    """Check `context` to see if it is a date based context specification.   If it is,
    translate it into a literal .pmap, .imap, or .rmap name.   Otherwise return `context` unchanged.
    """
    instrument = filekind = None
    match = config.CONTEXT_DATETIME_RE.match(context)
    if match:
        context = _pmap_from_date(context, observatory)
    else:        
        match = config.CONTEXT_RE.match(context)
        if match:
            obs_instr_kind = match.group("context")[:-1]
            parts = obs_instr_kind.split("-")
            if not 1 <= len(parts) <= 3:
                raise InvalidDateBasedContext("Invalid date based context [observatory-[instrument-[reftype]]] spec.")
            observatory = check_observatory(parts[0])
            instrument = parts[1] if len(parts) > 1 else None
            filekind = parts[2] if len(parts) > 2 else None
            datestr = match.group("date")
            if datestr in imodels.CONTEXT_TYPES:  # server defaults are "pseudo dates" :-)
                context = imodels.get_default_context(observatory, datestr)
            else:
                context = _pmap_from_date(datestr, observatory)
    if instrument:
        pmap = crds.get_pickled_mapping(context)  # reviewed
        try:
            instrument = check_instrument(instrument)
        except Exception:
            raise InvalidDateBasedContext("Bad instrument '{0}' in CRDS date based context specification.", instrument)
        imap = pmap.get_imap(instrument)
        context = imap.name
        if filekind:
            try:
                filekind = check_reftype(filekind)
            except Exception:
                raise InvalidDateBasedContext("Bad reftype '{0}' in  CRDS date based context specification.", filekind)
            context = imap.get_rmap(filekind).name
    return context

def _pmap_from_date(date, observatory):
    """Using `date` and `observatory` lookup the operational context from that period."""
    _dt = check_context_date(date)
    try:
        return imodels.get_context_by_date(date=date, observatory=observatory)
    except Exception:
        raise UnknownContextError("No CRDS context found corresponding to (prior to) date '{0}'", date)

def check_context_date(date):
    """Verify the format of simple context datetime string `date` and return a datetime.datetime object."""
    try:
        if not config.CONTEXT_DATETIME_RE.match(date):
            raise Exception("Forced date error")
        return timestamp.parse_date(date)
    except Exception:
        raise InvalidDateBasedContext(
            "Invalid context date/time format '{0}' "
            "should be YYYY-MM-DDTHH:MM:SS | " + " | ".join(imodels.CONTEXT_TYPES), date)

def check_since_date(date):
    if date is None:
        date = "1900-01-01T00:00:00"
    try:
        return timestamp.is_datetime(date.replace("T"," "))   # secure
    except:
        raise InvalidDateFormat("Invalid date/time specification: '{0}' should be YYYY-MM-DDTHH:MM:SS", date) 

def check_mapping(mapping):
    blob = check_known_file(mapping)
    if blob.type != "mapping":
        raise UnknownMappingError("Mapping parameter '{0}' is not a known CRDS mapping file.", mapping)
    return blob
    
def check_reference(reference):
    blob = check_known_file(reference)
    if blob.type != "reference":
        raise UnknownReferenceError("Reference parameter '{0}' is not a known CRDS reference file.", reference)
    return blob

def check_header(header):
    if not isinstance(header, dict):
        raise InvalidHeaderError("Header parameter is not a dictionary.")
    for key, value in list(header.items()):
        if not isinstance(key, python23.string_types) or not FITS_KEY_RE.match(key):
            raise InvalidHeaderError("Bad key in header {0}", key)
        if not isinstance(value, (python23.string_types, int, float, bool)) or not FITS_VAL_RE.match(value):
            raise InvalidHeaderError("Bad value in header... not a str, int, float, or bool, or illegal str: '{0}'", value)
    return header

def check_observatory(obs):
    obs = obs.lower()
    if obs != imodels.OBSERVATORY:
        raise InvalidObservatoryError("Mismatch between requested observatory '{0}' and server observatory '{1}'", 
                                      obs, imodels.OBSERVATORY)
    return obs

def check_instrument(instr):
    instr = instr.lower()
    if not isinstance(instr, python23.string_types) or not INSTRUMENT_RE.match(instr) or instr not in imodels.INSTRUMENTS:
        raise InvalidInstrumentError("Mismatch between requested instrument '{0}' and server instruments '{1}'", 
                                     instr, imodels.INSTRUMENTS)
    return instr

def check_reftypes(reftypes):
    cleaned = []
    if not isinstance(reftypes, (list, tuple, type(None))):
        raise InvalidReftypesError("reftypes parameter should be a list of reftype/filekind strings or None.")
    if reftypes is not None:
        for reftype in reftypes:
            cleaned.append(check_reftype(reftype))
    return cleaned

def check_reftype(reftype):
    if not isinstance(reftype, python23.string_types):
        raise InvalidReftypesError("Non-string reftype: '{0}'", reftype)
    reftype = reftype.lower()
    if reftype not in imodels.FILEKINDS:
        raise InvalidReftypesError("Reftype '{0}' is not a known reference type.", imodels.FILEKINDS)
    return reftype

def check_dataset_ids(datasets):
    cleaned = []
    if not isinstance(datasets, list):
        raise InvalidDatasetIds("Expected list of dataset ids.")
    for dataset in datasets:
        if not isinstance(dataset, python23.string_types) or not DATASET_ID_RE.match(dataset):
            raise InvalidDatasetIds("Expected datasets to be official id strings.")
        cleaned.append(dataset.upper())
    return cleaned

def check_header_map(header_map):
    if not isinstance(header_map, dict):
        raise InvalidDatasetIds("Expected object mapping dataset ids to headers: { dataset_id : { header } }.")
    for dataset, header in list(header_map.items()):
        if not isinstance(dataset, python23.string_types) or (not DATASET_ID_RE.match(dataset) and not FILE_RE.match(dataset)):
            raise InvalidDatasetIds("Bad dataset id: '{0}'", dataset)
        try:
            check_header(header)
        except Exception as exc:
            raise InvalidHeaderError("Invalid header at dataset id '{0}' : '{1}'", dataset, str(exc))
    return header_map

def check_file_list(files):
    if not isinstance(files, (list, tuple, type(None))):
        raise InvalidFileList("Expected list of filenames or None.")
    if files:
        for name in files:
            if not isinstance(name, python23.string_types) or not FILE_RE.match(name):
                raise InvalidFileList("Expected list of filenames or None.")
    return files

def check_field_list(fields):
    if not isinstance(fields, (list, tuple, type(None))):
        raise InvalidFieldList("Expected list of fields or None.")
    if fields:
        for name in fields:
            if not isinstance(name, python23.string_types) or not FIELD_RE.match(name):
                raise InvalidFileList("Expected list of fields or None.")
    return fields

def check_context_kind(kind):
    if kind not in ["operational"]:
        raise UnpushableContextKind("The specified context kind is invalid.")
    return kind

def check_key(key):
    if not re.match(r"\w+", key):
        raise InvalidKey("The specified key is invalid.")
    return key

def check_pipeline_name(pipeline):
    if not re.match(r"(\w|/)+", pipeline):
        raise InvalidPipelineName("The specified pipeline name is invalid.")
    return pipeline

BOOL_TRANS = {
        "True": True,
        "TRUE": True,
        "true": True,
        True: True,
        "False": False,
        "FALSE": False,
        "false": False,
        False: False,
        "nil": False,
        }

def check_boolean(flag):
    """Verify boolean input value and return Python bool."""
    assert flag in BOOL_TRANS, "Invalid boolean value."
    return BOOL_TRANS[flag]

class InvalidUserError(EncError):
    """The specified username is not known to this server."""
 
def check_username(username):
    """Verify that username is a valid user."""
    try:
        if username != "*":
            assert len(list(User.objects.filter(username=username))) == 1
    except Exception:
        raise InvalidUserError("The specified CRDS server username " + repr(username) + " is invalid.")
    return username

# ===========================================================================

@jsonrpc_method('list_mappings(observatory=String, glob_pattern=String)')   # secure
def list_mappings(request, observatory, glob_pattern):
    return _list_mappings(observatory, glob_pattern)

# NOTE: Asynchronous delivery status that defines the availability of files complicates
# caching here,  at a minimum update_delivery_status() shoud be hoisted outsite
# the memory caching.  Updates to the file blob status should then invalidate the cache.
# causing this function to re-execute making new files available.

# @imodels.crds_cached
def _list_mappings(observatory, glob_pattern):
    if observatory is None:
        observatory = sconfig.observatory
    check_observatory(observatory)
    if not re.match(LIST_GLOB_RE, glob_pattern):
        raise BadListGlobError("Illegal glob pattern, not permitted '{0}'", glob_pattern)
    
    # Check if files en route to archive already got there.
    imodels.update_delivery_status()
    
    # This just lists all the files in the cache,  some of which aren't achived or even confirmed.
    mappings = rmap.list_mappings(glob_pattern, observatory)
    # In order to sync obsolete bad mappings,  it's important *not* to check for bad files.
    # Weed out the files not in an available state.
    blobs = imodels.get_fileblob_map(name__in = mappings, # rejected = False, blacklisted = False, 
                                    state__in = sconfig.CRDS_DISTRIBUTION_STATES)

    return sorted(blobs.keys())

@jsonrpc_method('list_references(observatory=String, glob_pattern=String)')   # secure
def list_references(request, observatory, glob_pattern):
    return _list_references(observatory, glob_pattern)

# NOTE:  See notes on Asynchronous delivery status above under list_mappings().

# @imodels.crds_cached
def _list_references(observatory, glob_pattern):
    """List the *available* (as determined by pending deliveries and the CRDS database)
    references found in the CRDS cache that match `glob_pattern.`
    """
    if observatory is None:
        observatory = sconfig.observatory
    check_observatory(observatory)
    if not re.match(LIST_GLOB_RE, glob_pattern):
        raise BadListGlobError("Illegal glob pattern, not permitted '{0}'", glob_pattern)
    
    # Check if files en route to archive already got there.
    imodels.update_delivery_status()
    
    # This just lists all the files in the cache,  some of which aren't achived or even confirmed.
    references = rmap.list_references(glob_pattern, observatory)

    # In order to sync obsolete bad mappings,  it's important *not* to check for bad files.
    # Weed out the files not in an available state.
    blobs = imodels.get_fileblob_map(name__in = references, # rejected = False, blacklisted = False, 
                                     state__in = sconfig.CRDS_DISTRIBUTION_STATES)

    return sorted(blobs.keys())

@jsonrpc_method('get_best_references(context=String, header=Object, reftypes=Array)')  # secure
# @verbose()
def get_best_references(request, context, header, reftypes):
    context = check_context(context)
    header = check_header(header)
    reftypes = check_reftypes(reftypes)
    return heavy_client.hv_best_references(context, header, include=reftypes, condition=True)

MAX_BESTREFS_PER_RPC = 1000

# ===========================================================================================================

@jsonrpc_method('get_best_references_by_ids(context=String, dataset_ids=Array, reftypes=Array, include_headers=Boolean)')   # secure
def get_best_references_by_ids(request, context, dataset_ids, reftypes, include_headers):
    return _get_best_references_by_ids(request, context, dataset_ids, reftypes, include_headers)

def _get_best_references_by_ids(request, context, dataset_ids, reftypes, include_headers):
    """Core computation which determines best refences for a list of datasets relative to 
    a particular CRDS context which can be specified symbolically.
    """
    context = check_context(context)
    if len(dataset_ids) > MAX_BESTREFS_PER_RPC:
        raise InvalidDatasetIds("Get best references by ids limited to <= '{0}' datasets per call.", MAX_BESTREFS_PER_RPC)
    dataset_ids = check_dataset_ids(dataset_ids)
    reftypes = check_reftypes(reftypes)
    include_headers = check_boolean(include_headers)

    headers = get_simplified_dataset_headers_by_id(context, dataset_ids)

    log.verbose("Headers for", repr(dataset_ids), "=", headers)
    result = { "headers" : headers } if include_headers else {}

    for dataset_id in dataset_ids:
        try:
            header = headers[dataset_id]
        except KeyError:
            result[dataset_id] = (False, "FAILED: " + "unable to obtain matching parameters.")
            continue
        if isinstance(header, python23.string_types):
            result[dataset_id] = (False, header)
        else:
            try:
                result[dataset_id] = (True, heavy_client.hv_best_references(context, header, include=reftypes, condition=True))
            except Exception as exc:
                result[dataset_id] = (False, "FAILED: " + str(exc))
    return result

@jsonrpc_method('get_aui_best_references(date=String, dataset_ids=Array)')   # secure
def get_aui_best_references(request, date, dataset_ids):
    """Present the AUI with a simpler tailored interface for getting lists of bestrefs by date."""
    context = check_context(date)
    dataset_ids = check_dataset_ids(dataset_ids)
    # checking happens in _get_best...
    complex_results = _get_best_references_by_ids(request, context, dataset_ids, reftypes=(), include_headers=False)
    simpler_results = {}
    for dataset_id, result in list(complex_results.items()):
        if result[0]:
            filenames = []
            for typename, filename in list(result[1].items()):
                if not filename.startswith("NOT FOUND"):
                    filenames.append(filename)
            simpler_results[dataset_id] = (True, filenames)
        else:
            simpler_results[dataset_id] = result
    return simpler_results

def get_simplified_dataset_headers_by_id(context, dataset_ids):
    """Simplified dataset headers first computes synthetic dataset headers,  and then maps the
    resulting uniform compound dataset ids back onto the original dataset ID input set,  taking
    the first member of any association as the definitive member rather than returning all members
    as compound IDs.  Simple ID inputs result in simple ID outputs,  not compound IDs.   Compound ID
    inputs still result in compound ID outputs.
    """
    dataset_ids = [ did.upper() for did in dataset_ids ]
    header_map = call_context_function(context, "database.get_synthetic_dataset_headers_by_id", context, dataset_ids) 
    sorted_ids = sorted(header_map.keys())
    simplified_map = {}
    for did in dataset_ids:
        try:
            simplified_map[did] = header_map[did]
        except KeyError:
            try:
                # replace(".","_") is a hack to support JWST ID's in either .detector or _detector formats
                # original JWST API has .detector but _detector is in common use in filenames.
                # CRDS normalized ID for is .detector
                containing = [did2 for did2 in sorted_ids if (did in did2) or (did in did2.replace(".","_"))]
                simplified_map[did] = header_map[containing[0]]
            except Exception:
                continue
    return simplified_map

# ===========================================================================================================

@jsonrpc_method('get_best_references_by_header_map(context=String, headers=Object, reftypes=Array)') # secure
def get_best_references_by_header_map(request, context, headers, reftypes):  
    context = check_context(context)
    headers = check_header_map(headers)
    reftypes = check_reftypes(reftypes)
    result = {}
    for id, header in list(headers.items()):
        try:
            result[id] = (True, heavy_client.hv_best_references(context, header, include=reftypes, condition=True))
        except Exception as exc:
            result[id] = (False, "FAILED: " + str(exc))
    return result

# ===========================================================================================================

@jsonrpc_method('get_mapping_names(context=Object)') # secure
def get_mapping_names(request, context):
    """Return the list of mappings referred to by `context` or a list of contexts as
    defined by loading the mapping closure from the file system.
    """
    return _get_mapping_names(context)

@imodels.crds_cached
def _get_mapping_names(context):
    """Return the list of mappings referred to by `context` or a list of contexts.""" 
    if isinstance(context, python23.string_types):
        context = [context]
    elif not isinstance(context, (list, tuple)):
        raise UnknownMappingError("Not a .pmap name or list of .pmap names")
    mappings = set()
    for pmap in context:
        pmap = check_context(pmap)
        ctx = crds.get_cached_mapping(pmap)
        mappings = mappings.union(set(ctx.mapping_names()))
    return sorted(list(mappings))

# ===========================================================================================================

@jsonrpc_method('get_reference_names(context=String)') # secure
def get_reference_names(request, context):
    context = check_context(context)
    return _get_reference_names(context)

@imodels.crds_cached
def _get_reference_names(context):
    """Return the list of references referred to by `context` as defined by fully loading
    `context` from the file system.
    """ 
    ctx = crds.get_pickled_mapping(context)  # reviewed
    return ctx.reference_names()

# ===========================================================================================================

@jsonrpc_method('get_url(context=String, filename=String)')  # secure
def get_url(request, context, filename):
    """Based on `context` to determine observatory,  return the URL of `filename`."""
    context = check_context(context)
    check_filename(filename)
    ctx = crds.get_pickled_mapping(context)  # reviewed
    return create_url(ctx.observatory, filename)

# ===========================================================================================================

@jsonrpc_method('get_file_info(observatory=Object, filename=String)')   # secure
def get_file_info(request, observatory, filename):
    """Return the CRDS catalog info for a single `filename` of the specified `observatory`."""
    try:
        observatory = check_observatory(observatory)
    except InvalidObservatoryError:   # originally this worked on context, not observatory,  now both.
        observatory = crds.get_pickled_mapping(check_context(observatory)).observatory  # load mapping and fetch observ.  # reviewed
    blob = check_known_file(filename)
    blob.thaw()
    return blob.info

@jsonrpc_method('get_file_info_map(observatory=String, files=Array, fields=Array)')  # secure
def get_file_info_map(request, observatory, files, fields):
    """Return { filename : { field_info, ...} } for filenames in `files` with field_info defined by 
    listed FileBlob `fields`.
    
    If `files` is None return for all files.
    If `fields` is None return for all fields.
    """
    observatory = check_observatory(observatory)
    files = check_file_list(files)
    fields = check_field_list(fields)
    filemap = imodels.get_fileblob_map(observatory=observatory)
    if files is None:
        files = list(filemap.keys())
    if fields is None:
        blob0 = list(filemap.values())[0]
        blob0.thaw()
        fields = list(blob0.info.keys())
    result = {}
    for name in files:
        try:
            blob = filemap[name]
        except KeyError:
            result[name] = "NOT FOUND"
            continue
        blob.thaw()
        result[name] = { field:value for (field, value) in list(blob.info.items()) if field in fields }
    return result

MAX_HEADERS_PER_RPC = 1000

# ===============================================================

def call_context_function(context, func_name, *args, **keys):
    """Based on `context`,  load an observtory specific version of `func_name`
    and call it with the remaining positional and keyword parameters.
    """
    pmap = crds.get_pickled_mapping(context)  # reviewed
    func = utils.get_object("crds.server", "x" + pmap.observatory, func_name)
    return func(*args, **keys)

@jsonrpc_method('get_dataset_headers_by_id(context=String, dataset_ids=Array, datasets_since=String)') # secure
def get_dataset_headers_by_id(request, context, dataset_ids, datasets_since):
    context = check_context(context)
    dataset_ids = check_dataset_ids(dataset_ids)
    datasets_since = check_since_date(datasets_since)   # IGNORED
    assert len(dataset_ids) <= MAX_HEADERS_PER_RPC, \
           "Too many ids.   More than {} datasets specified.".format(MAX_HEADERS_PER_RPC)
    return call_context_function(context, "database.get_dataset_headers_by_id", context, dataset_ids)

@jsonrpc_method('get_dataset_ids(context=String, instrument=String, datasets_since=Object)')   # secure
def get_dataset_ids(request, context, instrument, datasets_since=None):
    context = check_context(context)
    instrument = check_instrument(instrument)
    datasets_since = check_since_date(datasets_since)
    return call_context_function(context, "database.get_dataset_ids", instrument, datasets_since)

# ===============================================================

@jsonrpc_method('file_exists(filename=String)')   # secure
def file_exists(request, filename):
    _filename = check_known_file(filename)
    return True

@jsonrpc_method('get_default_context(observatory=String)')    # secure
def get_default_context(request, observatory):
    if observatory is None:
        observatory = sconfig.observatory
    observatory = check_observatory(observatory)
    return imodels.get_default_context(observatory, "operational")

@jsonrpc_method('get_context_by_date(date=String, observatory=String)')  # secure
def get_context_by_date(request, date, observatory):
    if observatory is None:
        observatory = sconfig.observatory
    else:
        observatory = check_observatory(observatory)
    try:
        return check_context(date, observatory)
    except exceptions.IrrelevantReferenceTypeError:
        return "N/A"

# ===========================================================================================================

@jsonrpc_method('get_server_info()')   # secure
# @log_view
# @verbose(100)
def get_server_info(request):
    """Core information about server configuration used to drive CRDS serverless operating modes."""
    info = _get_server_info()
    info["last_synced"] = str(timestamp.now())
    return info

@imodels.crds_cached
def _get_server_info():
    """Memcached version of get_server_info(),  'request' is not cacheable."""
    version_info = versions.get_version("crds")
    version_info.pop("file", None)  # don't leak absolute path
    version_info["svnurl"] = "/" + "/".join(version_info["svnurl"].split("/")[3:])  # don't leak full url,  just branch
    info = {
        "last_refreshed" : str(timestamp.now()),
        "bad_files_list" : imodels.get_bad_files(sconfig.observatory),
        "force_remote_mode" : sconfig.FORCE_REMOTE_MODE,
        "mappings" : list_mappings(None, None, "*map"),
        "context_history" : imodels.get_context_history_tuples(sconfig.observatory),
        "observatory" : sconfig.observatory,
        "crds_version" : version_info,

        # These define client:server limits,  not server:archive-web-service limits
        "max_headers_per_rpc" : MAX_HEADERS_PER_RPC,
        "max_bestrefs_per_rpc" : MAX_BESTREFS_PER_RPC,

        "reference_url": {
            "checked" : {
                sconfig.observatory : sconfig.CRDS_REFERENCE_URL,
                    },
            "unchecked" : {
                sconfig.observatory : sconfig.CRDS_UNCHECKED_REFERENCE_URL,
                },
            },

        "mapping_url": {
            "checked" : {
                sconfig.observatory : sconfig.CRDS_MAPPING_URL,
                },
            "unchecked" : {
                sconfig.observatory : sconfig.CRDS_UNCHECKED_MAPPING_URL,
                },
            },
        }

    for context in imodels.CONTEXT_TYPES:
        info[context + "_context"] = imodels.get_default_context(sconfig.observatory, context)

    return info

# ===============================================================

@jsonrpc_method('get_required_parkeys(context=String)')   # secure
def get_required_parkeys(request, context):
    context = check_context(context)
    pmap = crds.get_pickled_mapping(context)  # reviewed
    return pmap.get_required_parkeys()

# ===============================================================

@jsonrpc_method('get_sqlite_db(observatory=String)')    # secure
def get_sqlite_db(request, observatory):
    """Return the CRDS catalog database as a compressed, base64 encoded string."""
    return _get_sqlite_db(observatory)

@imodels.crds_cached
def _get_sqlite_db(observatory):
    """Return the CRDS catalog database as a compressed, base64 encoded string."""
    observatory = check_observatory(observatory)
    db_path = crds_db.dump_sqlite_db(observatory)
    db = open(db_path,"rb").read()
    return base64.b64encode(zlib.compress(db)).decode('ascii')

# ===============================================================

@jsonrpc_method('get_mapping_url(String, String)')  # secure
def get_mapping_url(request, context, mapping):
    context = check_context(context)
    _blob = check_mapping(mapping)
    ctx = crds.get_pickled_mapping(context)   # reviewed
    return create_url(ctx.observatory, mapping)

@jsonrpc_method('get_reference_url(String, String)') # secure
def get_reference_url(request, context, reference):
    context = check_context(context)
    _blob = check_reference(reference)
    ctx = crds.get_pickled_mapping(context)  # reviewed
    return create_url(ctx.observatory, reference)

# ===============================================================

MAX_BESTREFS_ERR_LINES = 1000

#
# This service returns the precomputed results produced by the cronjob
# monitor_reprocessing script as a JSON object/struct.
#

# @log_view
@jsonrpc_method('get_affected_datasets(observatory=String, old_context=Object, new_context=Object)')
def get_affected_datasets(request, observatory, old_context, new_context):
    observatory = check_observatory(observatory)   #  XXXX observatory ignored
    reprocessing_dir = os.path.join(os.environ["CRDS"], "monitor_reprocessing")
    old_serial_num = check_for_serial_num(old_context)
    new_serial_num = check_for_serial_num(new_context)
    old_serial_patt = "*[0-9]" if old_serial_num is None else old_serial_num
    new_serial_patt = "[0-9]*" if new_serial_num is None else new_serial_num
    dir_patt = "*" + old_serial_patt + "_" + new_serial_patt
    transitions_glob = os.path.join(reprocessing_dir, dir_patt)
    not_ready = "No precomputed affected datasets results exist for old_context='{}' and new_context='{}'".format(old_context, new_context)
    try:
        computation_dir  = sorted(glob.glob(transitions_glob))[-1]
    except IndexError as exc:
        raise ValueError(not_ready)
    response = compose_affected_datasets_response(observatory, computation_dir)
    if isinstance(response["bestrefs_status"], python23.string_types) and "FAILED:" in response["bestrefs_status"]:
        raise ValueError(not_ready)
    return response

def check_for_serial_num(context):
    """Given an unvalidated context object,  produce the serial number for it or None.
    Raise an exception if it's invalid.
    """
    if context is None:
        return None
    checked = check_context(context)
    assert context.endswith(".pmap"), "context must be a .pmap"
    return checked.split(".")[-2].split("_")[-1]

@imodels.crds_cached
def compose_affected_datasets_response(observatory, computation_dir):
    """Given the output directory for an affected_datasets computation,
    presumably run by monitor_reprocessing cron,  return a Struct of
    results,  including the affected dataset ids.  
    """
    try:
        ids_contents = get_compressed_file(os.path.join(computation_dir, "affected_ids.txt"))
        affected_ids = ids_contents.splitlines(False)
    except Exception as exc:
        affected_ids = "FAILED: " + str(exc)

    try:
        dir_parts = computation_dir.split("_")
        old_context, new_context = dir_parts[-2], dir_parts[-1]
        old_context = observatory + "_" + old_context + ".pmap"
        new_context = observatory + "_" + new_context + ".pmap"
    except Exception as exc:
        old_context = new_context = "FAILED: " + str(exc)

    try:
        status_file = os.path.join(computation_dir, "bestrefs.status")
        bestrefs_status = int(open(status_file).read().strip())
    except Exception as exc:
        bestrefs_status = "FAILED: " + str(exc)

    try:
        bestrefs_err_contents = get_compressed_file(os.path.join(computation_dir, "bestrefs_err_truncated.txt"))
    except Exception as exc:
        try:
            bestrefs_err_contents = get_compressed_file(os.path.join(computation_dir, "bestrefs_err.txt"))
        except Exception as exc2:
            bestrefs_err_contents = None
    if bestrefs_err_contents is not None:
        bestrefs_err_lines = bestrefs_err_contents.splitlines(False)
        if len(bestrefs_err_lines) > MAX_BESTREFS_ERR_LINES:
            bestrefs_err_lines = bestrefs_err_lines[:MAX_BESTREFS_ERR_LINES//2] + \
                ["..."] + \
                bestrefs_err_lines[-MAX_BESTREFS_ERR_LINES//2:]
        bestrefs_err_summary = "\n".join(bestrefs_err_lines)
    else:
        bestrefs_err_summary = "FAILED: " + str(exc2)

    try:
        report_dir = computation_dir.split("/")[-1]
    except Exception as exc:
        report_dir = "FAILED: " + str(exc)

    response = utils.Struct()
    response.computation_dir = report_dir
    response.observatory = observatory
    response.affected_ids = affected_ids
    response.bestrefs_status = bestrefs_status
    response.old_context = old_context
    response.new_context = new_context
    response.bestrefs_err_summary = bestrefs_err_summary

    return response

def get_compressed_file(filepath):
    """Return the contents of filepath which may or may not exist with a .gz decoration."""
    if os.path.exists(filepath):
        return open(filepath).read()
    elif os.path.exists(filepath + ".gz"):
        contents = gzip.open(filepath + ".gz", "rb").read().decode("utf-8")
    else:
        raise IOError("File not found: " + str(repr(filepath)))
    return contents

# ===============================================================

@jsonrpc_method('get_context_history(String)')  # secure
def get_context_history(request, observatory):
    observatory = check_observatory(observatory)
    return imodels.get_context_history_tuples(observatory)

@jsonrpc_method('push_remote_context(String, String, String, String)')
def push_remote_context(request, observatory, kind, key, context):
    observatory = check_observatory(observatory)
    kind = check_context_kind(kind)
    context = check_context(context, observatory)
    key = check_key(key)
    imodels.push_remote_context(observatory, kind, key, context)
    return None

@jsonrpc_method('get_remote_context(String, String)')
def get_remote_context(request, observatory, pipeline_name):
    observatory = check_observatory(observatory)
    pipeline_name = check_pipeline_name(pipeline_name)
    return imodels.get_remote_context(observatory, pipeline_name)

# ===============================================================

@jsonrpc_method('get_submission_info(String, String)')
def get_submission_info(request, observatory, username):
    """Return parameters relevant to doing command line file submissions."""
    observatory = check_observatory(observatory)
    username = check_username(username)
    return submit.get_submission_info(observatory, username)
 
# # ===============================================================
 
@jsonrpc_method('jpoll_pull_messages(key=String, since_id=String)')
def jpoll_pull_messages(request, key, since_id):
    """Return a list of jpoll message objects from channel defind by `key`
    with sequence numbers after `since_id`.
    """
    return jviews.pull_messages_core(key, since_id=int(since_id))
 
@jsonrpc_method("jpoll_abort(key=String)")
def jpoll_abort(request, key):
    """Mark the process that writes to the channel identified by `key` for
    voluntary termination.
    """
    return jviews.abort_core(key)

# ===============================================================

def  check_version(master_version):
    assert re.match(r"^[a-zA-Z\-\.0-9\_]{1,128}$", master_version), \
        "Invalid version string,  must be 1-128 chars of A-Z, a-z, 0-9, ., -, _"
    return master_version

# ===========================================================================================================

@jsonrpc_method('get_system_versions(master_version=String, context=String)')
def get_system_versions(request, master_version, context):
    """This service looks up a SYSTEM CALVER reference based on `master_version` within
    `context`,  loads it,  and returns it as an object.  The structure of the object is
    outside the scope of CRDS.  Initial references are .json
    """
    master_version = check_version(master_version)
    if context.lower() in ["null", "none"]:
        context = imodels.OBSERVATORY + "-versions"
    context = check_context(context)
    # simulate real world performance more closely
    header = {
        "INSTRUME" : "SYSTEM",
        "META.INSTRUMENT.NAME" : "SYSTEM",
        "CAL_VER" : master_version,
        "META.CALIBRATION_SOFTWARE_VERSION" : master_version,
        "META.OBSERVATION.DATE": "2050-01-01",
        "DATE-OBS" : "2050-01-01",
        "META.OBSERVATION.TIME": "00:00:00",
        "TIME-OBS" : "00:00:00",
        }
    log.set_verbose()
    references = rmap.get_best_references(context, header, condition=True, include=["calver"])
    calver_name = references["calver"]
    if not calver_name.startswith("NOT FOUND") and config.is_reference(calver_name):
        calver_reference = crds.locate_file(references["calver"], imodels.OBSERVATORY)
        with open(calver_reference) as handle:
            contents = json.load(handle)
    else:
        raise exceptions.CrdsLookupError(calver_name)
    return contents

# ===============================================================

@jsonrpc_method('get_delivery_status(since=String)')
def get_delivery_status(request, since):
    since_date = check_since_date(since).replace("T"," ")
    deliveries = imodels.get_delivery_status()
    returned = []
    for delivery in deliveries:
        del delivery["user"]
        del delivery["status_class"]
        if delivery["date"] >= since_date:
            returned.append(delivery)
        else:
            break
    return returned

# ===============================================================

#@jsonrpc_method('jsonapi.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('jsonapi.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
