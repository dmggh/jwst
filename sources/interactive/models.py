import os.path
import re
import hashlib
import datetime

from django.db import models

# Create your models here.
from crds import (timestamp, rmap, utils, refactor, checksum, log)
from crds.compat import (literal_eval, namedtuple, OrderedDict)

import crds.hst

from crds.server.config import observatory as OBSERVATORY

# ============================================================================

OBSERVATORIES = ["hst","jwst"]

INSTRUMENTS = sorted(crds.hst.INSTRUMENTS)  # + crds.jwst...

FILEKINDS   = sorted(crds.hst.FILEKINDS)    # + crds.jwst...
FILEKIND_TEXT_DESCR = sorted(crds.hst.TEXT_DESCR.items())

EXTENSIONS  = sorted(crds.hst.EXTENSIONS)   # + crds.jwst...

# ============================================================================

class BlobField(object):
    """Basic properties for a field of a Blob."""
    def __init__(self, type, help, default, blank=True):
        self.type = type
        self.help = help
        self.default = default
        self.blank = blank

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

    model_fields = ["id","name","blob"]
    blob_fields = {}    
    repr_list = None    
    
    name = models.CharField(
        max_length = 64, default="(none)",
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
        return sorted(list(self.model_fields) + list(self.blob_fields))

    def __repr__(self):
        """Display values of fields in `self.repr_list` else display
        values of all fields in name-sorted order.
        """
        displayed = self.repr_list or self.fields 
        displayed.remove("blob")
        rep = self.__class__.__name__ + "(" 
        for field in displayed:
            rep += field + "='" + str(getattr(self, field)) + "', "
        rep = rep[:-2] + ")"
        return rep
    
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
            blob[name] = self.enforce_type(name, getattr(self,name))
        self.blob = repr(blob)
        models.Model.save(self)
        
    @classmethod
    def load(cls, name):
        """Load the blob named `name`.   Note that "anonymous" blobs cannot
        be load()'ed.
        """
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
        d = {}
        for obj in cls.objects.all():
            d[obj.name] = obj
            obj.thaw()
        return d

# ============================================================================

class CounterBlob(BlobModel):
    """The serial number counter for a single kind of file,  named:
            <observatory> _ <instrument> _ <filekind>
            
    Automatically generates a new counter if it doesn't already exist:
    use with care.
    """
    blob_fields = dict(
        counter = BlobField(int, "an integer counter", 0),
    )
    
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
        """Like next,  but set the counter identified by args[:-1] to args[-1]
        """
        # nominally class, observatory, instrument, filekind, number
        num = int(args[-1])
        blob = cls.setup(args[:-1])
        blob.counter = num
        blob.save()

# ============================================================================

PEDIGREES = ["INFLIGHT","GROUND","DUMMY","MODEL"]
CHANGE_LEVELS = ["SEVERE", "MEDIUM", "TRIVIAL"]

FILENAME_RE = "^[A-Za-z0-9_.]+$"
FILEPATH_RE = "^[A-Za-z0-9_./]+$"

FILE_STATUS_MAP = OrderedDict([
    ("uploaded", "orange"),   # On the server,  still temporary
    ("submitted", "orange"),  # In CRDS, pending delivery
    ("delivered", "blue"),    # Delivered to downstream systems, pending archive
    ("operational", "green"), # Archived and in use.
    ("blacklisted", "red"),
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
        db_table = "crds_catalog" # rename SQL table from interactive_fileblob
    
    model_fields = BlobModel.model_fields + \
        ["state", "blacklisted", "observatory", "instrument", "filekind", 
         "type", "derived_from"]

    blacklisted = models.BooleanField(
        default=False, 
        help_text="If True, this file should not be used.")
    
    state = SimpleCharField( FILE_STATUS_MAP.keys(),
        "operational status of this file.", "submitted" )

    observatory = SimpleCharField( OBSERVATORIES,
        "observatory associated with file", "hst")
    
    instrument = SimpleCharField(INSTRUMENTS, 
        "instrument associated with file", "")
    
    filekind = SimpleCharField(FILEKINDS, 
        "dataset keyword associated with this file", "")

    type = SimpleCharField( ["reference","mapping"],
        "type of file,  reference data or CRDS rule or context", "")
    
    derived_from = models.CharField(max_length=48,
        help_text = "Previous version of this file this one was based on.")

    # ===============================
    
    blob_fields = dict(
        uploaded_as = BlobField(FILENAME_RE, "original upload filename", ""),
        creator_name = BlobField(str, "person who made this file",""),
        deliverer_user = BlobField(str, "username who uploaded the file", ""),
        deliverer_email = BlobField(str, "person's e-mail who uploaded the file", ""),
        description = BlobField(
            str, "Brief rationale for changes to this file.", ""),
        catalog_link = BlobField(FILEPATH_RE, 
            "Path to catalog file listing this file for delivery to OPUS. " \
            "File transitions from 'delivered' to 'operational' when deleted.",
            ""),

        # Automatically generated fields
        pathname = BlobField("^[A-Za-z0-9_./]+$", 
            "path/filename to CRDS master copy of file", "None"),
        delivery_date = BlobField(str, 
            "date file was delivered to CRDS", ""),
        sha1sum = BlobField(str, 
            "checksum of file at upload time", ""),

        comparison_file = BlobField(FILENAME_RE, 
            "Name of existing file to compare to for mode coverage.", ""),
        change_level = BlobField(CHANGE_LEVELS,
            "Do the changes to this file force recalibration of science data?",
            "SEVERE"),
                       
        blacklisted_by = BlobField(list,
            "List of blacklisted files this file refers to directly or indirectly.",
            []),
    )
    
    @classmethod
    def new(cls, observatory, upload_name, permanent_location, 
            creator_name, deliverer_user, deliverer_email, description, 
            change_level="SEVERE", add_slow_fields=True, 
            state="submitted", derived_from=None):
        """Create a new FileBlob or subclass."""
        
        assert isinstance(add_slow_fields, (bool,int)), "parameter type error"
        
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
        if add_slow_fields:
            blob.sha1sum = blob.checksum()
        instrument, filekind = utils.get_file_properties(
            observatory, permanent_location)
        blob.instrument = instrument
        blob.filekind= filekind
        blob.derived_from = derived_from if derived_from else "(no predecessor)"

        # These need to be checked before the file is copied and the blob is made.
        if not rmap.is_mapping(upload_name):
            blob.change_level = change_level

        blob.state = state
        
        blob.save()
        
        return blob

    @property
    def filename(self):
        return os.path.basename(self.pathname)
    
    @property
    def status(self):
        if self.blacklisted:
            return "blacklisted"
        elif self.state == "delivered":
            if os.path.exists(self.catalog_link):
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

    def checksum(self):
        return hashlib.sha1(open(self.pathname).read()).hexdigest()
    
    @property
    def checksum_ok(self):
        return self.sha1sum and (self.checksum() == self.sha1sum)
    
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
        return [col.name for col in \
                self.__class__.filter(derived_from=self.derived_from) \
                if col.name != self.name]

    # Hokeyness because BlobModel doesn't actually have .objects because it
    # it is abstract... so normal class method inheritance techniques fail.
    @classmethod
    def filter(cls, **matches):  # omit "uploaded" files from filter result
        return [file_ for file_ in BlobModel._filter(FileBlob, **matches) if \
                file_.state != "uploaded"]

# ============================================================================

def set_state(filename, state):
    blob = FileBlob.load(filename)
    blob.state = state
    blob.save()
    
def get_state(filename):
    return FileBlob.load(filename).state

def known_files():
    return [f.name for f in FileBlob.objects.all()]
    

# ============================================================================

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
    bad_references = fileblob.blacklisted_by
    try:
        bad_references.remove(blacklisted_by)
    except ValueError:
        pass
    # Only remove blacklisting if there are no remaining bad references.
    if not bad_references or bad_references == [blacklisted]:
        fileblob.blacklisted = False
        fileblob.save()
    
def is_blacklisted(blacklisted_file):
    """Return the list of files which contaminate `blacklisted_file` making
    it blacklisted itself.   `mapping` refers to `blacklisted_file`.
    """
    try:
        return FileBlob.load(blacklisted_file).blacklisted
    except Exception:
        return False

# ============================================================================

AUDITED_ACTIONS = [
    "mass import", "submit file", "blacklist", "new context", "batch submit", 
    "edit rmap", "deliver", 
    ]

class AuditBlob(BlobModel):
    """Maintains an audit trail of important actions indicating who did them,
    when, and why.
    """
    blob_fields = dict(
        # User supplied fields
        user = BlobField(str, "user performing this action", ""),
        date = BlobField(str, "date action performed", ""),
        action = BlobField(AUDITED_ACTIONS,"name of action performed", ""),        
        filename = BlobField("^[A-Za-z0-9_./]*$", 
                "file affected by this action", "None"),
        why = BlobField(str, "reason this action was performed",""),
        details = BlobField(str, "supplementary info", ""),
        observatory = BlobField(
            OBSERVATORIES, "associated observatory", ""),
        instrument = BlobField(
            INSTRUMENTS + ["unknown"], "associated instrument", ""),
        filekind = BlobField(
            FILEKINDS + ["unknown"], "associated filekind", ""),
    )
    
    @classmethod
    def new(cls, user, action, affected_file, why, details, 
            observatory=None, instrument="unknown", filekind="unknown", date=None):
        """Save a record of an action in the database."""
        blob = cls()
        blob.user = user
        blob.action = action
        blob.filename = affected_file
        blob.why = why
        blob.details = details
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

class ContextBlob(BlobModel):
    """Keeps track of which mappings are the default.
    """
    blob_fields = dict(
        # User supplied fields
        observatory = BlobField(
            OBSERVATORIES, "associated observatory", ""),
        context = BlobField("\w+\.pmap", "default pipeline context", ""),
    )
    
    @classmethod
    def get(cls, observatory, state="default"):
        return cls.load(observatory + "." + state + "_context")

    def save(self, state="default"):
        self.name = self.observatory + "." + state + "_context"
        return BlobModel.save(self)
    
def set_default_context(context, observatory=OBSERVATORY, user="crds-system",
                        state="default"):
    assert context.endswith(".pmap"), "context must be a .pmap"
    ctxblob = FileBlob.load(context)  # make sure it exists
    try:
        blob = ContextBlob.get(observatory, state)
        was = blob.context
        blob.context = context
    except LookupError:
        was = "undefined"
        blob = ContextBlob(observatory=observatory, context=context)
    blob.save()

def get_default_context(observatory=OBSERVATORY, state="default"):
    """Return the latest context which is in `state`."""
    return ContextBlob.get(observatory, state).context

# =============================================================================

def add_crds_file(observatory, upload_name, permanent_location, 
            deliverer, deliverer_email, description,
            change_level="SEVERE", add_slow_fields=True,
            creator_name="unknown", state="submitted", update_derivation=True):
    "Make a database record for this file.  Track the action of creating it."""

    if rmap.is_mapping(upload_name):
        mapping = rmap.load_mapping(permanent_location)
        if update_derivation:
            derived_from = mapping.name
            refactor.replace_header_value(
                permanent_location, "derived_from", mapping.name)
            refactor.replace_header_value(
                permanent_location, "name", os.path.basename(permanent_location))
            checksum.update_checksum(permanent_location)
        else:
            derived_from = mapping.derived_from
    else:
        if update_derivation:
            derived_from = upload_name
        else:
            derived_from = "initial reference import " + str(datetime.datetime.now())
    try:
        # Set file permissions to read only.
        os.chmod(permanent_location, 0444)
    except Exception:
        pass

    fileblob = FileBlob.new(
        observatory, upload_name, permanent_location, 
        creator_name, deliverer, deliverer_email, description,
        change_level=change_level, add_slow_fields=add_slow_fields,
        state=state, derived_from=derived_from)
    
    return fileblob

def file_exists(filename, observatory="hst"):
    """Return True IFF `filename` is a known CRDS reference or mapping file."""
    try:
        return FileBlob.load(filename)
    except Exception:
        return False
