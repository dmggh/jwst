"""This module defines JSON-RPC views and checking functions in the django-json-rpc paradigm."""

from __future__ import division

import base64
import math
import re
import zlib

from jsonrpc import jsonrpc_method
from jsonrpc.exceptions import Error

from django.utils import html

from crds.server.interactive import models as imodels
from crds.server.interactive import versions, database, crds_db
from crds.server.interactive.common import DATASET_ID_RE, FITS_KEY_RE, FITS_VAL_RE, LIST_GLOB_RE
from crds.server.interactive.common import INSTRUMENT_RE, FIELD_RE
import crds.server.config as config    # server parameters
from crds import rmap, utils, log, timestamp
import crds.config                     # generic client/server
from crds.config import FILE_RE, check_filename

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
    """Create a CRDS server URL for a filename,  i.e. a URL including possible checking."""
    if crds.config.is_mapping(filename):
        url = config.CRDS_MAPPING_URL + filename
    else:
        url = config.CRDS_REFERENCE_URL + filename
    return url

def create_unchecked_url(observatory, filename):
    """Create an archive URL for a filename.   Simple file download URL."""
    if crds.config.is_mapping(filename):
        url = config.CRDS_UNCHECKED_MAPPING_URL + filename
    else:
        url = config.CRDS_UNCHECKED_REFERENCE_URL + filename
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

def check_known_file(filename):
    """Check that `filename` is known to CRDS, available, and/or not blacklisted."""
    check_filename(filename)
    blob = imodels.file_exists(filename)
    if not blob:
        raise UnknownFile("File '{0}' is not known to CRDS.", filename)
    if not blob.available: 
        raise UnavailableFile("File '{0}' is not yet available.", filename)
    return blob

def check_context(context, observatory=None):
    """Ensure that `context` is either a known literal context or a valid date based context specification.
    Return the name of the corresponding literal context.
    """
    if observatory is None:    # json_rpc wrapper passes None when unspecified, not unspecified
        observatory = config.observatory
    else:
        observatory = check_observatory(observatory)
    if not crds.config.is_mapping(context):  # this is for speed, to short circuit most checking
        if not crds.config.is_mapping_spec(context):  # this is for more clarity
            raise UnknownContextError("Context parameter '{0}' is not a .pmap, .imap, or .rmap file"
                                      " or a valid date based context specification.", context)
        context = _check_date_based_context(context, observatory)
    if config.observatory not in context:
        raise MismatchedContextError("Requested context '{0}' doesn't match the observatory '{1}'" \
                                     " supported by this server.   Switch servers or contexts.", 
                                     context, config.observatory)
    _blob = check_known_file(context)
    if not crds.config.is_mapping(context):
        raise UnknownContextError("Context parameter '{0}' is not a known CRDS .pmap, .imap, or .rmap file.", context)
    return context

def _check_date_based_context(context, observatory):
    """Check `context` to see if it is a date based context specification.   If it is,
    translate it into a literal .pmap, .imap, or .rmap name.   Otherwise return `context` unchanged.
    """
    instrument = filekind = None
    match = crds.config.CONTEXT_DATETIME_RE.match(context)
    if match:
        context = _pmap_from_date(context, observatory)
    else:        
        match = crds.config.CONTEXT_RE.match(context)
        if match:
            obs_instr_kind = match.group("context")[:-1]
            parts = obs_instr_kind.split("-")
            if not 1 <= len(parts) <= 3:
                raise InvalidDateBasedContext("Invalid date based context [observatory-[instrument-[reftype]]] spec.")
            observatory = check_observatory(parts[0])
            instrument = parts[1] if len(parts) > 1 else None
            filekind = parts[2] if len(parts) > 2 else None
            datestr = match.group("date")
            if datestr in ["edit", "operational"]:  # server defaults are "pseudo dates" :-)
                context = imodels.get_default_context(observatory=observatory, state=datestr)
            else:
                context = _pmap_from_date(datestr, observatory)
    if instrument:
        pmap = rmap.get_cached_mapping(context)
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
        if not crds.config.CONTEXT_DATETIME_RE.match(date):
            raise Exception("Forced date error")
        return timestamp.parse_date(date)
    except Exception:
        raise InvalidDateBasedContext("Invalid context date/time format '{0}' " \
                                      "should be YYYY-MM-DDTHH:MM:SS | edit | operational", date)

