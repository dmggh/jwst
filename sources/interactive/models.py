import os.path
import re
import hashlib

from django.db import models

# Create your models here.
import crds.timestamp
from crds.compat import literal_eval, namedtuple

# ============================================================================

OBSERVATORIES = ["hst"]

INSTRUMENTS = ["acs","cos","stis","wfc3"]

REFTYPES = ['apdstab', 'apertab', 'atodtab', 'badttab', 'biasfile', 'bpixtab',
            'brftab', 'brsttab', 'ccdtab', 'cdstab', 'cfltfile', 'crrejtab',
            'darkfile', 'deadtab', 'dgeofile', 'disptab', 'echsctab', 'exstab',
            'flatfile', 'gactab', 'geofile', 'halotab', 'idctab', 'inangtab',
            'lamptab', 'lfltfile', 'mdriztab', 'mlintab', 'mofftab', 'nlinfile',
            'oscntab', 'pctab', 'pfltfile', 'phatab', 'phottab', 'riptab',
            'sdctab', 'spottab', 'sptrctab', 'srwtab', 'tdctab',
            'tdstab', 'wcptab', 'xtractab']

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
        rep = self.__class__.__name__ + "(" 
        for field in sorted(self.fields):
            rep += field + "=" + repr(self._values[field]) + ", "
        rep = rep[:-2] + ")"
        return rep
    
    def __getattr__(self, attr):
        if attr in self.fields:
            if attr not in self._values:
                self._values[attr] = self.fields[attr].default
            return self._values[attr]
        else:
            return object.__getattr__(self, attr)
    
    def __setattr__(self, attr, value):
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
        """Load the blob named `name`.
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

class FileBlob(Blob):
    """Represents a delivered file,  either a reference or a mapping."""
    fields = dict(
        # User supplied fields
        uploaded_as = BlobField("^[A-Za-z0-9_.]+$", "original upload filename", ""),
        description = BlobField(str, "brief description of this delivery",""),
        modifier_name = BlobField(str, "person who made these changes",""),
        deliverer_user = BlobField(str, "username who uploaded the file", ""),
        deliverer_email = BlobField(str, "person's e-mail who uploaded the file", ""),
        
        blacklisted = BlobField(bool, 
            "If True this file should no longer be used.", False),

        # Automatically generated fields
        pathname = BlobField("^[A-Za-z0-9_./]+$", 
            "path/filename to CRDS master copy of file", "None"),
        delivery_date = BlobField(str, 
            "date file was delivered to CRDS", ""),
        observatory = BlobField(OBSERVATORIES, 
            "observatory associated with file", "hst"),
        instrument = BlobField(INSTRUMENTS, 
            "instrument associated with file", "", nonblank=False),
        filekind = BlobField(REFTYPES, 
            "dataset keyword associated with this file", "", nonblank=False),
        serial = BlobField("[A-Za-z0-9_]*",
            "file id or serial number for this file", "", nonblank=False),
        sha1sum = BlobField(str, 
            "checksum of file at upload time", "", nonblank=False),
    )
        
    @property
    def filename(self):
        return os.path.basename(self.pathname)
    
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

class AuditBlob(Blob):
    """Maintains an audit trail of important actions indicating who did them,
    when, and why.
    """
    fields = dict(
        # User supplied fields
        user = BlobField(str, "user performing this action", ""),
        date = BlobField(str, "date action performed", ""),
        kind = BlobField("blacklist", "name of action performed", ""),        
        why = BlobField(str, "reason this action was performed",""),
        affected_file = BlobField("^[A-Za-z0-9_./]+$", 
                "file affected by this action", "None"),
    )
    
    @classmethod
    def create_record(cls, user, kind, affected_file, why, details):
        """Save a record of an action in the database."""
        rec = cls()
        rec.user = user
        rec.date = crds.timestamp.now()
        rec.kind = kind
        rec.affected_file = affected_file
        rec.why = why
        rec.details = details
        rec.save()
