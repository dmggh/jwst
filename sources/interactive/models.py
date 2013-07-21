"""Database models for crds.server.interactive."""

import os
import os.path
import re
import datetime

from django.db import models
from django.core.exceptions import ObjectDoesNotExist

# Create your models here.
from crds import (timestamp, rmap, utils, refactor, log, data_file, uses)
from crds import CrdsError
from crds.compat import OrderedDict

from crds.server.config import observatory as OBSERVATORY
from crds.server.config import table_prefix as TABLE_PREFIX
import crds.server.config as config

from . import common
from . import json_ext

observatory_module = utils.get_object("crds." + OBSERVATORY)

# ============================================================================

OBSERVATORIES = ["hst", "jwst"]

INSTRUMENTS = sorted(observatory_module.INSTRUMENTS) # + crds.jwst...
FILEKINDS   = sorted(observatory_module.FILEKINDS)   # + crds.jwst...
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

class FieldError(Exception):
    """Blob field value did not meet its constraint."""
    
class MissingInputError(FieldError):
    """A required input field was not specified in a form submission."""
    
# ============================================================================

class CrdsModel(models.Model):
    class Meta:
        abstract = True    # Collapse model inheritance for flat SQL tables
        
    name = models.CharField(max_length=64, default="", help_text="unique name of this model.")

    unicode_list = ["name"]
    repr_list = ["name"]
    model_fields = ["name"]

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

    @classmethod
    def get_or_create(cls, *args):
        """Get the model for `name`, or create it."""
        name = "_".join(args)
        try:
            model = cls.objects.get(name=name)
        except ObjectDoesNotExist:
            model = cls(name=name)
        return model

# ============================================================================

class CounterModel(CrdsModel):
    """The serial number counter for a single kind of file,  named:
            <observatory> _ <instrument> _ <filekind>
            
    Automatically generates a new counter if it doesn't already exist:
    use with care.
    """
    class Meta:
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
        existing_serial = int(args[-1])
        model = cls.get_or_create(*args[:-1])
        if model.counter <= existing_serial:
            model.counter = existing_serial + 1
            model.save()
            log.info("Advanced file counter for '%s' to '%05d' based on from '%s'." % \
                     (model.name, model.counter, filepath))
            
def mirror_filename_counters(observatory, official_path):
    """As files are added,  make sure that the name serial number counters are consistent
    with the supplied `official name`.   This is particularly required for generated files
    which arrive with pre-assigned names.
    """
    locator = utils.get_locator_module(observatory)
    try:
        path, observatory, instrument, filekind, serial, ext = locator.decompose_newstyle_name(official_path)
    except AssertionError:
        pass
    else:
        CounterModel.mirror(official_path, observatory, instrument, filekind, ext, serial)

# ============================================================================

CONTEXT_TYPES = ["operational", "edit"]

# "default" is synonymous with "edit", the suggested derivation point for edits.

class ContextModel(CrdsModel):
    """Keeps track of which mappings are the default."""
    class Meta:
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

def set_default_context(context, observatory=OBSERVATORY, state="edit", description="set by system"):
    """Remember `context` as the default for `observatory` and `state`.  Update context history."""
    
    assert context.endswith(".pmap"), "context must be a .pmap"
    log.info("Setting '{}' default '{}' context to '{}'".format(observatory, state, context))
    model = ContextModel.get_or_create(observatory, state, "context")
    model.context = context
    model.save()

    # Create a context history record for this context switch.
    history = get_context_history(observatory=observatory, state=state)
    old_context = history[0].context if history else "none"
    if old_context != context:
        new_hist = ContextHistoryModel()
        new_hist.description = description
        new_hist.context = context
        new_hist.state = state
        new_hist.save()
        if state == "operational":
            datestr = timestamp.format_date(new_hist.start_date)
            context = rmap.load_mapping(context)
            supported_files = set(context.reference_names() + context.mapping_names())
            files = get_fileblob_map()
            for fname, blob in files.items():
                if fname in supported_files:
                    if blob.activation_date.year == DEFAULT_ACTIVATION_DATE.year:
                        log.info("Setting activation date of '{}' to '{}'".format(fname, datestr))
                        blob.thaw()
                        blob.activation_date = new_hist.start_date
                        blob.save()

