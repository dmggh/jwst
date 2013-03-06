import os
import os.path
import re
import hashlib
import datetime

from django.db import models

# Create your models here.
from crds import (timestamp, rmap, utils, refactor, checksum, log, data_file, uses)
from crds import CrdsError
from crds.compat import (namedtuple, OrderedDict)

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

class BlobModel(models.Model):
    """A generic hybrid format which contains several fast static fields
    as well as a "blob" of slow fields which are easier to declare and
    don't change the database schema.
    """
    class Meta:
        abstract = True    # Collapse model inheritance for flat SQL tables

    model_fields = ["id","name","blob"]  # field directly in database
    blob_fields = {}  # field in database as part of blob
    blob_properties = []  # computed field
    exclude_from_info = ["blob"]    # not included in self.info()
    repr_list = None    # fields shown in __repr__ or ALL if None
    unicode_list = None  # fields shown in __unicode__ or ALL if None
    
    name = models.CharField(
        max_length = 64, default="none",
        help_text = "descriptive string uniquely identifying this instance")
    
    blob = models.TextField( 
            help_text  = "repr() of value of this blob,  probably repr(dict).",
            default = "{}")
    
    def __init__(self, *args, **keys):
        models.Model.__init__(self, *args)
        for fieldname in self.blob_fields:
            setattr(self, fieldname, self.blob_fields[fieldname].default)
        for fieldname in keys:
            setattr(self, fieldname, keys[fieldname])
            
    @property
    def fields(self):
        return sorted(list(self.model_fields) + 
                      list(self.blob_fields) + 
                      list(self.blob_properties))

    def __repr__(self, displayed=None):
        """Display values of fields in `self.repr_list` else display
        values of all fields in name-sorted order.
        """
        if displayed is None:
            displayed = self.repr_list or self.fields
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
    
    def __unicode__(self):
        """To support Django db admin views."""
        self.thaw()
        return self.__repr__(self.unicode_list)
    
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

    def save(self):
        blob = {}
        for name in self.blob_fields:
            if name not in self.blob_properties:
                blob[name] = self.enforce_type(name, getattr(self,name))
        self.blob = repr(blob)
        models.Model.save(self)
        
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
    
    def thaw(self):
        blob = eval(self.blob)
        for name, value in blob.items():
            setattr(self, name, value)

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

class CounterBlob(BlobModel):
    """The serial number counter for a single kind of file,  named:
            <observatory> _ <instrument> _ <filekind>
            
    Automatically generates a new counter if it doesn't already exist:
    use with care.
    """
    class Meta:
        db_table = TABLE_PREFIX + "_counters" # rename SQL table from interactive_fileblob

    blob_fields = dict(
        counter = BlobField(int, "an integer counter", 0),
    )
    
    unicode_list = ["name","counter"]
    
    @classmethod
    def setup(cls, args):
        name = "_".join(args)
        try:
            blob = cls.load(name)
        except LookupError:
            blob = CounterBlob(name=name)
        return blob
    
    @classmethod
    def next(cls, *args):
        """Return the next integer in the series identified by `args`,  
        which are nominally class, observatory, instrument, filekind.
        .e.g.  mapping, hst, acs, biasfile
               reference, jwst, miri, biasfile
        """
        blob = cls.setup(args)
        blob.counter += 1
        blob.save()
        return blob.counter

    @classmethod
    def last(cls, *args):
        """Like next,  but return the last number issued."""
        blob = cls.setup(args)
        return blob.counter

    @classmethod
    def set(cls, *args): 
        """Like next(),  but set the counter identified by args[:-1] to args[-1]
        """
        # nominally class, observatory, instrument, filekind, number
        num = int(args[-1])
        blob = cls.setup(args[:-1])
        blob.counter = num
        blob.save()
    
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
        blob = cls.setup(args[:-1])
        if blob.counter <= existing_serial:
            blob.counter = existing_serial + 1
            blob.save()
            log.info("Advanced file counter for '%s' to '%05d' based on from '%s'." % \
                     (blob.name, blob.counter, filepath))
            
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
        CounterBlob.mirror(official_path, observatory, instrument, filekind, ext, serial)

# ============================================================================

