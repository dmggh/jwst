import os.path
import re
import hashlib

from django.db import models

# Create your models here.

from crds.compat import literal_eval, namedtuple

# ============================================================================

OBSERVATORIES = ["hst"]

INSTRUMENTS = ["acs","cos","stis","wfc3"]

REFTYPES = ['apdstab', 'apertab', 'atodtab', 'badttab', 'biasfile', 'bpixtab',
            'brftab', 'brsttab', 'ccdtab', 'cdstab', 'cfltfile', 'crrejtab',
            'darkfile', 'deadtab', 'dgeofile', 'disptab', 'echsctab', 'exstab',
            'flatfile', 'geofile', 'halotab', 'idctab', 'inangtab',
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
            max_length = 64,
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

# Basic properties for the fields of a Blob

BlobField = namedtuple("BlobField", "type,help,default")

# ============================================================================

class FieldError(Exception):
    """Blob field value did not meet its constraint."""
    
class Blob(object):
    """Generic base class for BlobModel live instances.   BlobModels load
    from the database into Blobs.   Blobs can be customized without changing
    the database schema.
    """
    _blob_kind = "Blob"
    _fields = {}   # BlobFields
    
    def __init__(self, blob=None, id=None, **keys):
        if blob is None:
            blob = {}
        self._values = {}
        self._id = id
        for fieldname in self._fields:
            self._values[fieldname] = self._fields[fieldname].default
        self._values.update(blob)
        for key in keys:
            self._values[key] = keys[key]
            
    def __repr__(self):
        rep = self.__class__.__name__ + "(" 
        for field in sorted(self._fields):
            rep += field + "=" + repr(self._values[field]) + ", "
        rep = rep[:-2] + ")"
        return rep
    
    def __getattr__(self, attr):
        if attr in self._fields:
            if attr not in self._values:
                self._values[attr] = self._fields[attr].default
            return self._values[attr]
        else:
            return object.__getattr__(self, attr)
    
    def __setattr__(self, attr, value):
        if attr in self._fields:
            self._values[attr] = self.enforce_type(attr, value)
        else:
            object.__setattr__(self, attr, value)
            
    def enforce_type(self, attr, value):
        """Ensure `value` meets the constraints for field `attr`.  Return
        a possibly coerced `value` if it's legal,  else raise an exception.
        """
        type_ = self._fields[attr].type
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

    def save(self, name):
        if self._id is None:
            obj = BlobModel()
            self._id = obj.id
        else:
            obj = BlobModel.objects.get(id=self._id)
        obj.kind = self.__class__.__name__
        obj.name = name 
        obj.freeze(self._values)
        
    @classmethod
    def load(cls, name):
        candidates = BlobModel.objects.filter(kind=cls.__name__, name=name)
        if len(candidates) == 0:
            raise LookupError("Couldn't find " + cls.__name__ + 
                              " named " + repr(name))
        elif len(candidates) > 1:
            raise LookupError("Found more than one " + cls.__name__ + 
                              " named " + repr(name))
        else:
            model = candidates[0] 
            blob = model.thaw()
            return cls(blob=blob, id=model.id)
        
    @classmethod
    def exists(cls, name):
        """Return True if `name` exists.
        """
        candidates = BlobModel.objects.filter(kind=cls.__name__, name=name)
        return len(candidates) >= 1

# ============================================================================

class FileBlob(Blob):
    """Represents a delivered file,  either a reference or a mapping.
    """
    _fields = dict(
        # User supplied fields
        uploaded_as = BlobField("^[A-Za-z0-9_.]+$", "original upload filename", ""),
        description = BlobField(str, "brief description of this delivery",""),
        modifier_name = BlobField(str, "person who made these changes",""),
        deliverer_name = BlobField(str, "person who uploaded the file", ""),
        deliverer_email = BlobField(str, "deliverer's e-mail", ""),
        
        # Automatically generated fields
        pathname = BlobField("^[A-Za-z0-9_./]+$", 
                             "path/filename to CRDS master copy of file", "None"),
        delivery_date = BlobField(str, "date file was delivered to CRDS", ""),
        observatory = BlobField(OBSERVATORIES, 
                                "observatory associated with file", "hst"),
        instrument = BlobField(INSTRUMENTS, 
                               "instrument associated with file", "None"),
        reftype = BlobField(REFTYPES, 
                            "reference type associated with file", "None"),
        sha1sum = BlobField(str, "checksum of file at upload time", "None"),
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
    pass

class ReferenceBlob(FileBlob):
    pass