def get_default_context(observatory=OBSERVATORY, state="edit"):
    """Return the latest context which is in `state`."""
    return ContextModel.get_or_create(observatory, state, "context").context

class ContextHistoryModel(CrdsModel):
    """Keeps track of interval at which the specified context was active and the reason for the switch."""
    class Meta:
        db_table = TABLE_PREFIX + "_context_history"
        ordering = ("start_date","context")

    model_fields = repr_list = unicode_list = ["observatory", "start_date", "context", "state", "description"]
    
    @property
    def observatory(self):
        return self.context.split("_")[0].split(".")[0]

    start_date = models.DateTimeField(auto_now_add=True)

    context = models.CharField(max_length=64, default="",
        help_text="name of .pmap assigned to for this kind of context.")
    
    state = models.CharField(max_length=32, default="operational", choices=zip(CONTEXT_TYPES, CONTEXT_TYPES))
    
    description = models.TextField( 
            help_text  = "Reason for the switch to this context.",
            default = "routine update")

    def __init__(self, *args, **keys):
        # observatory="", kind="", context=""):
        super(ContextHistoryModel, self).__init__(*args, **keys)
        
def get_context_history(observatory=OBSERVATORY, state="operational"):
    """Return the history of the specified context,  in reverse order of start date."""
    return [o for o in ContextHistoryModel.objects.filter(state=state).reverse() if o.observatory == observatory]
    # return [o for o in ContextHistoryModel.objects.all().reverse()]

def get_context_by_date(date, observatory=OBSERVATORY):
    """Return the history of the specified context,  in reverse order of start date."""
    dt = timestamp.parse_date(date)
    history = get_context_history(observatory)
    i = 0
    while  i < len(history) and dt < history[i].start_date:
        i += 1
    return str(history[i].context)

# ============================================================================

class BlobModel(CrdsModel):
    """A generic hybrid format which contains several fast static fields
    as well as a "blob" of slow fields which are easier to declare and
    don't change the database schema.
    """
    class Meta:
        abstract = True    # Collapse model inheritance for flat SQL tables

    model_fields = CrdsModel.model_fields + ["blob"]  # field directly in database
    
    blob_fields = {}  # field in database as part of blob
    exclude_from_info = ["blob"]    # not included in self.info()
    repr_list = None    # fields shown in __repr__ or ALL if None
    unicode_list = None  # fields shown in __unicode__ or ALL if None
    
    blob = models.TextField( 
            help_text  = "repr() of value of this blob,  probably repr(dict).",
            default = "{}")
    
    def __init__(self, *args, **keys):
        models.Model.__init__(self, *args, **keys)
        """
        for fieldname in self.blob_fields:
            setattr(self, fieldname, self.blob_fields[fieldname].default)
        for fieldname in keys:
            setattr(self, fieldname, keys[fieldname])
        """
 
    def save(self):
        try:
            old_blob = json_ext.loads(self.blob)
        except:
            old_blob = {}
        blob = {}
        for name in self.blob_fields:
            blob[name] = self.enforce_type(name, getattr(self, name, old_blob.get(name, self.blob_fields[name].default)))
        self.blob = json_ext.dumps(blob)
        super(BlobModel, self).save()
        
    def thaw(self):
        if hasattr(self, "_thawed"):
            return
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
        if hasattr(cls.objects, "select_for_update"):  # requires Django > 1.4
            candidates = cls.objects.select_for_update().filter(name=name)
        else:
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
        for key in matches.keys():
            if key in cls.model_fields:
                model_filters[key] = matches.pop(key)
        for candidate in cls.objects.filter(**model_filters):
            candidate.thaw()
            for filter in matches:
                fval = getattr(candidate, filter, None)
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

PEDIGREES = ["INFLIGHT", "GROUND", "DUMMY", "MODEL"]   # note: INFLIGHT include date
CHANGE_LEVELS = ["SEVERE", "MEDIUM", "TRIVIAL"]