def check_date(date):
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
    for key, value in header.items():
        if not isinstance(key, basestring) or not FITS_KEY_RE.match(key):
            raise InvalidHeaderError("Bad key in header {0}", key)
        if not isinstance(value, (basestring, int, float, bool)) or not FITS_VAL_RE.match(value):
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
    if not isinstance(instr, basestring) or not INSTRUMENT_RE.match(instr) or instr not in imodels.INSTRUMENTS:
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
    if not isinstance(reftype, basestring):
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
        if not isinstance(dataset, basestring) or not DATASET_ID_RE.match(dataset):
            raise InvalidDatasetIds("Expected datasets to be official id strings.")
        cleaned.append(dataset.upper())
    return cleaned

def check_header_map(header_map):
    if not isinstance(header_map, dict):
        raise InvalidDatasetIds("Expected object mapping dataset ids to headers: { dataset_id : { header } }.")
    for dataset, header in header_map.items():
        if not isinstance(dataset, basestring) or (not DATASET_ID_RE.match(dataset) and not FILE_RE.match(dataset)):
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
            if not isinstance(name, basestring) or not FILE_RE.match(name):
                raise InvalidFileList("Expected list of filenames or None.")
    return files

def check_field_list(fields):
    if not isinstance(fields, (list, tuple, type(None))):
        raise InvalidFieldList("Expected list of fields or None.")
    if fields:
        for name in fields:
            if not isinstance(name, basestring) or not FIELD_RE.match(name):
                raise InvalidFileList("Expected list of fields or None.")
    return fields

# ===========================================================================

@jsonrpc_method('list_mappings(observatory=String, glob_pattern=String)')   # secure
def list_mappings(request, observatory, glob_pattern):
    if observatory is None:
        observatory = config.observatory
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
                                    state__in = config.CRDS_DISTRIBUTION_STATES)

    return sorted(blobs.keys())

@jsonrpc_method('get_best_references(context=String, header=Object, reftypes=Array)')  # secure
def get_best_references(request, context, header, reftypes):
    context = check_context(context)
    header = check_header(header)
    reftypes = check_reftypes(reftypes)
    conditioned = utils.condition_header(header)
    return rmap.get_best_references(context, conditioned, include=reftypes)

MAX_DATASETS_PER_CALL = 1000

@jsonrpc_method('get_best_references_by_ids(context=String, dataset_ids=Array, reftypes=Array)')   # secure
def get_best_references_by_ids(request, context, dataset_ids, reftypes):
    context = check_context(context)
    dataset_ids = check_dataset_ids(dataset_ids)
    reftypes = check_reftypes(reftypes)
    pmap = rmap.get_cached_mapping(context)
    if not len(dataset_ids) <= MAX_DATASETS_PER_CALL:
        raise InvalidDatasetIds("Get best references by ids limited to <= '{0}' datasets per call.", MAX_DATASETS_PER_CALL)
    headers = database.get_dataset_headers_by_id(dataset_ids=dataset_ids, observatory=pmap.observatory)
    result = {}
    for dataset_id in dataset_ids:
        try:
            header = headers[dataset_id]
        except KeyError:
            result[dataset_id] = (False, "FAILED: " + "unable to obtain matching parameters.")
            continue
        try:
            result[dataset_id] = (True, rmap.get_best_references(context, header, include=reftypes, condition=True))
        except Exception as exc:
            result[dataset_id] = (False, "FAILED: " + str(exc))
    return result

