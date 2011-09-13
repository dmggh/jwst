import os.path
import re
import hashlib

from django.db import models

import pyfits

# Create your models here.
from crds import (timestamp, rmap, utils)
from crds.compat import (literal_eval, namedtuple)

# ============================================================================

OBSERVATORIES = ["hst","jwst"]

INSTRUMENTS = ["acs","cos","stis","wfc3"]

FILEKINDS = ['apdstab', 'apertab', 'atodtab', 'badttab', 'biasfile', 'bpixtab',
            'brftab', 'brsttab', 'ccdtab', 'cdstab', 'cfltfile', 'crrejtab',
            'darkfile', 'deadtab', 'dgeofile', 'disptab', 'echsctab', 'exstab',
            'flatfile', 'gactab', 'geofile', 'halotab', 'idctab', 'inangtab',
            'lamptab', 'lfltfile', 'mdriztab', 'mlintab', 'mofftab', 'nlinfile',
            'oscntab', 'pctab', 'pfltfile', 'phatab', 'phottab', 'riptab',
            'sdctab', 'spottab', 'sptrctab', 'srwtab', 'tdctab',
            'tdstab', 'wcptab', 'xtractab']

EXTENSIONS = [".pmap",".imap",".rmap",".fits"]

# ============================================================================

class BlobModel(models.Model):
    """A generic data format which lets us transactionally store anything
    which has a repr() which can be literal_eval()'ed back to life.   This
    lets us evolve our system without constantly changing database schemas.
    """
    kind  = models.CharField(
            max_length = 64,
            help_text = "class of this blob")
    
    name = models.CharField(
            max_length = 64, default="(none)",
            help_text = "descriptive string uniquely identifying this instance")

#    key1 = models.CharField(max_length=64, help_text="unencoded search key 1")
#    key2 = models.CharField(max_length=64, help_text="unencoded search key 2")
#    key3 = models.CharField(max_length=64, help_text="unencoded search key 3")
#    key4 = models.CharField(max_length=64, help_text="unencoded search key 4")

    contents  = models.TextField( 
            help_text  = "repr() of value of this blob,  probably repr(dict).")
    
    def freeze(self, value):
        """Save `value` to the database as the contents of this BlobModel.
        """
        self.contents = repr(value)
        self.save()
    
    def thaw(self):
        """Load and evaluate the contents of this BlobModel instance.  Return
        them.
        """
        return literal_eval(self.contents)

# ============================================================================

class BlobField(object):
    """Basic properties for a field of a Blob."""
    def __init__(self, type, help, default, nonblank=True):
        self.type = type
        self.help = help
        self.default = default
        self.nonblank = nonblank

# ============================================================================

class FieldError(Exception):
    """Blob field value did not meet its constraint."""
    
class MissingInputError(FieldError):
    """A required input field was not specified in a form submission."""
    