PEDIGREES = ["INFLIGHT","GROUND","DUMMY","MODEL"]
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
])

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
         "type", "derived_from"]
        
    unicode_list = ["name", "type", "instrument", "filekind", "state", "blacklisted"]
        
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
    
    derived_from = models.CharField(max_length=128,
        help_text = "Previous version of this file this one was based on.")

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
        delivery_date = BlobField(str, "date file was delivered to CRDS", "none"),
        activation_date = BlobField(str, "i.e. opus load date", "none"),
        # Automatically generated fields
        pathname = BlobField("^[A-Za-z0-9_./]+$", "path/filename to CRDS master copy of file", "none"),
        blacklisted_by = BlobField(list,"List of blacklisted files this file refers to directly or indirectly.", []),
        reject_by_file_name = BlobField(FILENAME_RE, "", ""),
        sha1sum = BlobField(str, "checksum of file at upload time", "none"),
        size = BlobField(long, "size of file in bytes.", -1),
        change_level = BlobField(CHANGE_LEVELS, "Do the changes to this file force recalibration of science data?", ""), 

        pedigree = FitsBlobField("PEDIGREE", str, "source of reference file", "none"),
        reference_file_type = FitsBlobField("REFTYPE", str, "From the REFTYPE keyword", "none"),
        useafter_date = FitsBlobField("USEAFTER", str, "date after which file should be used", "none"),
        comment = FitsBlobField("DESCRIP", str, "from DESCRIP keyword of reference file.", "none"),
)

    @property
    def is_bad_file(self):
        """Return the 'reject state' of this file,  either True or False."""
        return self.blacklisted or self.rejected
    
    @property
    def available(self):
        """Return True if this file is allowed to be distributed now."""
        # TODO add general_availabilty_date....
        return self.state in config.CRDS_DISTRIBUTION_STATES and not self.is_bad_file
    
    def init_FITS_fields(self):
        for name, field in self.blob_fields.items():
            if isinstance(field, FitsBlobField):
                try:
                    value = data_file.getval(self.pathname, field.fitskey)
                    setattr(self, name, value)
                except Exception:
                    name = self.uploaded_as or self.name
                    log.warning("required keyword '%s' is missing in '%s'" % (field.fitskey, name))
    
    def add_slow_fields(self):
        log.info("Adding slow fields for", repr(self.name))
        self.sha1sum = self.compute_checksum()
        if self.type == "reference":
            self.init_FITS_fields()
        self.save()
            
    def check_unique_sha1sum(self):
        # matches = self.__class__.filter(sha1sum=self.sha1sum)
        return # XXXX TODO file uniqueness sha1sum not verified
        if len(matches) < 1:
            raise CrdsError("Checksum computation error for '%s'.  No matching blob found." % self.uploaded_as)
        if len(matches) > 1:
            others = ", ".join([str(x.name) for x in matches if str(x.name) != str(self.name)])
            raise CrdsError("Submitted file '%s' renamed to '%s' is identical to existing files: %s" % (self.uploaded_as, self.name, others))

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
        blob.delivery_date = timestamp.now()
        try:
            instrument, filekind = utils.get_file_properties(observatory, permanent_location)
            blob.instrument = instrument
            blob.filekind= filekind
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
        try:
            return os.stat(self.pathname).st_size
        except Exception, exc:
            log.error("Computing size of", repr(self.name),"failed:", str(exc))
            return -1
    
    @property
    def status(self):
        if self.blacklisted:
            return "blacklisted"
        elif self.state == "delivered":
            if os.path.exists(self.catalog_link) or os.path.exists(self.catalog_link + "_proc"):
                return "delivered"
            else:
                self.state = "operational"
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
    
    def compute_checksum(self):
        try:
            return utils.checksum(self.pathname)
        except Exception, exc:
            log.error("Computing sha1sum of", repr(self.pathname), "failed:", str(exc))
            return "checksum failed: " + str(exc)

    @property
    def checksum_ok(self):
        return self.compute_checksum() == self.sha1sum
    
    def destroy(self):
        """Destroy this FileBlob and it's associated file.   This
        cannot be revoked and should *ONLY* be called as part of cleanup for
        a failed multi-part file submission.
        """
        try:
            log.info("DESTROYING", repr(self.pathname))
            assert "/grp/hst/cdbs" not in self.pathname,   \
                "Can't delete borrowed CDBS file."
            os.remove(self.pathname)
            self.delete()
        except Exception, exc:
            log.error("Problem destroying",repr(self.pathname))

    @property
    def collisions(self):
        """A list of other files derived from the same source file...  possibly bad."""
        # include file.state == "uploaded",  those pending confirmation.
        return [col.name for col in BlobModel._filter(FileBlob, derived_from=self.derived_from) if col.name != self.name]

    # Hokeyness because BlobModel doesn't actually have .objects because it
    # it is abstract... so normal class method inheritance techniques fail.
    @classmethod
    def filter(cls, **matches):  # omit "uploaded" files from filter result
        return [file_ for file_ in BlobModel._filter(FileBlob, **matches) if file_.state != "uploaded"]

