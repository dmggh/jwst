from django.db import models

# Create your models here.

from crds.compat import literal_eval, namedtuple

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
        for field in self._fields:
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
            self._values[attr] = self._fields[attr].type(value)
        else:
            object.__setattr__(self, attr, value)
            
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
            return cls(blob=blob)
    

# ============================================================================

class FileBlob(Blob):
    """Represents a delivered file,  either a reference or a mapping.
    """
    _fields = dict(
            filename = BlobField(str, "name of the uploaded file", ""),
            deliverer = BlobField(str, "person who uploaded the file", ""),
            email = BlobField(str, "deliverer's e-mail", ""),
            observatory = BlobField(str, "observatory associated with file", "hst"),
            instrument = BlobField(str, "instrument associated with file", "none"),
            reftype = BlobField(str, "reference type associated with file", "none"),
            sha1sum = BlobField(str, "checksum of file at upload time", "none")
        )
    
    def save(self):
        Blob.save(self, self.filename)

