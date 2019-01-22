"""Database models for crds_server.interactive."""
import os
import os.path
import sys
import re
import datetime
from collections import OrderedDict, defaultdict
import math
import uuid

# ============================================================================

from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from django.core import cache
from django.db import transaction

# ============================================================================

# Create your models here.
import crds
from crds import (timestamp, rmap, utils, refactor, log, data_file, uses, diff, checksum)
from crds import CrdsError
from crds.log import srepr

# ============================================================================

from crds_server.config import observatory as OBSERVATORY
from crds_server.config import table_prefix as TABLE_PREFIX
from crds_server import config

# ============================================================================

from . import common
from . import json_ext

from .common import FieldError, MissingInputError

# ============================================================================

observatory_module = utils.get_object("crds." + OBSERVATORY)

# ============================================================================

CRDS_CACHE = cache.caches["crds_cache"]

#  IMPORTANT:  crds_cached functions must cache on positional parameters only,
#  using keyword parameters in a cached function results in permanent misses.

def crds_cached(f):
    """Decorator to cache a function in the 'crds_cache'.
    This is distinct from 'default' because 'default' interacts with sessions
    and Django's own unit tests fail.
    """
    # @common.profile(f.__name__ + ".stats")
    def wrapper(*args, **keys):
        raw_key = __name__ + "_" + f.__name__ + "_" + str(args + tuple(sorted(keys.items())))
        raw_key = raw_key.replace("(","_").replace(")","_").replace("'","").replace(",","_").replace(" ","")
        key = utils.str_checksum(raw_key)
        val = retrieve_cache(key)
        if val is not None:
            log.verbose("crds_cached", f.__name__, raw_key, key, "HIT")
        else:
            val = f(*args, **keys)
            log.info("crds_cached", f.__name__, raw_key, key, "MISS")
            store_cache(key, val)
        return val
    wrapper.__doc__ = f.__doc__
    wrapper.__name__ = f.__name__
    return wrapper

def clear_cache():
    """Clear the crds core cache used for storing."""
    # log.info("Clearing Django crds_cache (nominally memcached).")
    CRDS_CACHE.clear()

# multi-chunk due to 1M limit in memcached and pymemcached and possibly Django