@jsonrpc_method('get_best_references_by_header_map(context=String, headers=Object, reftypes=Array)') # secure
def get_best_references_by_header_map(request, context, headers, reftypes):  
    context = check_context(context)
    headers = check_header_map(headers)
    reftypes = check_reftypes(reftypes)
    result = {}
    for id, header in headers.items():
        try:
            result[id] = (True, rmap.get_best_references(context, header, include=reftypes, condition=True))
        except Exception as exc:
            result[id] = (False, "FAILED: " + str(exc))
    return result

@jsonrpc_method('get_mapping_names(context=Object)') # secure
def get_mapping_names(request, context):
    """Return the list of mappings referred to by `context` or a list of contexts."""
    if isinstance(context, basestring):
        context = [context]
    elif not isinstance(context, (list, tuple)):
        raise UnknownMappingError("Not a .pmap name or list of .pmap names")
    mappings = set()
    for pmap in context:
        pmap = check_context(pmap)
        ctx = crds.get_cached_mapping(pmap)
        mappings = mappings.union(set(ctx.mapping_names()))
    return sorted(list(mappings))

@jsonrpc_method('get_reference_names(context=String)') # secure
def get_reference_names(request, context):
    context = check_context(context)
    ctx = rmap.get_cached_mapping(context)
    return ctx.reference_names()

CRDS_JSONRPC_CHUNK_SIZE = 2**23    # 8M

@jsonrpc_method('get_file_chunk(context=String, filename=String, chunk=Number)')   # secure
def get_file_chunk(request, context, filename, chunk):
    context = check_context(context)
    blob = check_known_file(filename)
    chunks = int(math.ceil(blob.size / CRDS_JSONRPC_CHUNK_SIZE))
    if not isinstance(chunk, (int, float, basestring)) or math.floor(int(chunk)) != math.floor(chunk):
        raise InvalidChunk("the specified chunk must be an integer index.")
    if not (0 <= chunk < chunks):
        raise InvalidChunk("the specified data chunk '{0}' is out of range.", chunk)
    with open(blob.pathname, "rb") as infile:
        infile.seek(chunk*CRDS_JSONRPC_CHUNK_SIZE)
        data = infile.read(CRDS_JSONRPC_CHUNK_SIZE)
    edata = base64.b64encode(data)
    return [chunks, edata]

@jsonrpc_method('get_url(context=String, filename=String)')  # secure
def get_url(request, context, filename):
    """Based on `context` to determine observatory,  return the URL of `filename`."""
    context = check_context(context)
    check_filename(filename)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, filename)

@jsonrpc_method('get_file_info(observatory=String, filename=String)')   # secure
def get_file_info(request, observatory, filename):
    """Return the CRDS catalog info for a single `filename` of the specified `observatory`."""
    try:
        observatory = check_observatory(observatory)
    except InvalidObservatoryError:   # originally this worked on context, not observatory,  now both.
        observatory = check_context(observatory).observatory  # load mapping and fetch observ.
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

@jsonrpc_method('get_dataset_headers_by_id(context=String, dataset_ids=Array)')   #secure
def get_dataset_headers_by_id(request, context, dataset_ids):
    context = check_context(context)
    dataset_ids = check_dataset_ids(dataset_ids)
    pmap = rmap.get_cached_mapping(context)
    return database.get_dataset_headers_by_id(dataset_ids=dataset_ids, observatory=pmap.observatory)

@jsonrpc_method('get_dataset_headers_by_instrument(context=String, instrument=Array, datasets_since=Object)')  # secure
def get_dataset_headers_by_instrument(request, context, instrument, datasets_since=None):
    if datasets_since is None:
        datasets_since = "0000-01-01 00:00:00"
    context = check_context(context)
    instrument = check_instrument(instrument)
    datasets_since = check_date(datasets_since)
    pmap = rmap.get_cached_mapping(context)
    datasets = database.get_dataset_headers_by_instrument(instrument, observatory=pmap.observatory, 
                                                          datasets_since=datasets_since)
    return _filter_datasets_by_date(instrument, datasets_since, datasets)