FILENAME_RE = "^[A-Za-z0-9_.]+$"
FILEPATH_RE = "^[A-Za-z0-9_./]+$"

FILE_STATUS_MAP = OrderedDict([
    ("uploaded", "orange"),   # On the server,  still temporary
    ("submitted", "orange"),  # In CRDS, pending delivery
    ("delivered", "blue"),    # Delivered to downstream systems, pending archive
    ("archived", "green"),    # Archived and in use.
    ("operational", "darkgreen"), # In operational use in the pipeline.
    ("blacklisted", "red"),
    ("rejected", "red"),
    ("cancelled", "red"),
])

FILE_STATES = FILE_STATUS_MAP.keys()

DEFAULT_ACTIVATION_DATE =  datetime.datetime(2050, 1, 1, 0, 0)

class SimpleCharField(models.CharField):
    def __init__(self, choice_list, help_text, default):
        models.CharField.__init__(self, 
            max_length=self.max_length(choice_list),
            choices = zip(choice_list, choice_list),
            help_text = help_text,
            default = default)
    
    def max_length(self, choice_list):
        length = 0
        for choice in choice_list:
            length = max(length, len(choice))
        return length
    
class FileBlob(BlobModel):
    """Represents a delivered file,  either a reference or a mapping."""

    class Meta:
        db_table = TABLE_PREFIX + "_catalog" # rename SQL table from interactive_fileblob
    
    model_fields = BlobModel.model_fields + \
        ["state", "blacklisted", "rejected", "observatory", "instrument", "filekind", 
         "type", "derived_from", "sha1sum", "delivery_date", "activation_date", "useafter_date",
         "change_level", "pedigree", "reference_file_type", "size"]
        
    repr_list = unicode_list = ["id", "name", "type", "instrument", "filekind", "state", "blacklisted", "change_level", "available"]
        
    exclude_from_info = BlobModel.exclude_from_info + \
        ["pathname","creator","deliverer", "deliverer_email","catalog_link"]

    state = SimpleCharField( FILE_STATUS_MAP.keys(),
        "operational status of this file.", "submitted" )

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
        auto_now_add=True, help_text="Date file was received by CRDS.")
    
    activation_date = models.DateTimeField(
        auto_now_add=False, default=DEFAULT_ACTIVATION_DATE, help_text="Date file first listed in an operational context.")
    
    useafter_date = models.DateTimeField(
        auto_now_add=False, default=DEFAULT_ACTIVATION_DATE, help_text="Dataset date after which this file is a valid reference.")

    change_level = SimpleCharField(
        CHANGE_LEVELS,  "Affect of changes in this file relative to preceding version on science results", "SEVERE")
    
    pedigree = models.CharField(
        max_length=80, blank=True, default="", help_text="From PEDIGREE, reference characterization, e.g. GROUND 16/07/2008 16/07/2010")
    
    reference_file_type = models.CharField(
        max_length=80, blank=True, default="", help_text="From REFTYPE,  description of file type.")
    
    size = models.BigIntegerField(default=-1, help_text="size of file in bytes.")
    
    # ===============================
    
    blob_fields = dict(
        uploaded_as = BlobField(FILENAME_RE, "original upload filename", ""),
        creator_name = BlobField(str, "person who made this file",""),
        deliverer_user = BlobField(str, "username who uploaded the file", ""),
        deliverer_email = BlobField(str, "person's e-mail who uploaded the file", ""),
        description = BlobField(str, "Brief rationale for changes to this file.", "none"),
        catalog_link = BlobField(FILEPATH_RE, 
            "Path to catalog file listing this file for delivery to OPUS. " \
            "File transitions from 'delivered' to 'operational' when deleted.", ""),

        # Automatically generated fields
        pathname = BlobField("^[A-Za-z0-9_./]+$", "path/filename to CRDS master copy of file", "none"),
        blacklisted_by = BlobField(list,"List of blacklisted files this file refers to directly or indirectly.", []),
        reject_by_file_name = BlobField(FILENAME_RE, "", ""),
        comment = BlobField(str, "from DESCRIP keyword of reference file.", "none"),
        aperture = BlobField(str, "from APERTURE keyword of reference file.", "none")
        )

    @property
    def is_bad_file(self):
        """Return the 'reject state' of this file,  either True or False."""
        return self.blacklisted or self.rejected
    
    bad_field_checks = {
        "uploaded_as" : lambda self: not self.uploaded_as,
        "catalog_link" : lambda self: self.catalog_link and not os.path.exists(self.catalog_link),
        "pathname" : lambda self: not os.path.exists(self.pathname),
        "size" : lambda self: self.size == -1 or self.size != self.compute_size(),
        "sha1sum" : lambda self: self.sha1sum == "none",
        "activation_date": lambda self: self.state in ["archived", "operational"] and \
                                    self.activation_date == DEFAULT_ACTIVATION_DATE,
        "useafter_date": lambda self: self.useafter_date == DEFAULT_ACTIVATION_DATE and self.type != "mapping",
        "type" : lambda self: not self.type,
        "observatory": lambda self: self.observatory not in OBSERVATORIES,
        "instrument": lambda self:  (not self.name.endswith(".pmap")) and self.instrument not in INSTRUMENTS,
        "filekind": lambda self:  (not self.name.endswith((".pmap",".imap"))) and self.filekind not in FILEKINDS,
        "aperture" : lambda self: not self.aperture and self.type != "mapping",
        "comment" : lambda self: not self.comment,
        "description" : lambda self: not self.description,
        "pedigree" : lambda self: self.type == "reference" and not self.pedigree,
        "deliverer_user" : lambda self: not self.deliverer_user,
        "deliverer_email" : lambda self: not self.deliverer_email,
        "creator_name" : lambda self: not self.creator_name,
    }
    
    def get_defects(self, verify_checksum=False):
        """Check `self` and return a list of problems.   See therapist."""
        defects = []
        for field in self.bad_field_checks:
            if self.bad_field_checks[field](self):
                defects.append("BAD {} = '{}'".format(field, getattr(self, field)))
        if verify_checksum and not self.checksum_ok:  # slow
            defects.append("BAD sha1sum = '%s'".format(self.sha1sum))
        return defects
    
    def repair_defects(self, defects=None):
        """Attempt to automatically fix list of `defects` in `self`."""
        if defects is None:
            defects = self.get_defects()
        repairs = {}
        failed = {}
        for defect in defects:
            field = defect.split()[1]  # skip BAD
            fixer = getattr(self, "repair_" + field, None)
            if fixer:
                old = getattr(self, field)
                try:
                    fixer()
                    repairs[field] = "REPAIRED '{}' from '{}' to '{}'".format(field, old, getattr(self, field))
                except Exception, exc:
                    failed[field] = "FAILED repairing '{}' from '{}' exception: '{}'".format(field, old, str(exc))
            else:
                failed[field] = "NO FIXER for '{}'.".format(field)
        if repairs:
            self.save()
        return repairs, failed
    
    def repair_uploaded_as(self):
        frompath, topath = self.uploaded_as, None
        if os.path.exists(self.pathname):
            topath = os.path.basename(self.pathname)
        else:
            try:
                path = rmap.locate_file(self.observatory, self.name)
                if os.path.exists(path):
                    topath = self.name
            except:
                pass
        if topath:
            self.uploaded_as = topath
            return 
        else:
            return "FAILED REPAIRING uploaded_as='{}'".format(frompath)

    def repair_pathname(self):
        cached = rmap.locate_file(self.name, OBSERVATORY)
        if os.path.exists(cached):
            self.pathname = cached

    def repair_catalog_link(self):
        self.catalog_link = ""
    
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
        self.set_fits_field("aperture", "APERTURE")
        
    def repair_aperture(self):
        self.set_fits_field("useafter_date", "USEAFTER")

    def repair_reference_file_type(self):
        self.set_fits_field("reference_file_type", "REFTYPE")

    def repair_pedigree(self):
        self.set_fits_field("pedigree", "PEDIGREE")
        
    def repair_comment(self):
        self.set_fits_field("comment", "DESCRIP")
        
    @property
    def available(self):
        """Return True if this file is allowed to be distributed now."""
        # TODO add general_availabilty_date....
        return self.state in config.CRDS_DISTRIBUTION_STATES and not self.is_bad_file
    
    @property
    def moniker(self):
        try:
            return repr(self.uploaded_as) + " --> " + repr(self.name)
        except:
            return "FileBlob-" + str(self.id)

    def init_FITS_fields(self):
        self.set_fits_field("pedigree", "PEDIGREE")
        self.set_fits_field("reference_file_type", "REFTYPE")
        self.set_fits_field("useafter_date", "USEAFTER", timestamp.parse_date)
        self.set_fits_field("comment", "DESCRIP")
        self.set_fits_field("aperture", "APERTURE")
 
    def set_fits_field(self, model_field, fitskey, sanitizer=lambda x: x):
        filename = self.uploaded_as or self.name
        if data_file.is_geis_data(self.pathname):
            read_from = self.pathname[:-1] + "h"
        else:
            read_from = self.pathname
        try:
            value = data_file.getval(read_from, fitskey)
        except Exception as exc:
            log.error("Fetching keyword '%s' from '%s' failed: '%s'" % (fitskey, read_from, exc))
            return
        try:
            setattr(self, model_field, sanitizer(value))
        except Exception as exc:
            log.error("Setting field '%s' for '%s' failed: '%s'" % (model_field, filename, exc))

    def add_slow_fields(self):
        self.thaw()
        log.info("Adding slow fields for",  self.moniker)
        if self.type == "reference":
            self.init_FITS_fields()
        self.sha1sum = self.compute_checksum()
        self.save()
        try:
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
            log.verbose("Computed checksum for", repr(self.moniker), "as", repr(checksum))
            return checksum
        except Exception, exc:
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
        blob.pathname = permanent_location
        blob.name = blob.filename
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
        except Exception, exc:
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
        if self.is_bad_file:
            return "blacklisted"
        elif self.state == "delivered":
            if os.path.exists(self.catalog_link) or os.path.exists(self.catalog_link + "_proc"):
                return "delivered"
            else:
                self.state = "operational"
                self.save()
                return "operational"
        else:
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
                if col.name != self.name and self.derived_from != "none"]

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
            creator_name="unknown", state="submitted", update_derivation=True):
    "Make a database record for this file.  Track the action of creating it."""

    blob = FileBlob.new(
        observatory, upload_name, permanent_location, 
        creator_name, deliverer, deliverer_email, description,
        change_level=change_level, state=state, derived_from="none")

    if rmap.is_mapping(upload_name):
        if update_derivation:
            derived_from = refactor.update_derivation(permanent_location)
        else:
            derived_from = rmap.fetch_mapping(permanent_location).derived_from
        blob.derived_from = derived_from
        blob.save()
    
    # note that modifying derivation fields changes the sha1sum of mappings.
    if add_slow_fields:
        blob.add_slow_fields()

    # Set file permissions to read only.
    try:
        os.chmod(permanent_location, 0444)
    except:
        pass
    return blob