class Blob(object):
    """Generic base class for BlobModel live instances.   BlobModels load
    from the database into Blobs.   Blobs can be customized without changing
    the database schema.
    """
    fields = {}   # BlobFields
    
    repr_list = None
    
    def __init__(self, blob=None, id=None, **keys):
        if blob is None:
            blob = {}
        self._values = {}
        self._id = id
        for fieldname in self.fields:
            self._values[fieldname] = self.fields[fieldname].default
        self._values.update(blob)
        for key in keys:
            self._values[key] = keys[key]
            
    def __repr__(self):
        """Display values of fields in `self.repr_list` else display
        values of all fields in name-sorted order.
        """
        rep = self.__class__.__name__ + "(" 
        for field in self.repr_list or sorted(self.fields):
            rep += field + "=" + repr(self._values[field]) + ", "
        rep = rep[:-2] + ")"
        return rep
    
    def __getattr__(self, attr):
        """Handle fields specially."""
        if attr in self.fields:
            return self._values[attr]
        else:
            return object.__getattr__(self, attr)
    
    def __setattr__(self, attr, value):
        """Handle fields specially,  enforcing legal values."""
        if attr in self.fields:
            self._values[attr] = self.enforce_type(attr, value)
        else:
            object.__setattr__(self, attr, value)
            
    def enforce_type(self, attr, value):
        """Ensure `value` meets the constraints for field `attr`.  Return
        a possibly coerced `value` if it's legal,  else raise an exception.
        """
        type_ = self.fields[attr].type
        if not str(value).strip():
            if self.fields[attr].nonblank: 
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

    def save(self, name=None):
        """Save a blob named `name`,  or else an anonymous blob.
        """
        if self._id is None:
            obj = BlobModel()
            self._id = obj.id
        else:
            obj = BlobModel.objects.get(id=self._id)
        obj.kind = self.__class__.__name__
        if name is not None:
            obj.name = name 
        obj.freeze(self._values)
        
    @classmethod
    def load(cls, name):
        """Load the blob named `name`.   Note that "anonymous" blobs cannot
        be load()'ed.
        """
        candidates = BlobModel.objects.filter(kind=cls.__name__, name=name)
        if len(candidates) == 0:
            raise LookupError("Couldn't find " + cls.__name__ + 
                              " named " + repr(name))
        elif len(candidates) > 1:
            raise LookupError("Found more than one " + cls.__name__ + 
                              " named " + repr(name))
        else:
            return cls.from_model(candidates[0])
        
    @classmethod
    def from_model(cls, model):
        """Reconstitute a BlobModel `model` as an instance of this `cls`."""
        return cls(blob=model.thaw(), id=model.id)
  
    @classmethod
    def filter(cls, **matches):
        """Return the Blobs of this `cls` which match the filter `matches`."""
        for model in BlobModel.objects.filter(kind=cls.__name__):
            candidate = cls.from_model(model)
            for key, val in matches.items():
                cval = getattr(candidate, key, None)
                if val != cval:
                    break
            else:
                yield candidate

    @classmethod
    def exists(cls, name):
        """Return True if `name` exists."""
        candidates = BlobModel.objects.filter(kind=cls.__name__, name=name)
        return len(candidates) >= 1

# ============================================================================

class CounterBlob(Blob):
    """The serial number counter for a single kind of file,  named:
            <observatory> _ <instrument> _ <filekind>
            
    Automatically generates a new counter if it doesn't already exist:
    use with care.
    """
    fields = dict(
        counter = BlobField(int, "an integer counter", 0),
    )
    
    @classmethod
    def _setup(cls, args):
        name = "_".join(args)
        try:
            blob = cls.load(name)
        except LookupError:
            blob = CounterBlob()
        return name, blob
    
    @classmethod
    def next(cls, *args):
        """Return the next integer in the series identified by `args`,  
        which are nominally class, observatory, instrument, filekind.
        .e.g.  mapping, hst, acs, biasfile
               reference, jwst, miri, biasfile
        """
        name, blob = cls._setup(args)
        blob.counter += 1
        blob.save(name)
        return blob.counter

    @classmethod
    def last(cls, *args):
        """Like next,  but return the last number issued."""
        name, blob = cls._setup(args)
        return blob.counter

    @classmethod
    def set(cls, *args): 
        """Like next,  but set the counter identified by args[:-1] to args[-1]
        """
        # nominally class, observatory, instrument, filekind, number
        num = int(args[-1])
        name, blob = cls._setup(args[:-1])
        blob.counter = num
        blob.save(name)

# ============================================================================

FILE_STATUS_MAP = {
    "operational" : "green",
    "pending archive" : "orange",
    "blacklisted" : "red",
}

PEDIGREES = ["INFLIGHT","GROUND","DUMMY","MODEL"]
CHANGE_LEVELS = ["SEVERE", "MEDIUM", "TRIVIAL"]
COMMENT_MODES = ["Y","N","APPEND"]

FILENAME_RE = "^[A-Za-z0-9_.]+$"