# ============================================================================

def add_crds_file(observatory, upload_name, permanent_location, 
            deliverer, deliverer_email, description,
            change_level="SEVERE", add_slow_fields=True,
            creator_name="unknown", state="submitted", update_derivation=True):
    "Make a database record for this file.  Track the action of creating it."""

    if rmap.is_mapping(upload_name):
        if update_derivation:
            derived_from = refactor.update_derivation(permanent_location)
        else:
            mapping = rmap.fetch_mapping(permanent_location)
            derived_from = mapping.derived_from
    else:  # references
        if update_derivation:
            derived_from = upload_name
        else:
            derived_from = "initial reference import " + str(datetime.datetime.now())
    try:
        # Set file permissions to read only.
        os.chmod(permanent_location, 0444)
    except Exception:
        pass

    blob = FileBlob.new(
        observatory, upload_name, permanent_location, 
        creator_name, deliverer, deliverer_email, description,
        change_level=change_level, state=state, derived_from=derived_from)

    if add_slow_fields:
        blob.add_slow_fields()
        blob.check_unique_sha1sum()
        
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

CONTEXT_TYPES = ["default", "operational"]

# "default" is synonymous with "edit", the suggested derivation point for edits.

class ContextBlob(BlobModel):
    """Keeps track of which mappings are the default.
    """
    class Meta:
        db_table = TABLE_PREFIX + "_contexts" # rename SQL table from interactive_fileblob

    blob_fields = dict(
        # User supplied fields
        observatory = BlobField(
            OBSERVATORIES, "associated observatory", ""),
        context = BlobField("\w+\.pmap", "default pipeline context", ""),
    )
    
    unicode_list = ["name", "context"]
    
    @classmethod
    def check_type(self, state):
        assert state in CONTEXT_TYPES, "Unknown context type " + repr(state)
    
    @classmethod
    def get(cls, observatory, state="default"):
        cls.check_type(state)
        return cls.load(observatory + "." + state + "_context")

    def save(self, state="default"):
        self.__class__.check_type(state)
        self.name = self.observatory + "." + state + "_context"
        return BlobModel.save(self)
    
    @classmethod
    def get_map(cls):
        contexts = cls.filter()
        map = {}
        for blob in contexts:
            state = blob.name.split(".")[1].split("_")[0]
            value = blob.context
            map[state] = value
        return map

# ============================================================================

class RepeatableResultBlob(BlobModel):
    """A model for storing results rendered as a web page... so they can be 
    re-rendered at later time without re-executing forms and hence back/forward 
    arrows can work to redisplay options.
    """
    class Meta:
        db_table = TABLE_PREFIX + "_results" # rename SQL table

    blob_fields = dict(
        # User supplied fields
        parameters_enc = BlobField(
            str, "json encoding of HTML rendering parameter dictionary", "{}"),
        page_template = BlobField(
            "\w+\.html", "HTML template which will be rendered using parameter dictionary", ""),
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
            self._parameters = json_ext.loads(self.parameters_enc)
        return common.Struct(self._parameters)

    @classmethod
    def set_parameter(cls, result_id, name, value):
        result = cls.get(id=int(result_id))
        result.parameters[name] = value
        result.parameters_enc = json_ext.dumps(result.parameters)
        result.save()

# ============================================================================

def set_default_context(context, observatory=OBSERVATORY, user="crds-system",
                        state="default"):
    assert context.endswith(".pmap"), "context must be a .pmap"
    ctxblob = FileBlob.load(context)  # make sure it exists
    try:
        blob = ContextBlob.get(observatory, state)
        blob.context = context
    except LookupError:
        blob = ContextBlob(observatory=observatory, context=context)
    blob.save(state=state)

def get_default_context(observatory=OBSERVATORY, state="default"):
    """Return the latest context which is in `state`."""
    return ContextBlob.get(observatory, state).context

# =============================================================================