def _filter_datasets_by_date(instrument, datasets_since, datasets):
    """Return the mapping of datasets which occurred after `datasets_since` based on exposure start."""
    if datasets_since:
        filtered = {}
        for (datasetid, header) in datasets.items():
            start = header["DATE-OBS"] + " " + header["TIME-OBS"]
            if start < datasets_since:
                log.verbose("Skipping dataset", datasetid, "for", instrument,
                            "based on expstart=" + start, "< datasets_since=" + datasets_since)
            else:
                filtered[datasetid] = header
        return filtered
    else:
        return datasets

@jsonrpc_method('get_dataset_ids(context=String, instrument=String)')   # secure
def get_dataset_ids(request, context, instrument):
    context = check_context(context)
    instrument = check_instrument(instrument)
    pmap = rmap.get_cached_mapping(context)
    return database.get_dataset_ids(instrument, observatory=pmap.observatory)

# ===============================================================

@jsonrpc_method('file_exists(filename=String)')   # secure
def file_exists(request, filename):
    _filename = check_known_file(filename)
    return True

@jsonrpc_method('get_default_context(observatory=String)')    # secure
def get_default_context(request, observatory):
    if observatory is None:
        observatory = config.observatory
    observatory = check_observatory(observatory)
    return imodels.get_default_context(observatory, state="operational")

@jsonrpc_method('get_context_by_date(date=String, observatory=String)')  # secure
def get_context_by_date(request, date, observatory):
    if observatory is None:
        observatory = config.observatory
    else:
        observatory = check_observatory(observatory)
    return check_context(date, observatory)

@jsonrpc_method('get_server_info()')   # secure
def get_server_info(request):
    version_info = versions.get_version("crds")
    version_info.pop("file", None)  # don't leak absolute path
    version_info["svnurl"] = "/" + "/".join(version_info["svnurl"].split("/")[3:])  # don't leak full url,  just branch
    info = {
        "last_synced" : timestamp.now(),
        "edit_context" : imodels.get_default_context(config.observatory),
        "operational_context" : imodels.get_default_context(config.observatory, state="operational"),
        "bad_files" : " ".join(imodels.get_bad_files(config.observatory)),
        "observatory" : config.observatory,
        "crds_version" : version_info,
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

# ===============================================================

@jsonrpc_method('get_required_parkeys(context=String)')   # secure
def get_required_parkeys(request, context):
    context = check_context(context)
    pmap = rmap.get_cached_mapping(context)
    return pmap.get_required_parkeys()

# ===============================================================

@jsonrpc_method('get_sqlite_db(observatory=String)')    # secure
def get_sqlite_db(request, observatory):
    """Return the CRDS catalog database as a compressed, base64 encoded string."""
    observatory = check_observatory(observatory)
    db_path = crds_db.dump_sqlite_db(observatory)
    db = open(db_path,"rb").read()
    return base64.b64encode(zlib.compress(db))

# ===============================================================

@jsonrpc_method('get_mapping_url(String, String)')  # secure
def get_mapping_url(request, context, mapping):
    context = check_context(context)
    _blob = check_mapping(mapping)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, mapping)

@jsonrpc_method('get_reference_url(String, String)') # secure
def get_reference_url(request, context, reference):
    context = check_context(context)
    _blob = check_reference(reference)
    ctx = rmap.get_cached_mapping(context)
    return create_url(ctx.observatory, reference)

#@jsonrpc_method('jsonapi.sayHello')
#def whats_the_time(request, name='Lester'):
#  return "Hello %s" % name

#@jsonrpc_method('jsonapi.gimmeThat', authenticated=True)
#def something_special(request, secret_data):
#  return {'sauce': ['authenticated', 'sauce']}