class FileBlob(Blob):
    """Represents a delivered file,  either a reference or a mapping."""
    
    fields = dict(
        # User supplied fields
        uploaded_as = BlobField(FILENAME_RE, "original upload filename", ""),
        modifier_name = BlobField(str, "person who made these changes",""),
        deliverer_user = BlobField(str, "username who uploaded the file", ""),
        deliverer_email = BlobField(str, "person's e-mail who uploaded the file", ""),
        description = BlobField(
            str, "Brief rationale for changes to this file.", "", nonblank=False),
        state = BlobField(FILE_STATUS_MAP.keys(), 
            "operational status of this file.", "pending archive"),
        blacklisted_by = BlobField(list, 
            "Comma separated list of files marking this"
            " file as bad,  possibly self.", []),
        # Automatically generated fields
        pathname = BlobField("^[A-Za-z0-9_./]+$", 
            "path/filename to CRDS master copy of file", "None"),
        delivery_date = BlobField(str, 
            "date file was delivered to CRDS", ""),
        observatory = BlobField(OBSERVATORIES, 
            "observatory associated with file", "hst"),
        instrument = BlobField(INSTRUMENTS, 
            "instrument associated with file", "", nonblank=False),
        filekind = BlobField(FILEKINDS, 
            "dataset keyword associated with this file", "", nonblank=False),
        serial = BlobField("[A-Za-z0-9_]*",
            "file id or serial number for this file", "", nonblank=False),
        sha1sum = BlobField(str, 
            "checksum of file at upload time", "", nonblank=False),

        comparison_file = BlobField(
            FILENAME_RE, 
            "Name of existing file to compare to for mode coverage.", ""),
        pedigree = BlobField(
            PEDIGREES, 
            "What's the source of this file?", ""),
        opus_flag = BlobField(
            ["Y","N"], 
            "Should file be delivered to OPUS and archive?", "Y"),
        change_level = BlobField(
            CHANGE_LEVELS,
            "Do the changes to this file force recalibration of science data?",
            "SEVERE"),
        useafter_date = BlobField(
            str,  "Date after which this reference should be used", ""),
            
        observation_begin_date = BlobField(
            str, "Start of INFLIGHT observation." , ""),
        observation_end_date = BlobField(
            str, "End of INFLIGHT observation.", ""),
        mode_values = BlobField(
            dict, "Mapping from critical FITS header "
                "parameters to their values.", {}),
    )
    
    @classmethod
    def new(cls, observatory, upload_name, permanent_location, 
            deliverer_user, deliverer_email, description, 
            change_level="SEVERE", opus_flag="N",
            add_slow_fields=True, index=None):
        """Create a new FileBlob or subclass."""
        
        assert isinstance(add_slow_fields, (bool,int)), "parameter type error"
        
        blob = cls()
        blob.observatory = observatory
        blob.uploaded_as = upload_name
        blob.pathname = permanent_location
        blob.deliverer_user = deliverer_user
        blob.deliverer_email = deliverer_email
        blob.description = description
        blob.delivery_date = timestamp.now()
        if add_slow_fields:
            blob.sha1sum = blob.checksum()
        instrument, filekind, serial = utils.get_file_properties(
            observatory, permanent_location)
        blob.instrument = instrument
        blob.filekind= filekind
        blob.serial = serial
        blob.blacklisted_by = []

        # These need to be checked before the file is copied and the blob is made.
        if not rmap.is_mapping(upload_name):
            blob.change_level = change_level
            blob.opus_flag = opus_flag
#            blob.pedigree = pyfits.getval(permanent_location, "PEDIGREE")
#            blob.useafter_date = pyfits.getval(permanent_location, "USEAFTER")
            if blob.pedigree.strip().startswith("INFLIGHT"):
                # XXX fill in observation_begin_date, observation_end_date
                pass
        
        blob.save()
        
        if index is None:
            index = FileIndexBlob.load(observatory)
            index.add_file(blob.filename)
            index.save()
        else:  # caller takes responsibility for loading/saving
            index.add_file(blob.filename)

        return blob

    @property
    def filename(self):
        return os.path.basename(self.pathname)
    
    @property
    def status(self):
        if self.blacklisted_by:
            return "blacklisted"
        else:
            return self.state

    @property
    def status_class(self):
        return FILE_STATUS_MAP[self.status]
    
    @property
    def extension(self):
        parts = os.path.splitext(self.filename)
        return parts[-1]

    def save(self):
        Blob.save(self, self.filename)
        
    def checksum(self):
        return hashlib.sha1(open(self.pathname).read()).hexdigest()
    
    @property
    def checksum_ok(self):
        return self.checksum() == self.sha1sum
        
