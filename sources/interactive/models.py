import os.path
import re
import hashlib

from django.db import models

# Create your models here.
from crds import (timestamp, rmap)
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
                raise FieldError("Value for " + repr(attr) + 
                                 " didn't match " + repr(type_))
        elif isinstance(type_, list): # treat lists as literal legal values
            if value in type_:
                return value
            else:
                raise FieldError("Value for " + repr(attr) + 
                                 " was not one of " + repr(type_))
        else: # try to use field type as a type converter
            try:
                return type_(value)
            except Exception:
                raise FieldError("Value for " + repr(attr) +
                                 " not convertible to " + repr(type_))

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

class FileBlob(Blob):
    """Represents a delivered file,  either a reference or a mapping."""
    fields = dict(
        # User supplied fields
        uploaded_as = BlobField("^[A-Za-z0-9_.]+$", "original upload filename", ""),
        description = BlobField(str, "brief description of this delivery",""),
        modifier_name = BlobField(str, "person who made these changes",""),
        deliverer_user = BlobField(str, "username who uploaded the file", ""),
        deliverer_email = BlobField(str, "person's e-mail who uploaded the file", ""),
        status = BlobField(["operational","pending archive","blacklisted","bad"], 
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
    )
    
    @property
    def filename(self):
        return os.path.basename(self.pathname)
    
    @property
    def extension(self):
        parts = os.path.splitext(self.filename)
        return parts[-1]

    def save(self):
        Blob.save(self, self.filename)
        
    def checksum(self):
        return hashlib.sha1(open(self.pathname).read()).hexdigest()
    
    def verify(self):
        assert self.checksum() == self.sha1sum, "checksum error"
        
class MappingBlob(FileBlob):
    """Represents a CRDS mapping file, i.e. a pipeline or instrument context,
    or an rmap.   Records delivery info, status, and location.
    """
    
class ReferenceBlob(FileBlob):
    """Represents a reference data file managed by CRDS."""

# ============================================================================

AUDITED_ACTIONS = ["blacklist","submit file","reserve name"]

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
    def create_record(cls, user, action, affected_file, why, details, date=None,
                      fileblob=None):
        """Save a record of an action in the database."""
        rec = cls()
        rec.user = user
        rec.action = action
        rec.filename = affected_file
        rec.why = why
        rec.details = details
        if date is None:
            date = crds.timestamp.now()
        rec.date = date
        if fileblob is None:
            fileblob = rec.fileblob
        rec.observatory = fileblob.observatory
        rec.instrument = fileblob.instrument
        rec.filekind = fileblob.filekind
        rec.save()

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
    