def file_exists(filename, observatory=OBSERVATORY):
    """Return True IFF `filename` is a known CRDS reference or mapping file."""
    try:
        return FileBlob.load(filename)
    except Exception:
        return False

def get_fileblob_map(observatory=OBSERVATORY, **keys):
    """Return a query set for all the file blobs belonging to observatory.   It's
    vastly faster to check for existence against this map than using file_exists(),
    probably because it's fewer SQL queries.
    """
    return { blob.name : blob for blob in FileBlob.objects.filter(observatory=observatory, **keys) }

def set_state(filename, state):
    blob = FileBlob.load(filename)
    blob.state = state
    blob.save()
    
def get_state(filename):
    return FileBlob.load(filename).state

def known_files():
    return [f.name for f in FileBlob.objects.all()]

# ============================================================================

def transitive_blacklist(blacklist_root, badflag, observatory):
    """Blacklist `blacklist_root` and all the files referring to it according
    to `badflag` as "ok" or "bad".
    """
    assert badflag in ["bad","ok"], "Invalid blacklist badflag=" + srepr(badflag)
    # Determine files which indirectly or directly reference `blacklist_root`
    uses_files = uses.uses([blacklist_root], observatory)

    all_blacklisted = sorted([blacklist_root] + uses_files)

    for also_blacklisted in all_blacklisted:
        log.verbose("Also blacklisting ", repr(also_blacklisted), "as", badflag)
        try:
            if badflag == "bad":
                blacklist(also_blacklisted, blacklist_root)
            elif badflag == "ok":
                unblacklist(also_blacklisted, blacklist_root)
        except Exception, exc:
            log.warning("Blacklist operation failed: ", str(exc))

    return all_blacklisted
    