def store_cache(key, val, chunk_size=950000):
    """Store Python val into CRDS cache in multiple chunks at `key`."""
    # return CRDS_CACHE.set(key, val)
    with log.error_on_exception("store_cache failed", repr(key)):
        pick = json_ext.dumps(val)
        for i in range(0, len(pick), chunk_size):
            chunk_key = key + "_{:02d}".format(i//chunk_size)
            chunk_data = pick[i:i+chunk_size]
            CRDS_CACHE.set(chunk_key, chunk_data.encode("utf-8"))
            log.verbose("store_cache", chunk_key, len(chunk_data))

def retrieve_cache(key):
    """Retrieve Python val from CRDS cache in multiple chunks from `key`."""
    # return CRDS_CACHE.get(key)
    val = None
    with log.error_on_exception("retrieve_cache failed", repr(key)):
        i = 0
        pick = ""
        while 1:
            chunk_key = key + "_{:02d}".format(i)
            fetch = CRDS_CACHE.get(chunk_key)  # .decode("utf-8")
            if fetch is None:
                break
            pick += fetch
            i += 1
            log.verbose("retrieve_cache", chunk_key, len(fetch))
        if fetch is None and len(pick) == 0:
            return None
        val = json_ext.loads(pick)
    return val

# ============================================================================

OBSERVATORIES = ["hst", "jwst"]

INSTRUMENTS = sorted(observatory_module.INSTRUMENTS) # + crds.jwst...
try:
    INSTRUMENTS.remove("all")
except:
    pass

FILEKINDS   = sorted(observatory_module.FILEKINDS)   # + crds.jwst...
try:
    FILEKINDS.remove("all")
except:
    pass

FILEKIND_TEXT_DESCR = sorted(observatory_module.TEXT_DESCR.items())
EXTENSIONS  = sorted(observatory_module.EXTENSIONS)   # + crds.jwst...

# ============================================================================

class BlobField(object):
    """Basic properties for a field of a Blob."""
    def __init__(self, type, help, default, blank=True):
        self.type = type
        self.help = help
        self.default = default
        self.blank = blank

class FitsBlobField(BlobField):
    def __init__(self, fitskey, *args, **keys):
        self.fitskey = fitskey
        BlobField.__init__(self, *args, **keys)

# ============================================================================

class CrdsModel(models.Model):
    class Meta(object):
        abstract = True    # Collapse model inheritance for flat SQL tables
        
    name = models.CharField(max_length=64, default="", help_text="unique name of this model.",
                            blank=True)

    unicode_list = ["name"]
    repr_list = ["name"]
    model_fields = ["name"]
    model_titles = ["Name"]

    @property
    def fields(self):
        return self.model_fields

    def _repr(self, displayed=None):
        """Display values of fields in `self.repr_list` else display
        values of all fields in name-sorted order.
        """
        if displayed is None:
            displayed = self.repr_list or ["id"] + self.fields
        if "blob" in displayed:
            displayed.remove("blob")
        rep = self.__class__.__name__ + "(" 
        for field in displayed:
            try:
                value = str(getattr(self, field))
            except Exception:
                value = "FAILED"
            rep += field + "='" + value + "', "
        rep = rep[:-2] + ")"
        return rep
    
    def __repr__(self):
        return self._repr(self.repr_list)
    
    def __unicode__(self):
        """To support Django db admin views."""
        return self._repr(self.unicode_list)

    __str__ = __unicode__   # for Python-3

    @classmethod
    def get_or_create(cls, *args):
        """Get the model for `name`, or create it."""
        with transaction.atomic():
            name = "_".join(args)
            try:
                model = cls.objects.get(name=name)
            except ObjectDoesNotExist:
                model = cls(name=name)
            return model

    def save(self, *args, **keys):
        with transaction.atomic():
            super(CrdsModel, self).save(*args, **keys)

# ============================================================================

class CounterModel(CrdsModel):
    """The serial number counter for a single kind of file,  named:
            <observatory> _ <instrument> _ <filekind>
            
    Automatically generates a new counter if it doesn't already exist:
    use with care.
    """
    class Meta(object):
        db_table = TABLE_PREFIX + "_counters" 

    counter = models.IntegerField(default=0, help_text="Value of the counter.")
    
    repr_list = unicode_list = ["id", "name","counter"]
    
    @classmethod
    def next(cls, *args):
        """Return the next integer in the series identified by `args`,  
        which are nominally class, observatory, instrument, filekind.
        .e.g.  mapping, hst, acs, biasfile
               reference, jwst, miri, biasfile
        """
        model = cls.get_or_create(*args)
        model.counter += 1
        model.save()
        return model.counter

    @classmethod
    def last(cls, *args):
        """Like next,  but return the last number issued."""
        return cls.get_or_create(*args).counter

    @classmethod
    def set(cls, *args): 
        """Like next(),  but set the counter identified by args[:-1] to args[-1]
        """
        # nominally class, observatory, instrument, filekind, number
        num = int(args[-1])
        model = cls.get_or_create(*args[:-1])
        model.counter = num
        model.save()
    
    @classmethod
    def mirror(cls, filepath, *args):
        """Make filename counters reflect what is on the file system as files are added.
        
        counter_name_parts = args[:-1]
        existing_serial = args[-1]
        
        if existing_serial >= counter(args):  counter(args) = existing_serial + 1
        
        This is done rather than merely reflecting the file system so that serial
        numbers can be allocated simply without requiring that a real file or stub to
        be present,  as would be the case if the CRDS server did not have a complete
        copy of all CRDS references and mappings.
        """
        if not args[-1]:
            return
        try:
            existing_serial = int(args[-1])
        except Exception:
            existing_serial = 0
        model = cls.get_or_create(*args[:-1])
        if model.counter <= existing_serial:
            model.counter = existing_serial
            model.save()
            log.info("Advanced file counter for '%s' to '%05d' based on '%s'." % \
                     (model.name, model.counter, filepath))
            
def mirror_filename_counters(observatory, official_path):
    """As files are added,  make sure that the name serial number counters are consistent
    with the supplied `official name`.   This is particularly required for generated files
    which arrive with pre-assigned names.
    """
    if official_path.endswith(".cat"):
        serial = int(os.path.splitext(os.path.basename(official_path))[0].split("_")[-2])
        CounterModel.mirror(official_path, observatory, "delivery_id", serial)
    else:
        locator = utils.get_locator_module(observatory)
        try:
            # NOTE: HST CDBS filenames don't explicitly identify project or instrument,  so pluggable.
            path, observatory, instrument, filekind, serial, ext = locator.decompose_newstyle_name(official_path)
        except AssertionError:
            pass
        else:
            CounterModel.mirror(official_path, observatory, instrument, filekind, ext, serial)

# ============================================================================

@crds_cached
def get_bad_files(observatory):
    """Return the current list of blacklisted or rejected files."""
    log.info("Computing bad files list.")
    fileblobs = get_fileblob_map(observatory)
    # mappings are both blacklisted and rejected which will trigger a warning/error on use
    # leaf mappings are blacklisted and rejected.
    # ancestor mappings in blacklists are not rejected.
    # references are only rejected
    # to keep bad_files list small,  only include *rejected* files.
    # client-side,  checker must inspect current context for contained bad mappings, i.e. rejected files.
    bad_files = [ str(blob.name) for blob in list(fileblobs.values()) if blob.observatory==observatory and blob.rejected ]
    return sorted(bad_files)

# ============================================================================

CONTEXT_TYPES = ["operational", "edit", "versions"]

# operational == context in use by default (pipeline must sync)
# edit == default derivation point for future rules creation (can be overridden during submission)
# versions == defines context capable of handling all cal code version strings, probably last context

# "default" is synonymous with "edit", the suggested derivation point for edits.

class ContextModel(CrdsModel):
    """Keeps track of which mappings are the default."""
    class Meta(object):
        db_table = TABLE_PREFIX + "_contexts" 

    model_fields = repr_list = unicode_list = CrdsModel.model_fields + ["observatory", "kind", "context"]
    
    context = models.CharField(max_length=64, default="",
        help_text="name of .pmap assigned to for this kind of context.")
    
    @property
    def observatory(self):
        return self.context.split("_")[0].split(".")[0]

    @property
    def kind(self):
        return self.name.split("_")[1]
    
    def __init__(self, *args, **keys):
        # observatory="", kind="", context=""):
        super(ContextModel, self).__init__(*args, **keys)

    @classmethod
    def get_map(cls):   # XXX TODO observatory handling
        """Return the mapping { kind : context }"""
        return { blob.kind : blob.context for blob in cls.objects.all() }

def set_default_context(context, observatory=OBSERVATORY, state="edit", description="set by system",
                        skip_history=False):
    """Remember `context` as the default for `observatory` and `state`. 
     
    Update context history unless skip_history is True (for test setup speed).
    """
    
    assert context.endswith(".pmap"), "context must be a .pmap"
    assert state in CONTEXT_TYPES,  "Invalid context state: " + repr(state) + " should be in " + repr(CONTEXT_TYPES)
    log.info("Setting '{}' default '{}' context to '{}'".format(observatory, state, context))
    model = ContextModel.get_or_create(observatory, state, "context")
    model.context = context
    model.save()
    
    add_meta_event("Set default", srepr(state), "context for", 
                   repr(observatory), "to", srepr(context), "with skip_history =", skip_history)

    if skip_history:
        return

    # Create a context history record for this context switch.
    history = get_context_history(observatory=observatory, state=state)
    old_context = history[0].context if history else "none"
    if old_context != context or (rmap.is_mapping(context) and not history):
        new_hist = ContextHistoryModel()
        new_hist.description = description
        new_hist.context = context
        new_hist.state = state
        new_hist.start_date = datetime.datetime.now()
        new_hist.save()
        if state == "operational":
            fileblob_map = get_fileblob_map()
            update_activation_dates(context, new_hist.start_date, fileblob_map)
            update_file_states(context, fileblob_map)
            update_file_replacements(old_context, context, fileblob_map)
            
    clear_cache()
    # get_default_context(observatory=observatory, state=state)
    # get_bad_files(observatory)

def update_activation_dates(context, activation_date, fileblob_map=None):
    """Set the activation dates of files which are new in `context` to `activation_date`."""
    if fileblob_map is None:
        fileblob_map = get_fileblob_map()
    datestr = timestamp.format_date(activation_date)
    supported_files = _active_files(context)
    for fname, blob in list(fileblob_map.items()):
        if fname in supported_files:
            if blob.activation_date.year == DEFAULT_ACTIVATION_DATE.year:
                log.verbose("Setting activation date of '{}' to '{}'".format(fname, datestr))
                blob.thaw()
                blob.activation_date = timestamp.parse_date(activation_date)
                blob.save()

def update_file_states(new_context=None, fileblob_map=None):
    """Interpret the catalog link for all files which are in a transitory state."""
    if new_context is None:
        new_context = get_default_context(OBSERVATORY, "operational")
        log.info("Updating for operational files in", repr(new_context))
    if fileblob_map is None:
        fileblob_map = get_fileblob_map()
    active_files = _active_files(new_context)
    for fname, blob in list(fileblob_map.items()):
        if blob.state in TRANSITORY_STATES + ACTIVE_STATES:
            old_state = blob.state
            if fname in active_files or data_file.get_conjugate(fname) in active_files:
                state = "operational"
            elif old_state == "archived":
                state = "archived"   # was archived,  but not operational now == still archived.
            else:
                state = blob.interpret_catalog_link()
            if old_state != state:
                log.verbose("Changing state of '{}' from '{}' to '{}'".format(blob.name, old_state, state))
                _update_file_state(blob, state)
        elif blob.state in INACTIVE_STATES:
            log.info("Skipping", repr(blob.name), "in state", repr(blob.state))
        else:
            raise CrdsError("Unhandled file state for '{}' = '{}'".format(fname, blob.state))

def _update_file_state(blob, state):
    """Change the `blob` to `state`, thawing it first,  saving it.  Issue an info."""
    if blob.state != state:
        log.verbose("Changing state of '{}' to '{}'".format(blob.name, state))
        blob.thaw()
        blob.state = state
        blob.save()

def update_delivery_status():
    """Check to see if the un-archived files have been delivered to the archive yet.
    If so, update the archive state. 

    Used in jsonapi list_mappings service, requires speed,  assumes nominal system 
    state where deliveries are working.
    """
    blobs = get_fileblob_map(state__in = TRANSITORY_STATES)
    for blob in list(blobs.values()):
        blob.interpret_catalog_link()

def _active_files(context):
    """Return the set of all filenames referred to by `context`."""
    pmap = crds.get_cached_mapping(context)
    return set(pmap.mapping_names() + pmap.reference_names())

@utils.cached
def _all_activated_files():
    """Return the set of all files known to have ever been activated (used in operational context)."""
    all_files = set()
    for blob in get_context_history():
        if blob.state == "operational":
            log.info("Loading active files from", repr(blob.context))
            all_files = all_files.union(_active_files(blob.context))
    return all_files

def update_file_replacements(old_pmap, new_pmap, fileblob_map=None):
    """Given root mappings `old_pmap` and `new_pmap`, difference them and update the CRDS catalog
    for any files which are replaced by the transition from old to new.   This will set the reject 
    flag of replaced files,  and set their reject_by_filename name to the file which replaces them.
    """
    if old_pmap == "none":
        return
    if fileblob_map is None:
        fileblob_map = get_fileblob_map()
    with log.error_on_exception("failed setting file rejects based on context transition", 
                                repr(old_pmap), "-->", repr(new_pmap)):
        old_map = rmap.asmapping(old_pmap, cached="readonly")
        #  Recursively figure out all diffs between nested files in the pmaps
        diffs = old_map.difference(new_pmap)
        for d in diffs:
            if diff.diff_action(d) == "replace":
                old_rep, new_rep = diff.diff_replace_old_new(d)
                log.info("Setting replaced_by_filename for", repr(old_rep), "with replacement file", repr(new_rep))
                fileblob_map[old_rep].replaced_by_filename = new_rep
                fileblob_map[old_rep].save()

@crds_cached
def get_default_context(observatory, state):
    """Return the latest context which is in `state`."""
    assert observatory == OBSERVATORY, "Bad observatory for this server."
    assert state in CONTEXT_TYPES,  "Invalid context state: " + repr(state) + " should be in " + repr(CONTEXT_TYPES)
    return str(ContextModel.get_or_create(observatory, state, "context").context)

class ContextHistoryModel(CrdsModel):
    """Keeps track of interval at which the specified context was active and the reason for the switch."""
    class Meta(object):
        db_table = TABLE_PREFIX + "_context_history"
        ordering = ("start_date","context")

    model_fields = repr_list = unicode_list = ["observatory", "start_date", "context", "state", "description"]
    
    @property
    def observatory(self):
        return self.context.split("_")[0].split(".")[0]

    start_date = models.DateTimeField()

    context = models.CharField(max_length=64, default="",
        help_text="name of .pmap assigned to for this kind of context.")
    
    state = models.CharField(max_length=32, default="operational", choices=list(zip(CONTEXT_TYPES, CONTEXT_TYPES)))
    
    description = models.TextField( 
            help_text  = "Reason for the switch to this context.",
            default = "routine update")

    def __init__(self, *args, **keys):
        # observatory="", kind="", context=""):
        super(ContextHistoryModel, self).__init__(*args, **keys)
        
def get_context_history(observatory=OBSERVATORY, state="operational"):
    """Return the history models of the specified context,  in reverse order of start date."""
    return [o for o in ContextHistoryModel.objects.filter(state=state).reverse() if o.observatory == observatory]
    # return [o for o in ContextHistoryModel.objects.all().reverse()]

@crds_cached
def get_context_history_tuples(observatory):
    """Return the history for `observatory` in list of tuples form."""
    history = get_context_history(observatory)
    history_tuples = []
    for era in history:
        history_tuples.append((str(era.start_date).replace("T"," "), era.context, era.description))
    return history_tuples

def get_context_by_date(date, observatory=OBSERVATORY):
    """Return the name of the context associated with date for `observatory`."""
    history = get_context_history_tuples(observatory)
    return search_history(history, date)

def search_history(history, date):
    """Search a context `history` tuple list for the context corresponding to `date`.
    
    History should be sorted as from get_context_history_tuples().
    """
    dt = timestamp.reformat_date(date)
    i = 0
    while  i < len(history) and dt < history[i][0]:
        i += 1
    return str(history[i][1])

# ============================================================================

class BlobModel(CrdsModel):
    """A generic hybrid format which contains several fast static fields
    as well as a "blob" of slow fields which are easier to declare and
    don't change the database schema.
    """
    class Meta(object):
        abstract = True    # Collapse model inheritance for flat SQL tables

    model_fields = CrdsModel.model_fields + ["blob"]  # field directly in database
    model_titles = CrdsModel.model_titles + ["Blob"]
    
    blob_fields = {}  # field in database as part of blob
    exclude_from_info = ["blob"]    # not included in self.info()
    repr_list = None    # fields shown in __repr__ or ALL if None
    unicode_list = None  # fields shown in __unicode__ or ALL if None
    
    blob = models.TextField( 
            help_text  = "repr() of value of this blob,  probably repr(dict).",
            default = "{}")
    
    def __init__(self, *args, **keys):
        CrdsModel.__init__(self, *args, **keys)
        """
        for fieldname in self.blob_fields:
            setattr(self, fieldname, self.blob_fields[fieldname].default)
        for fieldname in keys:
            setattr(self, fieldname, keys[fieldname])
        """
 
    def save(self):
        try:
            old_blob = json_ext.loads(self.blob)
            old_blob = { name : old_blob[name] for name in self.blob_fields } # ditch fields no longer in model.
        except:
            old_blob = {}
        blob = {}
        for name in self.blob_fields:
            blob[name] = self.enforce_type(name, getattr(self, name, old_blob.get(name, self.blob_fields[name].default)))
        self.blob = json_ext.dumps(blob)
        super(BlobModel, self).save()
        clear_cache()
        
    def thaw(self):
        if hasattr(self, "_thawed"):
            return self
        self._thawed = True
        blob = json_ext.loads(self.blob)
        for name in self.blob_fields:
            setattr(self, name, blob.get(name, self.blob_fields[name].default))
        return self

    def _repr(self, displayed=None):
        self.thaw()
        return super(BlobModel, self)._repr(displayed)
    
    @property
    def fields(self):
        return sorted(list(self.model_fields) + 
                      list(self.blob_fields))

    def enforce_type(self, attr, value):
        """Ensure `value` meets the constraints for field `attr`.  Return
        a possibly coerced `value` if it's legal,  else raise an exception.
        """
        type_ = self.blob_fields[attr].type
        if not str(value).strip():
            if not self.blob_fields[attr].blank: 
                raise FieldError("Required field " + repr(attr) + " is blank.")
            else:
                return ""
        if isinstance(type_, str):   # treat str-types as regexes for value
            if re.match(type_, str(value)):
                return value
            else:
                raise FieldError("Value for " + repr(attr) + " of " + 
                                 repr(value) + " didn't match " + repr(type_))
        elif isinstance(type_, list): # treat lists as literal legal values
            if value in type_:
                return value
            else:
                raise FieldError("Value for " + repr(attr) + " of " + 
                                 repr(value) + " was not one of " + repr(type_))
        else: # try to use field type as a type converter
            try:
                return type_(value)
            except Exception:
                raise FieldError("Value for " + repr(attr) + " of " + 
                                 repr(value) + " not convertible to " + repr(type_))

    @classmethod
    def load(cls, name):
        """Load the blob named `name`.   Note that "anonymous" blobs cannot
        be load()'ed.   Uses select_for_update() if available to lock loaded object
        until saved, deleted, or out of scope, preventing race conditions due to
        "simultaneous" updates of the same object.
        """
        # select for update locks a model row until it is saved or rolled back.
        # if hasattr(cls.objects, "select_for_update"):  # requires Django > 1.4
        #    candidates = cls.objects.select_for_update().filter(name=name)
        #else:
        # XXX now select_for_update must be done inside a transaction.
        candidates = cls.objects.filter(name=name)            
        if len(candidates) == 0:
            raise LookupError("Couldn't find " + cls.__name__ + 
                              " named " + repr(name))
        elif len(candidates) > 1:
            raise RuntimeError("Found more than one " + cls.__name__ + 
                              " named " + repr(name))
        else:
            model = candidates[0]
            model.thaw()
            return model
    
    @classmethod
    def get(cls, id):
        model = cls.objects.get(id=id)
        model.thaw()
        return model
    
    @staticmethod    
    def _filter(cls, **matches):
        """Return list of Blobs of this `cls` which match filter `matches`."""
        filtered = []
        matches = dict(matches)  # copy
        model_filters = {}
        for key in list(matches.keys()):
            if key.split("__")[0] in cls.model_fields:
                model_filters[key] = matches.pop(key)
        for candidate in cls.objects.filter(**model_filters):
            candidate.thaw()
            for filter in matches:
                fval = getattr(candidate, filter, None)
                if isinstance(fval, (bool, int, float)):
                    if not matches[filter] == fval:
                        break
                else:
                    if not re.match(matches[filter], fval):
                        break
            else:
                filtered.append(candidate)
        return filtered
    
    @classmethod
    def filter(cls, **matches):
        return BlobModel._filter(cls, **matches)

    @classmethod
    def exists(cls, name):
        """Return True if `name` exists."""
        candidates = cls.filter(name=name)
        return len(candidates) >= 1

    @classmethod
    def dictionary(cls):
        """Return { name : blob } for all Blobs in this class."""
        d = {}
        for obj in cls.objects.all():
            d[obj.name] = obj
            obj.thaw()
        return d

    @property
    def info(self):
        """Return { field : value } for all the information in this Blob."""
        return { field.lower() : str(getattr(self, field)).lower() for field in self.fields
                 if field not in self.exclude_from_info }

# ============================================================================

# When last used,  the Mixin below was actually part of the FileBlob object.  It was removed to
# a mixin to reduce clutter...  but testing/usage is correspondingly weaker and suspect.

# The following three convenience functions were created at the time of the Mixin refactoring
# to systematize use patterns I normally used on-the-fly at the "./manage shell" command line
# working directly with the interactive.models module.

# The set of checks and repairs are not guaranteed to be complete or correct,  review them
# and run tests on mirrored catalogs before running them on the OPS server.

def check_defects(fields=None, files=None, verify_checksum=False):
    """Return a mapping { filename : (blob, defects), ...} corresponding to defects in the specified `fields` of 
    `files`.  Only FileBlob's containing defects are returned.
    
    IFF verify_checksum is True,  check the sha1sum in the FileBlob versus the cached file contents.  Slow.
    """
    map = get_fileblob_map()
    if isinstance(files, str):
        files = rmap.list_mappings(files, OBSERVATORY) + rmap.list_references(files, OBSERVATORY)
    if files:
        map = { name : blob for (name, blob) in list(map.items()) if name in set(files) }
    defect_map = { name :  (blob, blob.get_defects(fields=fields, verify_checksum=verify_checksum)) for (name, blob) in list(map.items()) }
    defect_map = { name : (blob, defects) for (name, (blob, defects)) in list(defect_map.items()) if defects }
    return defect_map

def repair_defects(defect_map, verbose=True):
    """Given a `defect_map` from check_defects(),  attempt to repair all the specified defects.
    
    Running check_defects() independently enables you to look it over before attempting any repairs.
    
    Return a repair_map of the form: { name : (blob, defects, repairs, failed), ... }.
    """
    repair_map = {}
    for name in defect_map:
        blob, defects = defect_map[name]
        repairs, failed = blob.repair_defects(defects)
        repair_map[name] = (blob, defects, repairs, failed)
        if verbose:
            for repair in repairs:
                print(name, repairs[repair])
            for failure in failed:
                print(name, failed[failure])
    clear_cache()
    return repair_map
    
def repair_defects_all(fields=None, files=None, verify_checksum=False, verbose=True):
    """In one operation,  detect and repair defects,  returning a repair_map as in repair_defects().
    
    Consider running check_defects() and repair_defcts() independently,  inspecting the defects
    manually before attempting repairs.
    """
    defect_map = check_defects(fields=fields, files=files, verify_checksum=verify_checksum)
    return repair_defects(defect_map, verbose=verbose)

class FileBlobRepairMixin(object):
    """This mixin defines methods for checking and repairing the FileBlob catalog defined below.
    
    These are used solely for catalog maintenance,  not for providing operational functions.
    
    Use these functions with extreme caution,  trying any repairs on a mirrored database before
    repeating the process on the OPS server.
    
    There's nothing sacred about these functions,  they were developed in response to real world
    issues with the operational catalogs.   Review the check and repair for any field you wish to
    repair carefully.
    """
    
    bad_field_checks = {
        "uploaded_as" : lambda self: not self.uploaded_as,
        "blacklisted" : lambda self: self.blacklisted_by and not self.blacklisted,
        "size" : lambda self: self.size in [-1, 0] or self.size != self.compute_size(),
        "sha1sum" : lambda self: self.sha1sum == "none",
        "delivery_date" : lambda self: self.delivery_date > self.activation_date and self.activation_date >= START_OF_CRDS,
        "activation_date": lambda self: self.state in ["archived", "operational"] and \
                                    self.activation_date == DEFAULT_ACTIVATION_DATE and self.name in _all_activated_files(),
        "useafter_date" : lambda self: self.useafter_date_str.strip().upper() in ["", "NONE"] and self.type != "mapping",
        "type" : lambda self: not self.type,
        "observatory": lambda self: self.observatory not in OBSERVATORIES,
        "instrument": lambda self:  (((not self.name.endswith(".pmap")) and self.instrument not in INSTRUMENTS) or 
                                     (self.name.endswith(".pmap") and self.instrument != "")),
        "filekind": lambda self:  (((not self.name.endswith((".pmap",".imap"))) and self.filekind not in FILEKINDS) or
                                   (self.name.endswith((".pmap",".imap")) and self.filekind != "")),

        "comment" : lambda self: self.type == "reference" and self.comment.lower() in ["", "none", "undefined"],
        "history" :  lambda self : self.type.lower() == "reference" and self.history in ["none","NONE","None", None, ""],
        "description" : lambda self : self.type.lower() == "reference" and self.description in ["none", "NONE", "None", None, ""],

        "pedigree" : lambda self: self.type == "reference" and not self.pedigree and \
            not re.match(r"\w+\.r[0-9][hd]", self.name),
        "deliverer_user" : lambda self: not self.deliverer_user,
        "deliverer_email" : lambda self: not self.deliverer_email,
        "creator_name" : lambda self: not self.creator_name,
        "mapping_name_field": lambda self: rmap.is_mapping(self.name) and not self.name == rmap.fetch_mapping(self.name).name,
    }
    
    def get_defects(self, verify_checksum=False, fields=None):
        """Check `self` and return a list of problems.   See therapist."""
        self.thaw()
        defects = []
        for field in fields or self.bad_field_checks:
            try:
                if self.bad_field_checks[field](self):
                    try:
                        defects.append("BAD {} = '{}'".format(field, getattr(self, field)))
                    except:
                        defects.append("BAD {}".format(field))
            except Exception as exc:
                defects.append("BAD {} defect test failed: {}".format(field, str(exc)))
        if verify_checksum and not self.checksum_ok:  # slow
            defects.append("BAD sha1sum = '{}' vs. computed = '{}'".format(self.sha1sum, self.compute_checksum()))
        return defects

    @property
    def has_defects(self):
        return bool(len(self.get_defects()))
    
    def repair_defects(self, defects=None):
        """Attempt to automatically fix list of `defects` in `self`."""
        self.thaw()
        if defects is None:
            defects = self.get_defects()
        repairs = {}
        failed = {}
        for defect in defects:
            field = defect.split()[1]  # skip BAD
            fixer = getattr(self, "repair_" + field, None)
            if fixer:
                try:
                    old = getattr(self, field)
                except:
                    old = "undefined for this fixer"
                try:
                    rval = fixer()
                    try:
                        new = getattr(self, field)
                    except:
                        new = rval
                    if old != new:
                        repairs[field] = "REPAIRED '{}' from '{}' to '{}'".format(field, old, new)
                    else:
                        raise RuntimeError("no change from fixer")
                except Exception as exc:
                    failed[field] = "failed repairing '{}' from '{}' exception: '{}'".format(field, old, str(exc))
            else:
                failed[field] = "NO FIXER for '{}'.".format(field)
        if repairs:
            self.save()
        return repairs, failed
    
    def repair_blacklisted(self):
        """If the fileblob has blacklisted_by files,  then it should have it's blacklisted flag set True."""
        self.blacklisted = len(self.blacklisted_by) > 0

    def repair_mapping_name_field(self):
        """Fix the mapping header name field to be consistent with the blob name name and path."""
        mapping = rmap.fetch_mapping(self.name)
        mapping.header["name"] = str(self.name)
        mapping.write(self.pathname)
        self.repair_size()
        self.repair_sha1sum()
        return self.name

    def repair_uploaded_as(self):
        frompath, topath = self.uploaded_as, None
        if os.path.exists(self.pathname):
            self.uploaded_as = os.path.basename(self.pathname)
            return 
        else:
            return "failed repairing uploaded_as='{}'".format(frompath)

    def repair_type(self):
        self.type = "mapping" if rmap.is_mapping(self.name) else "reference"
        
    def repair_size(self):
        self.size = self.compute_size()
            
    def repair_sha1sum(self):
        self.sha1sum = self.compute_checksum()
        
    def repair_observatory(self):
        self.observatory = utils.file_to_observatory(self.pathname)
        
    def repair_instrument(self):
        self.instrument = utils.get_file_properties(utils.file_to_observatory(self.pathname), self.pathname)[0]
        
    def repair_filekind(self):
        self.filekind = utils.get_file_properties(utils.file_to_observatory(self.pathname), self.pathname)[1]
        
    def repair_aperture(self):
        self.set_metadata_field("aperture", ["APERTURE", "META.APERTURE.NAME", "APERNAME"])  # aperture_keyword from FileBlobModel multiple inheritance
        
    def repair_useafter_date(self):
        self.set_metadata_field("useafter_date", ["USEAFTER", "META.USEAFTER"], 
                                timestamp.parse_date, default=DEFAULT_USEAFTER_DATE)

    def repair_reference_file_type(self):
        self.set_metadata_field("reference_file_type", ["REFTYPE", "META.REFTYPE"])

    def repair_pedigree(self):
        self.set_metadata_field("pedigree", ["PEDIGREE", "META.PEDIGREE"])
        if self.observatory == "jwst" and not self.pedigree:
            log.warning("Using JWST default PEDIGREE of DUMMY.")
            self.pedigree = "DUMMY"

    def repair_comment(self):
        self.set_metadata_field("comment", ["DESCRIP", "DESCRIPTION", "META.DESCRIPTION"])

    def repair_delivery_date(self):
        delivery_date = [ audit.date for audit in AuditBlob.filter(filename=self.name) 
                          if audit.action in ["mass import", "submit file", "batch submit"]][0]
        self.delivery_date = delivery_date

    def repair_history(self):
        self.set_metadata_field("history", ["HISTORY", "META.HISTORY",], condition=False)

    def repair_activation_date(self):
        for hist in reversed(get_context_history()):  # find earliest pmap which uses mapping
            pmap = crds.get_cached_mapping(hist.context)
            names = pmap.mapping_names() + pmap.reference_names()
            if self.name in names:
                self.activation_date = hist.start_date
                break

    if OBSERVATORY == "hst":

        bad_field_checks["aperture"] = lambda self: self.aperture=="none" and self.type != "mapping" and self.instrument != "wfpc2"

    elif OBSERVATORY == "jwst":  #===========================================================

        pass
    
# ============================================================================

PEDIGREES = ["INFLIGHT", "GROUND", "DUMMY", "MODEL"]   # note: INFLIGHT include date
CHANGE_LEVELS = ["SEVERE", "MODERATE", "TRIVIAL"]

FILE_STATUS_MAP = OrderedDict([
    ("uploaded", "orange"),   # On the server,  still temporary
    ("delivered", "blue"),    # Delivered to downstream systems, pending archive
    ("submitted", "orange"),  # In found by pipeline poller
    ("archiving", "blue"),    # Being processed by pipeline poller
    ("archived", "darkgreen"),    # Archived and in use.
    ("operational", "darkgold"), # In operational use in the pipeline.
    ("cancelled", "red"),      # submission cancelled by submitter
    ("archiving-failed", "red"),   # delivery to archive failed in CRDS pipeline.
    ("bad", "red")  # blacklisted or rejected
])

# In CRDS but on the way into the archive.
TRANSITORY_STATES = ["delivered","submitted","archiving", "archiving-failed"]

# Either obsolete but retained in CRDS and the archive or in operational use in the pipeline.
ACTIVE_STATES = ["archived", "operational"]

# Eventually,  such files are useable and can be referred to by mappings accepted now
USEABLE_STATES = ACTIVE_STATES + TRANSITORY_STATES
           
INACTIVE_STATES = ["uploaded", "cancelled"]

ALL_STATES = TRANSITORY_STATES + ACTIVE_STATES + INACTIVE_STATES
FILE_STATES = list(FILE_STATUS_MAP.keys())

assert len(ALL_STATES) == len(set(ALL_STATES)), "Doubly-assigned or duplicate state in FileBlob state declarations."
assert len(FILE_STATES) >= len(ALL_STATES),  "Uncategorized state in FileBlob state declarations."

DEFAULT_ACTIVATION_DATE =  datetime.datetime(2050, 1, 1, 0, 0)
DEFAULT_USEAFTER_DATE = datetime.datetime(1900, 1, 1, 0, 0)
START_OF_CRDS = datetime.datetime(2013, 8, 1, 0, 0)

def SimpleCharField(choice_list, help_text, default):
    """CharField with automatic field sizing using next power-of-2 of max length + simplified choice spec."""
    length = 0
    for choice in choice_list:
        length = max(length, len(choice))
    max_length = int(2**(math.ceil(math.log(length,2))+1))    
    return models.CharField( 
        max_length=max_length,
        choices = list(zip(choice_list, choice_list)),
        help_text = help_text,
        default = default)

class FileBlob(BlobModel, FileBlobRepairMixin):
    """Represents a delivered file,  either a reference or a mapping."""

    class Meta(object):
        db_table = TABLE_PREFIX + "_catalog" # rename SQL table from interactive_fileblob
    
    # attribute names of model data
    model_fields = BlobModel.model_fields + \
        ["state", "blacklisted", "rejected", "observatory", "instrument", "filekind", 
         "type", "derived_from", "sha1sum", "delivery_date", "activation_date", "useafter_date",
         "change_level", "pedigree", "reference_file_type", "size", "uploaded_as", "creator_name",
         "deliverer_user", "deliverer_email", "description", "catalog_link",
         "replaced_by_filename", "comment", "aperture", "history"]
    
    # corresponding table column titles
    model_titles = BlobModel.model_titles + \
        ["State", "Blacklisted", "Rejected", "Observatory", "Instrument", "Filekind", 
         "Type", "Derived From", "Sha1sum", "Delivery Date", "Activation Date", "Useafter Date",
         "Change Level", "Pedigree", "File Type", "Size", "Upload As", "Creator Name",
         "Deliverer", "Deliverer Email", "Description", "Catalog Link",
         "Replaced By", "Descrip", "Aperture", "History"]

    # Comment/comment renamed re-labeled as Descrip
    
    # table fields and titles for use in web displays which combine mappings with catalog
    fusion_fields = [ field.replace("_date", "_date_str") for field in model_fields ]
    fusion_items = tuple(item for item in zip(fusion_fields, model_titles) 
                         if item[0] not in ["name", "blob"])
    
    repr_list = unicode_list = ["id", "name", "type", "instrument", "filekind", "state", 
                                "blacklisted", "rejected", "change_level", "available"]
        
    # -------------------------------------------------------------------------------------------------------------
    
    exclude_from_info = BlobModel.exclude_from_info + \
        ["pathname","creator","deliverer", "deliverer_email","catalog_link"]

    state = SimpleCharField( ALL_STATES,
        "operational status of this file.", "delivered" )

    blacklisted = models.BooleanField(
        default=False, 
        help_text="If True, this file should not be used, transitive to referencers.")
    
    rejected = models.BooleanField(
        default=False, 
        help_text="If True, this file should not be used, non-transitive.")
    
    observatory = SimpleCharField( OBSERVATORIES,
        "observatory associated with file", OBSERVATORY)
    
    instrument = SimpleCharField(INSTRUMENTS + ["unknown"], 
        "instrument associated with file", "")
    
    filekind = SimpleCharField(FILEKINDS + ["unknown"], 
        "dataset keyword associated with this file", "")

    type = SimpleCharField( ["reference","mapping"],
        "type of file,  reference data or CRDS rule or context", "")
    
    derived_from = models.CharField(max_length=128, default="none",
        help_text = "Previous version of this file this one was based on.")

    sha1sum = models.CharField(max_length=40,
        help_text = "Hex sha1sum of file contents as delivered", default="none")
    
    delivery_date = models.DateTimeField(
        default=datetime.datetime.now, help_text="Date file was received by CRDS.")
    
    activation_date = models.DateTimeField(
        default=DEFAULT_ACTIVATION_DATE, help_text="Date file first listed in an operational context.")
    
    useafter_date = models.DateTimeField(
        default=DEFAULT_USEAFTER_DATE, help_text="Dataset date after which this file is a valid reference.")

    change_level = SimpleCharField(
        CHANGE_LEVELS,  "Affect of changes in this file relative to preceding version on science results", "SEVERE")
    
    pedigree = models.CharField(
        max_length=80, blank=True, default="", help_text="From PEDIGREE, reference characterization, e.g. GROUND 16/07/2008 16/07/2010")
    
    reference_file_type = models.CharField(
        max_length=80, blank=True, default="", help_text="From REFTYPE,  description of file type.")
    
    size = models.BigIntegerField(default=-1, help_text="size of file in bytes.")
    
    uploaded_as = models.CharField(
        max_length=80,  blank=True, default="", help_text="original upload filename")
    
    creator_name = models.CharField(
        max_length=80, blank=True, default="", help_text="person who made this file,  possibly/likely not the submitter", )
    
    deliverer_user = models.CharField(
        max_length=80, blank=True, default="", help_text="username who uploaded the file",)
    
    deliverer_email = models.CharField(
        max_length=80, blank=True, default="", help_text="person's e-mail who uploaded the file",)

    description = models.TextField(
        blank=True, default="none", help_text="Brief rationale for changes to this file.",)
    
    catalog_link = models.CharField(
        max_length=128, blank=True, default="", help_text="",)

    replaced_by_filename = models.CharField(
        max_length=128, blank=True, default="", help_text="",)
    
    comment = models.TextField(
        blank=True, default="none", help_text="from DESCRIP keyword of reference file.",)
    
    aperture = models.CharField(
        max_length=80, blank=True, default="none", help_text="from APERTURE keyword of reference file.",)

    history = models.TextField(
        blank=True, default="none", help_text="History extracted from reference file.")
    
    # ===============================

    @property
    def activation_date_str(self):
        return self._repr_date(self.activation_date)

    @property
    def delivery_date_str(self):
        return self._repr_date(self.delivery_date)

    @property
    def useafter_date_str(self):
        return self._repr_date(self.useafter_date)

    

    def _repr_date(self, dateobj):
        """Clean up dates for web display,  replacing bogus defaults for uninitialized dates
        (reasonable for some purposes, arguably confusing on pages) with the value N/A.

        Return a string instead of an object,  formatted to seconds resolution.
        """
        if dateobj in [DEFAULT_ACTIVATION_DATE, DEFAULT_USEAFTER_DATE]:
            datestr = "N/A"
        else:
            datestr = timestamp.format_date(dateobj).split(".")[0]   # YYYY-MM-DD HH:MM:SS
        return datestr

    

    # ===============================

    @property
    def blacklisted_by(self):
        if self.type != "mapping":
            return []
        nested_mappings  = crds.get_pickled_mapping(self.name).mapping_names()  # reviewed
        return [str(blob.name) for blob in FileBlob.filter(rejected=True) if blob.name in nested_mappings]

    # ===============================

    blob_fields = dict()

    @property
    def pathname(self):   # assume server has standard cache layout
        return str(rmap.locate_file(self.name, observatory=self.observatory))
    
    @property
    def is_bad_file(self):
        """Return the 'reject state' of this file,  either True or False."""
        return self.state in INACTIVE_STATES or self.blacklisted or self.rejected
    
    @property
    def available(self):
        """Return True if this file is allowed to be distributed now."""
        # TODO add general_availabilty_date....
        if self.state in TRANSITORY_STATES:
            self.interpret_catalog_link()
        return self.state in config.CRDS_DISTRIBUTION_STATES # and not self.is_bad_file
    
    @property
    def moniker(self):
        try:
            return repr(self.uploaded_as) + " --> " + repr(self.name)
        except:
            return "FileBlob-" + str(self.id)

    def init_metadata_fields(self):
        """Extract metadata from the cataloged file and store it in the model.  Use the 
        value from the first keyword found.
        """
        self.set_metadata_field("pedigree", ["PEDIGREE", "META.PEDIGREE",])
        self.set_metadata_field("reference_file_type", ["REFTYPE", "META.REFTYPE",])
        self.set_metadata_field("useafter_date", ["USEAFTER", "META.USEAFTER",], timestamp.parse_date, default=DEFAULT_USEAFTER_DATE)
        self.set_metadata_field("comment", ["DESCRIP", "DESCRIPTION", "META.DESCRIPTION"], condition=False) # displayed as DESCRIPTION, stored as comment in models
        self.set_metadata_field("aperture", ["APERTURE", "META.APERTURE.NAME", "APERNAME"])
        self.set_metadata_field("history", ["HISTORY", "META.HISTORY",], condition=False)

    def set_metadata_field(self, model_field, keywords, sanitizer=lambda x: x, condition=True, default="none"):
        """Set `model_field` to the first of `keywords` found, optionally santizing the value, or
        `condition`ing the value.
        """
        try:
            value = self.get_one_of_metadata_field(keywords, condition, default)
        except Exception as exc:
            value = default
            log.error("Setting field '%s' for '%s' to default '%s' since fetch failed: '%s'" % (model_field, (self.uploaded_as, self.name), default, exc))
        else:
            value = sanitizer(value)
            log.info("Setting field '%s' for '%s' to '%s'." % (model_field, (self.uploaded_as, self.name), value))
        setattr(self, model_field, value)

    def get_one_of_metadata_field(self, keywords, condition, default):
        """Search the file corresponding to `self` for the first value of a
        keyword in `keywords` that is not None and optionally `condition` the
        value before returning it.  Return None if no keyword value is found.
        """
        filename = self.uploaded_as or self.name
        if data_file.is_geis_data(self.pathname):
            read_from = self.pathname[:-1] + "h"
        else:
            read_from = self.pathname
        for keyword in keywords:
            with log.error_on_exception("Fetching keyword", srepr(keyword), "from", srepr(filename)):
                val = data_file.getval(read_from, keyword, condition=condition)
                if val != "UNDEFINED":
                    return val
        return default

    def add_slow_fields(self, allow_duplicates=False, sha1sum=None):
        """Add catalog fields from this file which potentially take a long time to add,  like
        `sha1sum` which may be passed as a pre-existing value.   Optionally reject
        duplicate files identified by sha1sums if `allow_duplicates` is False. 

        (Duplicate file submissions are a fairly common mistake, don't remove
        without replacing.)
        """
        self.thaw()
        log.info("Adding slow fields for",  self.moniker, repr(locals()))
        if self.type == "reference":
            self.init_metadata_fields()
        self.sha1sum = sha1sum or self.compute_checksum()
        self.blacklisted = len(self.blacklisted_by) > 0
        self.save()
        try:
            # Give GEIS data a "pass" because evidently many diffs are header portion only.
            if not allow_duplicates or not data_file.is_geis_data(self.name):
                self.check_unique_sha1sum()
        except CrdsError:
            self.destroy()
            raise

    def check_unique_sha1sum(self):
        matches = self.__class__.filter(sha1sum=self.sha1sum)
        for m in matches:
            if m.name != self.name:
                others = ", ".join([repr(str(x.name)) for x in matches if str(x.name) != str(self.name)])
                raise CrdsError("Submitted file '%s' is identical to existing files: %s" % (self.uploaded_as, others))

    def compute_checksum(self):
        try:
            checksum = utils.checksum(self.pathname)
            log.info("Computed checksum for", repr(self.moniker), "as", repr(checksum))
            return checksum
        except Exception as exc:
            log.error("Computing sha1sum of", repr(self.moniker), "failed:", str(exc))
            return "checksum failed: " + str(exc)

    @property
    def checksum_ok(self):
        return self.compute_checksum() == self.sha1sum
    
    @classmethod
    def new(cls, observatory, upload_name, permanent_location, 
            creator_name, deliverer_user, deliverer_email, description, 
            change_level="SEVERE", state="submitted", derived_from="(no predecessor)"):
        """Create a new FileBlob or subclass."""
        blob = cls()
        blob.observatory = observatory
        blob.uploaded_as = upload_name
        if rmap.is_mapping(permanent_location):
            blob.type = "mapping"
        else:
            blob.type = "reference"
        blob.name = os.path.basename(permanent_location)
        blob.creator_name = creator_name
        blob.deliverer_user = deliverer_user
        blob.deliverer_email = deliverer_email
        blob.description = description
        # blob.delivery_date = timestamp.now()
        # blob.activation_date = blob.useafter_date = DEFAULT_ACTIVATION_DATE
        try:
            instrument, filekind = utils.get_file_properties(observatory, permanent_location)
            blob.instrument = instrument
            blob.filekind = filekind
        except Exception as exc:
            log.warning("Adding file with instrument and filekind UNKNOWN for file", 
                        repr(permanent_location), ":", str(exc))
            blob.instrument = blob.fileind = "unknown"

        blob.derived_from = derived_from
        
        blob.size = blob.compute_size()

        # These need to be checked before the file is copied and the blob is made.
        if not rmap.is_mapping(upload_name):
            blob.change_level = change_level

        blob.state = state
        
        blob.save()
        
        return blob

    @property
    def filename(self):
        return os.path.basename(self.pathname)
    
    def compute_size(self):
        """Determine the size of this file."""
        with log.error_on_exception("Computing size of", self.moniker):
            return os.stat(self.pathname).st_size
        return -1
    
    @property
    def status(self):
        """status is a kind of summary of state and other variables,  particularly archiving."""
        if self.is_bad_file:
            return "bad"    # rejected *or* blacklisted
        elif self.state in TRANSITORY_STATES:
            return self.interpret_catalog_link()
        else:
            return self.state
    
    def interpret_catalog_link(self):
        """Based on the current name of the catalog link that delivered this file,  determine the
        status of the archiving process.
        """
        self.thaw()
        
        # links from mirrored servers reflect paths on the original file system.  
        # correct the abspath to where delivered catalogs live on this system.
        catalog_link = os.path.join(config.CRDS_DELIVERY_DIR, os.path.basename(self.catalog_link))
        
        if not self.catalog_link:  # initial mass imported files never delivered
            return "archived"
        elif os.path.exists(catalog_link):    
            # CRDS has made catalog and files available for archiving
            return "delivered"
        elif os.path.exists(catalog_link + "_SUBMIT") or os.path.exists(catalog_link + "_submit"): 
            # found by the DMS CRDS pipeline poller
            return "submitted"
        elif os.path.exists(catalog_link + "_PROC") or os.path.exists(catalog_link + "_proc"): 
            # being processed by the DMS CRDS pipeline
            return "archiving"
        elif os.path.exists(catalog_link + "_ERROR") or os.path.exists(catalog_link + "_error"):
            # delivery failed and CRDS needs to take action
            return  "archiving-failed"
        else:
            self.state = "archived"
            self.save()
            return self.state

    @property
    def status_class(self):
        return FILE_STATUS_MAP[self.status]
    
    @property
    def extension(self):
        parts = os.path.splitext(self.filename)
        return parts[-1]
    
    def destroy(self):
        """Destroy this FileBlob and it's associated file.   This
        cannot be revoked and should *ONLY* be called as part of cleanup for
        a failed multi-part file submission.
        """
        self.thaw()
        with log.error_on_exception("Problem destroying", repr(self.moniker), ":", self.pathname):
            log.info("DESTROYING", self.moniker, ":", repr(self.pathname))
            assert "/grp/hst/cdbs" not in self.pathname,  "Can't delete borrowed CDBS file."
            self.delete()
            os.remove(self.pathname)

    @property
    def collisions(self):
        """A list of other files derived from the same source file...  possibly bad."""
        # include file.state == "uploaded",  those pending confirmation.
        return [col.name for col in BlobModel._filter(FileBlob, derived_from=self.derived_from) 
                if col.name != self.name and self.derived_from != "none" and not "generated" in self.derived_from ]

    # Hokeyness because BlobModel doesn't actually have .objects because it
    # it is abstract... so normal class method inheritance techniques fail.
    @classmethod
    def filter(cls, include_uploaded=False, **matches):  # omit "uploaded" files from filter result
        if include_uploaded:
            return BlobModel._filter(FileBlob, **matches)
        else:
            return [file_ for file_ in BlobModel._filter(FileBlob, **matches) if file_.state != "uploaded"]

# ============================================================================

def add_crds_file(observatory, upload_name, permanent_location, 
            deliverer, deliverer_email, description,
            change_level="SEVERE", add_slow_fields=True,
            creator_name="unknown", state="submitted", update_derivation=True,
            allow_duplicates=False, sha1sum=None):
    "Make a database record for this file.  Track the action of creating it."""
    if rmap.is_mapping(permanent_location):
        log.info("Adding", repr(upload_name), "as", repr(permanent_location))
        with log.warn_on_exception("Failed updating checksum on", repr(permanent_location)):
            os.chmod(permanent_location, int("644", 8))
            checksum.update_checksum(permanent_location)
        if update_derivation:
            derived_from = refactor.update_derivation(permanent_location)   # XXX mutate mapping file!
        else:  # ensure the name inside the mapping is consistent with permanent location.
            mapping = rmap.fetch_mapping(permanent_location)
            derived_from = mapping.derived_from
            actual_name = os.path.basename(permanent_location)
            if mapping.header["name"] != actual_name:
                with log.warn_on_exception("failed setting mapping header name of", repr(permanent_location)):
                    mapping.header["name"] = actual_name
                    mapping.write(permanent_location)   # XXX mutate mapping file!
    else:
        derived_from = "none"
    
    blob = FileBlob.new(
        observatory, upload_name, permanent_location, 
        creator_name, deliverer, deliverer_email, description,
        change_level=change_level, state=state, derived_from=derived_from)

    # note that modifying derivation fields changes the sha1sum of mappings.
    if add_slow_fields:
        blob.add_slow_fields(allow_duplicates=allow_duplicates, sha1sum=sha1sum)

    # Set file permissions to read only.
    try:
        os.chmod(permanent_location, 0o444)
    except:
        pass
    return blob

def file_exists(filename, observatory=OBSERVATORY):
    """Return True IFF `filename` is a known CRDS reference or mapping file."""
    try:
        return FileBlob.load(filename)
    except Exception:
        return None

def get_fileblob_map(observatory=OBSERVATORY, **keys):
    """Return a query set for all the file blobs belonging to observatory.   It's
    vastly faster to check for existence against this map than using file_exists(),
    probably because it's fewer SQL queries.
    """
    return { str(blob.name) : blob for blob in FileBlob.objects.filter(observatory=observatory, **keys) }

def set_state(filename, state):
    blob = FileBlob.load(filename)
    blob.state = state
    blob.save()
    
def get_state(filename):
    return FileBlob.load(filename).state

def known_files():
    return [f.name for f in FileBlob.objects.all()]

# ============================================================================

def transitive_blacklist(blacklist_root, badflag, observatory=OBSERVATORY):
    """Blacklist `blacklist_root` and all the files referring to it according
    to `badflag` as "ok" or "bad".
    """
    assert badflag in ["bad","ok"], "Invalid blacklist badflag=" + repr(str(badflag))
    # Determine files which indirectly or directly reference `blacklist_root`
    uses_files = uses.uses([blacklist_root], observatory)

    all_blacklisted = [blacklist_root] + uses_files

    for also_blacklisted in all_blacklisted:
        log.verbose("Also blacklisting ", repr(also_blacklisted), "as", badflag)
        try:
            if badflag == "bad":
                blacklist(also_blacklisted)
            elif badflag == "ok":
                unblacklist(also_blacklisted)
        except Exception as exc:
            log.warning("Blacklist operation failed: ", str(exc))

    return all_blacklisted
    
def blacklist(blacklisted):
    """Mark the file `blacklisted` as bad because of its reference to file
    `blacklisted_by`.
    """
    fileblob = FileBlob.load(os.path.basename(blacklisted))
    fileblob.blacklisted = True
    fileblob.save()
    
def unblacklist(blacklisted):
    """Remove blacklisting of file `blacklisted` on behalf of file
    `blacklisted_by`.
    """
    fileblob = FileBlob.load(os.path.basename(blacklisted))
    # Only remove blacklisting if there are no remaining bad references.
    if not fileblob.blacklisted_by:
        fileblob.blacklisted = False
        fileblob.save()
    
def set_reject(rejected_filename, rejected_bool):
    """Mark `rejected_filename` as rejected(True) or usable(False),  non-transitively."""
    assert isinstance(rejected_bool, bool), "Invalid reject state,  must be a bool."
    log.info("Setting reject flag of", repr(rejected_filename), "to", rejected_bool)
    fileblob = FileBlob.load(os.path.basename(rejected_filename))
    fileblob.rejected = rejected_bool
    fileblob.save()

# ============================================================================

AUDITED_ACTIONS = [
    "mass import", "submit file", "blacklist", "new context", "batch submit", "set default context",
    "delete references", "add references", "add_files tool",
    ]

class AuditBlob(BlobModel):
    """Maintains an audit trail of important actions indicating who did them,
    when, and why.
    """
    class Meta(object):
        db_table = TABLE_PREFIX + "_actions" # rename SQL table from interactive_fileblob
        
    user = models.CharField(max_length=64, default="", help_text="user who performed this action")
    date = models.CharField(max_length=26, default="", help_text="date of this action")
    action = SimpleCharField( AUDITED_ACTIONS, "name of action performed", "" )
    filename = models.CharField(max_length=64, default="", help_text="unique name of this model.")
    observatory = models.CharField(max_length=8, default=OBSERVATORY, help_text="observatory this action applied to.")
    instrument = models.CharField(max_length=32, default="", help_text="instrument this action applied to.", blank=True)
    filekind = models.CharField(max_length=32, default="", help_text="filekind this action applied to.", blank=True)
    why = models.TextField(help_text="reason this action was performed", default="", blank=True)
    details = models.TextField(help_text="supplementary info", default="", blank=True)

    model_fields = BlobModel.model_fields + ["user", "date", "action", "filename", "observatory", "instrument", "filekind",
                                             "why", "details"]

    blob_fields = dict(
        # User supplied fields
        # user = BlobField(str, "user performing this action", ""),
        # date = BlobField(str, "date action performed", ""),
        # action = BlobField(AUDITED_ACTIONS,"name of action performed", ""),        
        # filename = BlobField("^[A-Za-z0-9_./]*$","file affected by this action", "None"),
        # observatory = BlobField(OBSERVATORIES, "associated observatory", ""),
        # instrument = BlobField(INSTRUMENTS + ["unknown"], "associated instrument", ""),
        # filekind = BlobField(FILEKINDS + ["unknown"], "associated filekind", ""),
        # why = BlobField(str, "reason this action was performed",""),
        # details = BlobField(str, "supplementary info", ""),
    )
    
    repr_list = unicode_list = ["date", "filename", "action", "user", "instrument", "filekind", "why", "details"]
    unicode_list = ["date", "action", "user", "filename", "why", "details"]
    
    @classmethod
    def new(cls, user, action, affected_file, why, details, 
            observatory=None, instrument="unknown", filekind="unknown", date=None):
        """Save a record of an action in the database."""
        blob = cls()
        blob.user = user
        blob.action = action
        blob.filename = affected_file
        blob.why = why
        blob.details = str(details)
        if date is None:
            date = timestamp.now()
        blob.date = date
        blob.observatory = observatory or OBSERVATORY
        if instrument == "unknown" or filekind == "unknown":
            blob.set_file_properties()
        blob.save()
        return blob
    
    def set_file_properties(self):
        """Base on self.filename,  set self.instrument and self.filekind."""
        try:
            instrument, filekind = utils.get_file_properties(self.observatory, self.filename)
            self.instrument = instrument
            self.filekind = filekind
            return True
        except Exception:
            return False
    
    def repair(self):
        """Repair invalid fields of `self` if possible."""
        repaired = False
        self.thaw()
        if "unknown" in [self.instrument, self.filekind]:
            repaired = repaired or self.set_file_properties()
        if repaired:
            log.info("Repairing AuditBlob", repr(self.id), "for file", repr(self.filename))
            self.save()
        return repaired

    @property
    def fileblob(self):
        """The FileBlob for the filename associated with this AuditBlob."""
        if not hasattr(self, "_fileblob"):
            self._fileblob = FileBlob.load(self.filename)
        return self._fileblob
    
    @classmethod
    def delivery(cls, filename):
        """Return the AuditBlob associated with delivering `filename`."""
        for audit in cls.filter(action="deliver"):
            if filename in audit.details:
                return [audit]
        else:
            return []
        
    @classmethod
    def related_to(cls, filename):
        """Return all the AuditBlobs pertaining to actions on `filename`."""
        return cls.filter(filename=filename) + cls.delivery(filename)

    @property
    def extension(self):  return os.path.splitext(self.filename)[-1]

# ============================================================================

class RepeatableResultBlob(BlobModel):
    """A model for storing results rendered as a web page... so they can be 
    re-rendered at later time without re-executing forms and hence back/forward 
    arrows can work to redisplay options.
    """
    class Meta(object):
        db_table = TABLE_PREFIX + "_results" # rename SQL table
        
    repr_list = unicode_list = ["id","name", "page_template"]

    unicode_list = ["id", "name", "page_template"]
    
    blob_fields = dict(
        # User supplied fields
        parameters_enc = BlobField(
            str, "json encoding of HTML rendering parameter dictionary", "{}"),
        page_template = BlobField(
            r"\w+\.html", "HTML template which will be rendered using parameter dictionary", ""),
    )

    @classmethod
    def new(cls, page_template, parameters):
        self = cls()
        self.name= uuid.uuid4()
        self.page_template = page_template
        if "disposition" not in parameters:
            parameters["disposition"] = ""  # confirm/cancelled has happened (not)
        self.parameters_enc = json_ext.dumps(parameters)
        self.save()
        return self
    
    @property
    def uuid(self):
        return self.name

    @property
    def parameters(self):
        """return garbage-can dict of page template parameters"""
        if not hasattr(self, "_parameters"):
            self._parameters = utils.Struct(json_ext.loads(self.parameters_enc))
        return self._parameters

    @classmethod   # kludgy,  not confident about Django __setattr__, __setitem__
    def set_parameter(cls, results_id, name, value):
        result = cls.load(results_id)
        result.set_par(name, value)
        result.save()
        
    def set_par(self, name, value):   # Avoid multiple saves
        self.parameters[name] = value
        self.parameters_enc = json_ext.dumps(self.parameters)

    @property
    def repeatable_url(self):
        "Return the URL which can be used to display this persistent result."
        return "/display_result/" + str(self.uuid)

    @property
    def abs_repeatable_url(self):
        "Return the URL which can be used to display this persistent result."
        return config.CRDS_URL + "/display_result/" + str(self.uuid)

    @property
    def authenticated_url(self):
        "Return the URL which can be used to display this persistent result."
        return config.CRDS_URL + "/authenticated_result/" + str(self.uuid)

# =============================================================================

# ============================================================================

class RemoteContextModel(CrdsModel):
    """A model for storing the values of remote actual contexts pushed from priviledged sites.
    These are distinct from the server-side Set Context default context value since the remote
    site must successfully sync before there is a match.
    
    The remote cache is identified by it's key.
    """
    class Meta(object):
        db_table = TABLE_PREFIX + "_remote_context" # rename SQL table
        
    repr_list = unicode_list = ["id", "name", "observatory", "kind", "context"]
    
    observatory = models.CharField(max_length=32,
        help_text = "Observatory this context applies to.", default="none")

    kind = models.CharField(max_length=64,
        help_text = "operational, edit, etc.", default="none")

    key = models.CharField(max_length=128,
        help_text = "Observatory this context applies to.", default="none")

    context = models.CharField(max_length=64,
        help_text = "Name of context in use by remote cache.", default="none")


    @classmethod
    def new(cls, name, observatory, kind, context):
        self = cls()
        self.name = name
        self.observatory = observatory
        self.kind = kind
        self.key = str(uuid.uuid4())
        self.context = context
        self.save()
        return self

def push_remote_context(observatory, kind, key, context):
    """Update the context value for the specified observatory and kind for the remote
    site identified by key.
    """
    assert re.match(r"^\w+\.pmap$", context), \
        "Pushed context is not a valid .pmap name."
    assert file_exists(context), \
        "Pushed context file does not exist in CRDS."
    model = RemoteContextModel.objects.get(observatory=observatory, kind=kind, key=key)
    if model.context != context:
        add_meta_event("Remote", srepr(kind), "context update",
                       "named", srepr(model.name), "from key", srepr(key), 
                       "from context", srepr(model.context),
                       "to context", srepr(context))
        model.context = context
        model.save()

def get_remote_context(observatory, pipeline_name):
    """Get the context value for the specified remote pipeline."""
    model = RemoteContextModel.objects.get(observatory=observatory, name=pipeline_name)
    return model.context

# =============================================================================

def get_delivery_status():
    """Based on the .cat files in the audit log, return a list of dictionaries that 
    describe the corresponding deliveries.
    """
    auditblobs = [ blob for blob in AuditBlob.objects.all() if blob.thaw().filename.endswith(".cat") ]
    fileblobs = get_fileblob_map()
    catalog_info = []
    for audit in auditblobs:
        audit.thaw()
        files = []
        status = "delivery corrupt"
        status_class = "error"
        with log.error_on_exception("Failed interpreting catalog", repr(audit.filename)):
            files = sorted(open(os.path.join(config.CRDS_CATALOG_DIR, audit.filename)).read().splitlines())
            status = fileblobs[files[0]].status
            status_class = fileblobs[files[0]].status_class
        catalog_info.append(
                dict(date=audit.date,
                     action=audit.action,
                     user=audit.user,
                     description=audit.why,
                     files=files,
                     catalog=audit.filename,
                     status=status,
                     status_class=status_class)
            )
    delivery_status = list(reversed(sorted(catalog_info, key=lambda k: k["date"])))
    return delivery_status

# =============================================================================

META_EVENTS_FILE = os.path.join(config.CRDS_SERVER_LOGS, "meta_events.log")

def add_meta_event(*args, **keys):
    """Format the log message specified by *args, **keys and add it
    to the persistent events file.   The persistent events file is not
    mirrored between server strings so it remains a permament record
    when the database is copied from another server.   This enables it
    to record things like 'which context the I&T pipeline last synced'
    and 'when and how was this string last mirroed.'
    """
    now = timestamp.now()
    test_mode = "crds_server.manage test" in sys.argv
    if not test_mode:
        message = log.format(now, *args, **keys)
        with open(META_EVENTS_FILE, "a+") as events:
            events.write(message)
        log.info("META", message)

# ===========================================================================================================