class MappingBlob(FileBlob):
    """Represents a CRDS mapping file, i.e. a pipeline or instrument context,
    or an rmap.   Records delivery info, status, and location.
    """
    
class ReferenceBlob(FileBlob):
    """Represents a reference data file managed by CRDS."""
    
# ============================================================================

class FileIndexBlob(Blob):
    """Blob which records the names of all known CRDS files,  nominally
    one instance per observatory.   This eliminates the need to load a
    blob just to check that the file exists.   A file that is in CRDS is
    assumed to be good unless it appears on a blacklist.
    """
    fields = dict(
        known_files = BlobField(list, "original upload filename", []),
        )

    def add_file(self, filename):
        if filename not in self.known_files:
            self.known_files.append(filename)

    def exists(self, filename):
        return filename in self.known_files


# ============================================================================

AUDITED_ACTIONS = [
    "submit file", "blacklist", "reserve name", "mass import", 
    "new context", "replace reference", "add useafter",
    ]

class AuditBlob(Blob):
    """Maintains an audit trail of important actions indicating who did them,
    when, and why.
    """
    fields = dict(
        # User supplied fields
        user = BlobField(str, "user performing this action", ""),
        date = BlobField(str, "date action performed", ""),
        action = BlobField(AUDITED_ACTIONS,"name of action performed", ""),        
        filename = BlobField("^[A-Za-z0-9_./]+$", 
                "file affected by this action", "None"),
        why = BlobField(str, "reason this action was performed",""),
        details = BlobField(str, "supplementary info", "", nonblank=False),
        observatory = BlobField(
            OBSERVATORIES, "associated observatory", "", nonblank=False),
        instrument = BlobField(
            INSTRUMENTS, "associated instrument", "", nonblank=False),
        filekind = BlobField(
            FILEKINDS, "associated filekind", "", nonblank=False),
    )
    
    @classmethod
    def new(cls, user, action, affected_file, why, details, 
            observatory, instrument, filekind, date=None):
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
        blob.observatory = observatory
        blob.instrument = instrument
        blob.filekind = filekind
        blob.save()
        return blob

    @property
    def fileblob(self):
        if not hasattr(self, "_fileblob"):
            if rmap.is_mapping(self.filename):   # code smell here...  :-(
                self._fileblob = MappingBlob.load(self.filename)
            else:
                self._fileblob = ReferenceBlob.load(self.filename)
        return self._fileblob

    @property
    def extension(self):  return os.path.splitext(self.filename)[-1]


def add_crds_file(observatory, upload_name, permanent_location, 
            deliverer, deliverer_email, description, 
            creation_method, audit_details="", 
            change_level="SEVERE", opus_flag="N",
            add_slow_fields=True, index=None):
    "Make a database record for this file.  Track the action of creating it."""
    if rmap.is_mapping(permanent_location):
        blob_class = MappingBlob
    else:
        blob_class = ReferenceBlob
        
    fileblob = blob_class.new(
        observatory, upload_name, permanent_location, 
        deliverer, deliverer_email, description,
        change_level=change_level, opus_flag=opus_flag,
        add_slow_fields=add_slow_fields, index=index)
    
    # Redundancy, database record of how file got here, important action
    AuditBlob.new(
        deliverer, creation_method, fileblob.filename, 
        description, audit_details,
        observatory=fileblob.observatory, instrument=fileblob.instrument,  
        filekind=fileblob.filekind, date=fileblob.delivery_date,)
    
    return fileblob

def create_index(observatory):    
    """Create an empty file index for `observatory` if one does not already
    exist.  File indices track the existence of files in a single blob for
    the sake of speed.
    """
    try:
        index = FileIndexBlob.load(observatory)
    except LookupError:
        index = FileIndexBlob()
        index.save(observatory)
    return index