def blacklist(blacklisted,  blacklisted_by):
    """Mark the file `blacklisted` as bad because of its reference to file
    `blacklisted_by`.
    """
    fileblob = FileBlob.load(os.path.basename(blacklisted))
    fileblob.blacklisted = True
    if blacklisted_by not in fileblob.blacklisted_by:
        fileblob.blacklisted_by.append(blacklisted_by)
    fileblob.save()
    
def unblacklist(blacklisted,  blacklisted_by):
    """Remove blacklisting of file `blacklisted` on behalf of file
    `blacklisted_by`.
    """
    fileblob = FileBlob.load(os.path.basename(blacklisted))
    try:
        fileblob.blacklisted_by.remove(blacklisted_by)
    except ValueError:
        pass
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
    "mass import", "submit file", "blacklist", "new context", "batch submit", 
    "deliver", "set default context"
    ]

class AuditBlob(BlobModel):
    """Maintains an audit trail of important actions indicating who did them,
    when, and why.
    """
    class Meta:
        db_table = TABLE_PREFIX + "_actions" # rename SQL table from interactive_fileblob

    blob_fields = dict(
        # User supplied fields
        user = BlobField(str, "user performing this action", ""),
        date = BlobField(str, "date action performed", ""),
        action = BlobField(AUDITED_ACTIONS,"name of action performed", ""),        
        filename = BlobField("^[A-Za-z0-9_./]*$","file affected by this action", "None"),
        why = BlobField(str, "reason this action was performed",""),
        details = BlobField(str, "supplementary info", ""),
        observatory = BlobField(OBSERVATORIES, "associated observatory", ""),
        instrument = BlobField(INSTRUMENTS + ["unknown"], "associated instrument", ""),
        filekind = BlobField(FILEKINDS + ["unknown"], "associated filekind", ""),
    )
    
    unicode_list = ["action", "user", "date", "filename", "why"]
    
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
        blob.instrument = instrument
        blob.filekind = filekind
        blob.save()
        return blob

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
    class Meta:
        db_table = TABLE_PREFIX + "_results" # rename SQL table
        
    repr_list = unicode_list = ["id","page_template"]

    blob_fields = dict(
        # User supplied fields
        parameters_enc = BlobField(
            str, "json encoding of HTML rendering parameter dictionary", "{}"),
        page_template = BlobField(
            r"\w+\.html", "HTML template which will be rendered using parameter dictionary", ""),
    )

    unicode_list = ["id", "page_template"]
    
    @classmethod
    def new(cls, page_template, parameters):
        self = cls()
        self.page_template = page_template
        if "disposition" not in parameters:
            parameters["disposition"] = ""  # confirm/cancelled has happened (not)
        self.parameters_enc = json_ext.dumps(parameters)
        self.save()
        return self
    
    @property
    def parameters(self):
        """return garbage-can dict of page template parameters"""
        if not hasattr(self, "_parameters"):
            self._parameters = common.Struct(json_ext.loads(self.parameters_enc))
        return self._parameters

    @classmethod   # kludgy,  not confident about Django __setattr__, __setitem__
    def set_parameter(cls, result_id, name, value):
        result = cls.get(id=int(result_id))
        result.set_par(name, value)
        result.save()
        
    def set_par(self, name, value):   # Avoid multiple saves
        self.parameters[name] = value
        self.parameters_enc = json_ext.dumps(self.parameters)
        
    @property
    def repeatable_url(self):
        "Return the URL which can be used to display this persistent result."
        return "/display_result/" + str(self.id)

# =============================================================================

